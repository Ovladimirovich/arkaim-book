"""Управляемое обновление затронутых кадров (managed frame update).

Offline (сеть не используется):
  POST /studio/{id}/prepared-updates — подготовка задания БЕЗ генерации
    (итоговый промпт/негатив из resolve_shot, снимок правил, референсы,
    выбранный исполнитель из IMAGE_EXECUTORS);
  PATCH /studio/{id}/prepared-updates/{prep_id} — статусное продвижение
    после запуска СУЩЕСТВУЮЩЕГО image-jobs (generating → done);
  POST /studio/{id}/prepared-updates/{prep_id}/approve — утверждение нового
    кадра ШОТА (shots.N.approved_image_asset_id, новая версия сценария) и
    СЦЕНЫ (session.approved_image_asset_id); старый кадр НЕ удаляется;
  GET /studio/{id}/art-direction/apply — обогащённый отчёт: prepared_updates
    и stale_videos (видео на предыдущем кадре требуют обновления).

Запуск (из runtime/):
  python -m pytest tests/test_studio_prepared_updates.py -v
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

from test_studio_art_direction import SCENE, _make_session_with_shots, _put_rules  # noqa: E402


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture()
def isolated_session_store(tmp_path, monkeypatch):
    from studio import store as studio_store_mod

    monkeypatch.setattr(studio_store_mod, "_DB_PATH", tmp_path / "studio_prep_test.db")
    yield


@pytest.fixture()
def isolated_assets(tmp_path, monkeypatch):
    from core.adc_deps import registry
    from visual_assets import storage as storage_mod

    monkeypatch.setattr(storage_mod, "_DATA_DIR", tmp_path / "visual_assets")
    store = storage_mod.AssetStorage(db_path=tmp_path / "studio_prep_assets.db")
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


def _save_completed_image(store, scene_id: str, prompt: str, gen_rev=None, shot_id=None):
    from visual_assets.schemas import AssetStatus, AssetType, GenerationParams, VisualAsset
    from visual_assets.storage import generate_asset_id

    asset = VisualAsset(
        asset_id=generate_asset_id(),
        asset_type=AssetType.IMAGE,
        chapter=1,
        scene_id=scene_id,
        title="готовый кадр",
        status=AssetStatus.COMPLETED,
        prompt_used=prompt,
        generation=GenerationParams(art_direction_revision=gen_rev, shot_id=shot_id),
    )
    return asyncio.run(store.save(asset)) or asset


def _save_completed_video(store, scene_id: str, ref_image_id: str | None):
    from visual_assets.schemas import AssetStatus, AssetType, GenerationParams, VisualAsset
    from visual_assets.storage import generate_asset_id

    asset = VisualAsset(
        asset_id=generate_asset_id(),
        asset_type=AssetType.VIDEO,
        chapter=1,
        scene_id=scene_id,
        title="видео сцены",
        status=AssetStatus.COMPLETED,
        prompt_used="ВИДЕО_ПРОМПТ",
        generation=GenerationParams(reference_image_id=ref_image_id),
    )
    asyncio.run(store.save(asset))
    return asset


def _prepare(client, session_id: str, shot_id: str = "shot_001", **body):
    return client.post(
        f"/studio/{session_id}/prepared-updates",
        json={"shot_id": shot_id, **body},
    )


# ── 1. Подготовка задания (без генерации) ────────────────────────


class TestPrepareUpdate:
    def test_prepare_returns_resolved_prompt_and_executor(self, client, isolated_session_store):
        session_id = _make_session_with_shots()
        _put_rules(client, palette=["бурый янтарь"], style_prompt="сказочный эпос")

        resp = _prepare(client, session_id)
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        prepared = data["prepared"]
        assert prepared["shot_id"] == "shot_001"
        assert prepared["status"] == "prepared"
        assert prepared["backend"] == "mock"
        assert prepared["new_asset_id"] is None, "генерация не запускалась"
        assert "сказочный эпос" in prepared["new_prompt"]
        assert "бурый янтарь" in prepared["new_prompt"]
        assert isinstance(prepared["negative_prompt"], list)
        assert prepared["applied_rules"]["revision"] == 1
        # Исполнитель: справочник для выбора (локальный/облачный, требования)
        assert data["executor"]["execution_label"].startswith("локальный")
        assert data["resolved"]["resolved_prompt"] == prepared["new_prompt"]

    def test_prepare_unknown_shot_is_404(self, client, isolated_session_store):
        session_id = _make_session_with_shots()
        resp = _prepare(client, session_id, shot_id="нет_такого")
        assert resp.status_code == 404

    def test_prepare_unknown_backend_is_400(self, client, isolated_session_store):
        session_id = _make_session_with_shots()
        resp = _prepare(client, session_id, backend="comfyicu")
        assert resp.status_code == 400
        assert "comfyicu" in resp.text

    def test_prepare_with_source_asset(self, client, isolated_session_store, isolated_assets):
        session_id = _make_session_with_shots()
        old = _save_completed_image(isolated_assets, SCENE, prompt="СТАРЫЙ")

        resp = _prepare(client, session_id, source_asset_id=old.asset_id)
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["prepared"]["source_asset_id"] == old.asset_id

    def test_prepare_lists_in_get(self, client, isolated_session_store):
        session_id = _make_session_with_shots()
        _prepare(client, session_id)
        _prepare(client, session_id, shot_id="shot_002")

        resp = client.get(f"/studio/{session_id}/prepared-updates")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert len(data["prepared_updates"]) == 2
        assert "mock" in data["executors"]
        assert "agnes" in data["executors"]

        # Фильтр по шоту
        resp2 = client.get(f"/studio/{session_id}/prepared-updates", params={"shot_id": "shot_001"})
        items = resp2.json()["data"]["prepared_updates"]
        assert len(items) == 1
        assert items[0]["shot_id"] == "shot_001"

    def test_patch_advances_status(self, client, isolated_session_store):
        session_id = _make_session_with_shots()
        prep = _prepare(client, session_id).json()["data"]["prepared"]

        resp = client.patch(
            f"/studio/{session_id}/prepared-updates/{prep['prepared_id']}",
            json={"status": "generating", "new_asset_id": "asset_x"},
        )
        assert resp.status_code == 200, resp.text
        updated = resp.json()["data"]
        assert updated["status"] == "generating"
        assert updated["new_asset_id"] == "asset_x"

        resp2 = client.patch(
            f"/studio/{session_id}/prepared-updates/{prep['prepared_id']}",
            json={"status": "done"},
        )
        assert resp2.json()["data"]["status"] == "done"

    def test_patch_unknown_status_is_400(self, client, isolated_session_store):
        session_id = _make_session_with_shots()
        prep = _prepare(client, session_id).json()["data"]["prepared"]
        resp = client.patch(
            f"/studio/{session_id}/prepared-updates/{prep['prepared_id']}",
            json={"status": "exploded"},
        )
        assert resp.status_code == 400


# ── 2. Утверждение нового кадра шота ─────────────────────────────


class TestApproveUpdate:
    def _ready_prepared(self, client, isolated_assets, session_id: str, **body):
        """Подготовка + completed-вариант + done (мок-контур без сети)."""
        prep = _prepare(client, session_id, **body).json()["data"]["prepared"]
        new_asset = _save_completed_image(isolated_assets, SCENE, prompt="НОВЫЙ_ВАРИАНТ", gen_rev=1)
        resp = client.patch(
            f"/studio/{session_id}/prepared-updates/{prep['prepared_id']}",
            json={"status": "done", "new_asset_id": new_asset.asset_id},
        )
        assert resp.status_code == 200, resp.text
        return prep, new_asset

    def test_approve_sets_shot_and_scene_frame(self, client, isolated_session_store, isolated_assets):
        session_id = _make_session_with_shots()
        prep, new_asset = self._ready_prepared(client, isolated_assets, session_id)

        resp = client.post(f"/studio/{session_id}/prepared-updates/{prep['prepared_id']}/approve")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["approved_image_asset_id"] == new_asset.asset_id
        assert data["shot_id"] == "shot_001"
        assert data["shot_index"] == 0
        assert data["prepared"]["status"] == "approved"

        # Шот в активной версии знает новый утверждённый кадр
        apply_data = client.get(f"/studio/{session_id}/art-direction/apply").json()["data"]
        shot = apply_data["shots"][0]
        assert shot["approved_image_asset_id"] == new_asset.asset_id
        assert apply_data["scene"]["approved_image_asset_id"] == new_asset.asset_id

    def test_approve_keeps_previous_and_old_asset(self, client, isolated_session_store, isolated_assets):
        session_id = _make_session_with_shots()
        # Старый утверждённый кадр шота и сцены
        old = _save_completed_image(isolated_assets, SCENE, prompt="СТАРЫЙ_КАДР", gen_rev=0)
        client.post(
            f"/studio/{session_id}/modify",
            params={
                "target": "video_scenario",
                "field_path": "shots.0.approved_image_asset_id",
                "new_value": old.asset_id,
            },
        )
        client.post(f"/studio/{session_id}/approve-image", params={"asset_id": old.asset_id})

        prep, new_asset = self._ready_prepared(client, isolated_assets, session_id)
        resp = client.post(f"/studio/{session_id}/prepared-updates/{prep['prepared_id']}/approve")
        data = resp.json()["data"]
        assert data["previous_shot_approved_image_asset_id"] == old.asset_id
        assert data["previous_scene_approved_image_asset_id"] == old.asset_id

        # Старый кадр НЕ удалён и доступен
        still_there = isolated_assets.get(old.asset_id)
        assert asyncio.run(still_there) is not None
        # Старое утверждение шота сохранено в предыдущей версии сценария
        versions = client.get(f"/studio/{session_id}").json()["data"]["versions"]
        prev = next(v for v in versions if v["version_number"] == data["version_number"] - 1)
        assert prev["video_scenario"]["shots"][0]["approved_image_asset_id"] == old.asset_id

    def test_approve_not_ready_is_409(self, client, isolated_session_store, isolated_assets):
        session_id = _make_session_with_shots()
        prep = _prepare(client, session_id).json()["data"]["prepared"]
        # Статус всё ещё prepared — утверждать рано
        resp = client.post(f"/studio/{session_id}/prepared-updates/{prep['prepared_id']}/approve")
        assert resp.status_code == 409

    def test_video_stays_linked_to_old_frame_and_is_stale(self, client, isolated_session_store, isolated_assets):
        """Видео на старом кадре не удаляется; связь video→input image сохраняется."""
        session_id = _make_session_with_shots()
        old = _save_completed_image(isolated_assets, SCENE, prompt="СТАРЫЙ_КАДР", gen_rev=0)
        client.post(f"/studio/{session_id}/approve-image", params={"asset_id": old.asset_id})
        video = _save_completed_video(isolated_assets, SCENE, ref_image_id=old.asset_id)

        prep, new_asset = self._ready_prepared(client, isolated_assets, session_id)
        client.post(f"/studio/{session_id}/prepared-updates/{prep['prepared_id']}/approve")

        apply_data = client.get(f"/studio/{session_id}/art-direction/apply").json()["data"]
        stale = apply_data["stale_videos"]
        assert len(stale) == 1
        assert stale[0]["asset_id"] == video.asset_id
        assert stale[0]["reference_image_id"] == old.asset_id
        assert stale[0]["current_approved"] == new_asset.asset_id
        # Видео не удалилось
        still = isolated_assets.get(video.asset_id)
        assert asyncio.run(still) is not None


# ── 3. Обогащённый отчёт /apply ─────────────────────────────────


class TestApplyEnriched:
    def test_apply_returns_prepared_and_frame_status(self, client, isolated_session_store, isolated_assets):
        session_id = _make_session_with_shots()
        _put_rules(client, palette=["бурый янтарь"])  # revision 1
        # Затронутый старый кадр + привязка к шоту через generation.shot_id
        old = _save_completed_image(isolated_assets, SCENE, prompt="СТАРЫЙ", gen_rev=0, shot_id="shot_001")
        prep = _prepare(client, session_id, source_asset_id=old.asset_id, shot_id="shot_001").json()["data"]["prepared"]

        data = client.get(f"/studio/{session_id}/art-direction/apply").json()["data"]
        affected = data["affected_artifacts"]
        assert len(affected) == 1
        entry = affected[0]
        assert entry["asset_id"] == old.asset_id
        assert entry["shot_id"] == "shot_001"
        assert entry["shot"]["shot_id"] == "shot_001"
        assert entry["shot"]["resolved_prompt"]
        assert entry["frame_status"] == "prepared_for_update"
        assert entry["prepared"]["prepared_id"] == prep["prepared_id"]
        assert entry["prepared"]["status"] == "prepared"

        # Список подготовленных заданий в отчёте (для карточек интерфейса)
        assert len(data["prepared_updates"]) == 1
        assert data["prepared_updates"][0]["prepared_id"] == prep["prepared_id"]

    def test_new_variant_shows_as_new_variant(self, client, isolated_session_store, isolated_assets):
        session_id = _make_session_with_shots()
        _put_rules(client, palette=["бурый янтарь"])
        old = _save_completed_image(isolated_assets, SCENE, prompt="СТАРЫЙ", gen_rev=0)
        new_asset = _save_completed_image(isolated_assets, SCENE, prompt="НОВЫЙ", gen_rev=1)
        prep = _prepare(client, session_id, source_asset_id=old.asset_id).json()["data"]["prepared"]
        client.patch(
            f"/studio/{session_id}/prepared-updates/{prep['prepared_id']}",
            json={"status": "done", "new_asset_id": new_asset.asset_id},
        )

        data = client.get(f"/studio/{session_id}/art-direction/apply").json()["data"]
        by_id = {e["asset_id"]: e for e in data["affected_artifacts"]}
        # Задание выполнено: старый кадр снова «требует обновления»,
        # но связь с готовым вариантом видна (сравнение/утверждение).
        assert by_id[old.asset_id]["frame_status"] == "needs_update"
        assert by_id[old.asset_id]["prepared"]["status"] == "done"
        # Сам новый вариант тоже виден в отчёте (сравнение/утверждение)
        assert by_id[new_asset.asset_id]["frame_status"] == "new_variant"
