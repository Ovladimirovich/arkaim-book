"""Режиссёрский Studio: пошотовые правки /modify + референсы с просмотром файла.

Offline (сеть не используется):
  POST /studio/{id}/modify с dotted-путём по спискам (shots.N.field) — раньше
    списковые индексы молча не применялись;
  регрессия scalar-путей (motion.camera_motion, synopsis);
  POST /studio/{id}/upload-reference — файл + метаданные VisualAsset,
    открываемый через существующий GET /book/assets/{id}/file.

Запуск (из runtime/):
  python -m pytest tests/test_studio_shot_modify.py -v
"""

from __future__ import annotations

import asyncio
import base64
import sys
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

SCENE = "conflict_гиперборея_материальный_путь_атлантиды"  # chapter 1

PNG_1PX = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture()
def isolated_session_store(tmp_path, monkeypatch):
    """StudioStore на временной БД: рабочий data/studio.db не трогается."""
    from studio import store as studio_store_mod

    monkeypatch.setattr(studio_store_mod, "_DB_PATH", tmp_path / "studio_shot_test.db")
    yield


@pytest.fixture()
def isolated_assets(tmp_path, monkeypatch):
    """AssetStorage на временных хранилищах (для upload-reference и /file)."""
    from core.adc_deps import registry
    from visual_assets import storage as storage_mod

    monkeypatch.setattr(storage_mod, "_DATA_DIR", tmp_path / "visual_assets")
    store = storage_mod.AssetStorage(db_path=tmp_path / "studio_shot_assets.db")
    had = "asset_store" in registry._instances
    old = registry._instances.get("asset_store")
    registry._instances["asset_store"] = store
    yield store
    if had:
        registry._instances["asset_store"] = old
    else:
        registry._instances.pop("asset_store", None)


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient
    from core.main import app

    return TestClient(app)


def _make_session_with_shots():
    """Сессия + активная версия с тремя шотами (закрытие conn — aiosqlite)."""
    from media_plan.schemas import MediaPlan, PlanLineage, SourceRefs
    from studio.scenario_schemas import ScenarioShot, VideoScenario
    from studio.store import StudioStore

    async def _run():
        store = StudioStore()
        try:
            session = await store.create_session(user_id="admin", title="тест", chapter=1, scene_id=SCENE)
            img = MediaPlan(
                plan_id="plan_img",
                media_kind="image",
                prompt="КАДР_ПРОМПТ",
                lineage=PlanLineage(derivation="initial", created_from="scene_context"),
                source_refs=SourceRefs(scene_id=SCENE, chapter=1),
            )
            vid = MediaPlan(
                plan_id="plan_vid",
                media_kind="video",
                prompt="ВИДЕО_ПРОМПТ",
                duration_sec=8.0,
                fps=24,
                lineage=PlanLineage(derivation="initial", created_from="scene_context"),
                source_refs=SourceRefs(scene_id=SCENE, chapter=1),
            )
            scenario = VideoScenario(
                scenario_id="sc_test",
                scene_id=SCENE,
                title="Тест",
                synopsis="ИСХОДНЫЙ_СИНОПСИС",
                total_duration_sec=9.0,
                shots=[
                    ScenarioShot(shot_id="shot_001", order=0, shot_type="establishing", description="Опис_0", duration_sec=3.0),
                    ScenarioShot(shot_id="shot_002", order=1, shot_type="medium", description="Опис_1", duration_sec=3.0),
                    ScenarioShot(shot_id="shot_003", order=2, shot_type="wide", description="Опис_2", duration_sec=3.0),
                ],
            )
            await store.create_version(
                session_id=session.session_id,
                version_number=1,
                image_description=img,
                video_description=vid,
                video_scenario=scenario,
                created_by="system",
                note="initial",
            )
            return session.session_id
        finally:
            await store.close()

    return asyncio.run(_run())


def _get_session_detail(client, session_id: str) -> dict:
    resp = client.get(f"/studio/{session_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


# ── 1. Пошотовые правки /modify ──────────────────────────────────


class TestModifyShotByIndex:
    def test_shot_description_edit_by_index(self, client, isolated_session_store):
        session_id = _make_session_with_shots()

        resp = client.post(
            f"/studio/{session_id}/modify",
            params={
                "target": "video_scenario",
                "field_path": "shots.1.description",
                "new_value": "НОВОЕ_ОПИСАНИЕ_ПЛАНА",
            },
        )
        assert resp.status_code == 200, resp.text
        new_version = resp.json()["data"]
        assert new_version["version_number"] == 2
        assert new_version["parent_version_id"]

        detail = _get_session_detail(client, session_id)
        active = next(v for v in detail["versions"] if v["version_id"] == detail["session"]["active_version_id"])
        shots = active["video_scenario"]["shots"]
        assert shots[1]["description"] == "НОВОЕ_ОПИСАНИЕ_ПЛАНА"
        # Соседние шоты не тронуты — правка точечная
        assert shots[0]["description"] == "Опис_0"
        assert shots[2]["description"] == "Опис_2"
        # Прочие поля шота сохранены (модель не пересобрана из потерь)
        assert shots[1]["shot_id"] == "shot_002"
        assert shots[1]["shot_type"] == "medium"

    def test_shot_duration_edit_coerced_to_float(self, client, isolated_session_store):
        session_id = _make_session_with_shots()

        resp = client.post(
            f"/studio/{session_id}/modify",
            params={"target": "video_scenario", "field_path": "shots.0.duration_sec", "new_value": "4.5"},
        )
        assert resp.status_code == 200, resp.text

        detail = _get_session_detail(client, session_id)
        active = next(v for v in detail["versions"] if v["version_id"] == detail["session"]["active_version_id"])
        assert active["video_scenario"]["shots"][0]["duration_sec"] == 4.5

    def test_invalid_list_path_does_not_change_scenario(self, client, isolated_session_store):
        session_id = _make_session_with_shots()

        resp = client.post(
            f"/studio/{session_id}/modify",
            params={"target": "video_scenario", "field_path": "shots.99.description", "new_value": "X"},
        )
        assert resp.status_code == 200, resp.text

        detail = _get_session_detail(client, session_id)
        active = next(v for v in detail["versions"] if v["version_id"] == detail["session"]["active_version_id"])
        descriptions = [s["description"] for s in active["video_scenario"]["shots"]]
        assert descriptions == ["Опис_0", "Опис_1", "Опис_2"]

    def test_scalar_paths_still_work(self, client, isolated_session_store):
        """Регрессия: синопсис (scenario) и motion.camera_motion (mediaplan)."""
        session_id = _make_session_with_shots()

        r1 = client.post(
            f"/studio/{session_id}/modify",
            params={"target": "video_scenario", "field_path": "synopsis", "new_value": "НОВЫЙ_СИНОПСИС"},
        )
        assert r1.status_code == 200, r1.text

        r2 = client.post(
            f"/studio/{session_id}/modify",
            params={
                "target": "video_description",
                "field_path": "motion.camera_motion",
                "new_value": "slow_dolly_in",
            },
        )
        assert r2.status_code == 200, r2.text

        detail = _get_session_detail(client, session_id)
        active = next(v for v in detail["versions"] if v["version_id"] == detail["session"]["active_version_id"])
        assert active["video_scenario"]["synopsis"] == "НОВЫЙ_СИНОПСИС"
        assert active["video_description"]["motion"]["camera_motion"] == "slow_dolly_in"


# ── 2. Референсы: загрузка → метаданные → файл открывается ───────


class TestReferenceUpload:
    def test_reference_upload_is_viewable(self, client, isolated_session_store, isolated_assets):
        session_id = _make_session_with_shots()

        resp = client.post(
            f"/studio/{session_id}/upload-reference",
            files={"file": ("ref.png", PNG_1PX, "image/png")},
            data={"description": "такой свет"},
        )
        assert resp.status_code == 200, resp.text
        ref = resp.json()["data"]
        asset_id = ref["asset_id"]
        assert ref["description"] == "такой свет"

        # Файл открывается существующим GET /book/assets/{id}/file (без 404)
        opened = client.get(f"/book/assets/{asset_id}/file")
        assert opened.status_code == 200, opened.text
        assert opened.content == PNG_1PX

        # Метаданные ассета читаются (тип image, статус completed)
        meta = client.get(f"/book/assets/{asset_id}")
        assert meta.status_code == 200
        asset = meta.json()["data"]
        assert asset["asset_type"] == "image"
        assert asset["status"] == "completed"

        # Референс виден в сессии
        detail = _get_session_detail(client, session_id)
        assert any(r["asset_id"] == asset_id for r in detail["references"])

    def test_reference_upload_empty_file_rejected(self, client, isolated_session_store, isolated_assets):
        session_id = _make_session_with_shots()
        resp = client.post(
            f"/studio/{session_id}/upload-reference",
            files={"file": ("empty.png", b"", "image/png")},
            data={"description": ""},
        )
        assert resp.status_code == 400
