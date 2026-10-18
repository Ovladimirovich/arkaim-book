"""Единый визуальный язык фильма (art direction): правила, ревизии, применение.

Offline (сеть не используется):
  GET/PUT /studio/art-direction — единый источник film-wide правил;
    revision растёт ТОЛЬКО при фактическом изменении (diff по секциям);
  GET /studio/art-direction/library — справочники Visual Knowledge (без копий);
  GET /studio/{id}/art-direction/apply — применённые правила/локальные
    переопределения/итоговый промпт каждого плана + затронутые артефакты;
  правка локального списка шота (palette_override) через /modify — коэрция
    строки в список (раньше молча проваливалась в валидации).

Запуск (из runtime/):
  python -m pytest tests/test_studio_art_direction.py -v
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

SCENE = "conflict_гиперборея_материальный_путь_атлантиды"  # chapter 1


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture()
def isolated_session_store(tmp_path, monkeypatch):
    """StudioStore на временной БД: рабочий data/studio.db не трогается."""
    from studio import store as studio_store_mod

    monkeypatch.setattr(studio_store_mod, "_DB_PATH", tmp_path / "studio_ad_test.db")
    yield


@pytest.fixture()
def isolated_assets(tmp_path, monkeypatch):
    """AssetStorage на временных хранилищах (для affected-артефактов)."""
    from core.adc_deps import registry
    from visual_assets import storage as storage_mod

    monkeypatch.setattr(storage_mod, "_DATA_DIR", tmp_path / "visual_assets")
    store = storage_mod.AssetStorage(db_path=tmp_path / "studio_ad_assets.db")
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
    from media_plan.schemas import CharacterPlan, LocationRef, MediaPlan, PlanLineage, SourceRefs
    from studio.scenario_schemas import ScenarioShot, VideoScenario
    from studio.store import StudioStore

    async def _run():
        store = StudioStore()
        try:
            session = await store.create_session(user_id="admin", title="тест", chapter=1, scene_id=SCENE)
            img = MediaPlan(
                plan_id="plan_img",
                media_kind="image",
                prompt="КАДР_ПРОМПТ_ИЗМЕНЁН",
                lineage=PlanLineage(derivation="initial", created_from="scene_context"),
                source_refs=SourceRefs(scene_id=SCENE, chapter=1),
                characters=[CharacterPlan(character_id="char_1", name="Велик")],
                location=LocationRef(location_id="loc_1", name="Гиперборея", type="city"),
            )
            vid = MediaPlan(
                plan_id="plan_vid",
                media_kind="video",
                prompt="ВИДЕО_ПРОМПТ",
                duration_sec=9.0,
                fps=24,
                lineage=PlanLineage(derivation="initial", created_from="scene_context"),
                source_refs=SourceRefs(scene_id=SCENE, chapter=1),
            )
            scenario = VideoScenario(
                scenario_id="sc_ad",
                scene_id=SCENE,
                title="Зимний путь",
                synopsis="СИНОПСИС",
                total_duration_sec=9.0,
                shots=[
                    ScenarioShot(
                        shot_id="shot_001",
                        order=0,
                        shot_type="establishing",
                        description="Опис_0",
                        duration_sec=3.0,
                    ),
                    ScenarioShot(
                        shot_id="shot_002",
                        order=1,
                        shot_type="medium",
                        description="Опис_1",
                        duration_sec=3.0,
                    ),
                    ScenarioShot(
                        shot_id="shot_003",
                        order=2,
                        shot_type="wide",
                        description="Опис_2",
                        duration_sec=3.0,
                    ),
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


def _put_rules(client, **changes) -> dict:
    """PUT /studio/art-direction на основе текущих правил + изменения."""
    current = client.get("/studio/art-direction").json()["data"]
    current.update(changes)
    resp = client.put("/studio/art-direction", json=current)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


# ── 1. Единый источник правил: чтение/запись, ревизии ───────────


class TestArtDirectionRules:
    def test_get_returns_default_rules(self, client, isolated_session_store):
        resp = client.get("/studio/art-direction")
        assert resp.status_code == 200, resp.text
        ad = resp.json()["data"]
        assert ad["ad_id"] == "film"
        assert ad["revision"] == 0
        assert ad["style_preset"] == "cinematic_fantasy"
        assert ad["characters"] == []

    def test_put_increments_revision_on_change_only(self, client, isolated_session_store):
        data = _put_rules(client, palette=["золото", "лазурь"])
        assert data["art_direction"]["revision"] == 1
        assert data["changed_sections"] == ["palette"]

        # Без фактических изменений — ревизия НЕ растёт (diff пуст)
        same = _put_rules(client, palette=["золото", "лазурь"])
        assert same["art_direction"]["revision"] == 1
        assert same["changed_sections"] == []

        # Ещё одно изменение — ревизия растёт, запоминается что изменилось
        data2 = _put_rules(client, composition_rules=["третье правило"])
        assert data2["art_direction"]["revision"] == 2
        assert "composition_rules" in data2["changed_sections"]

    def test_put_change_is_persisted(self, client, isolated_session_store):
        _put_rules(client, lighting_rules=["мягкий боковой свет"])
        ad = client.get("/studio/art-direction").json()["data"]
        assert ad["lighting_rules"] == ["мягкий боковой свет"]
        assert ad["revision"] == 1

    def test_library_exposes_visual_knowledge_without_copies(self, client, isolated_session_store):
        resp = client.get("/studio/art-direction/library")
        assert resp.status_code == 200, resp.text
        lib = resp.json()["data"]
        assert lib["styles"], "STYLE_LIBRARY должна отдаваться"
        assert "cinematic_fantasy" in lib["styles"]
        assert lib["styles"]["cinematic_fantasy"]["prefix"]
        assert lib["characters"], "CHARACTER_VISUALS должна отдаваться"
        assert "Велик" in lib["characters"]
        assert lib["locations"], "LOCATION_VISUALS должна отдаваться"
        assert "Гиперборея" in lib["locations"]
        assert lib["locations"]["Гиперборея"]["palette"]


# ── 2. Применение правил к планам сцены ─────────────────────────


class TestApplyArtDirection:
    def test_apply_returns_per_shot_resolved_prompt(self, client, isolated_session_store):
        session_id = _make_session_with_shots()

        resp = client.get(f"/studio/{session_id}/art-direction/apply")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]

        assert data["art_direction"]["revision"] == 0
        assert data["scene"]["location"] == "Гиперборея"
        assert data["scene"]["characters"] == ["Велик"]
        assert data["episode"]["shot_count"] == 3
        assert data["episode"]["total_duration_sec"] == 9.0

        assert len(data["shots"]) == 3
        first = data["shots"][0]
        assert first["shot_id"] == "shot_001"
        assert first["local_overrides"] == {}  # ничего не задано локально
        assert first["applied"]["style_preset"] == "cinematic_fantasy"
        assert first["resolved_prompt"]
        assert "Опис_0" in first["resolved_prompt"]
        assert isinstance(first["resolved_negative"], list)

    def test_changed_rules_flow_into_resolved_prompts(self, client, isolated_session_store):
        session_id = _make_session_with_shots()

        _put_rules(
            client,
            style_prompt="ночная северная сказка",
            palette=["иней", "темнеющий синий"],
            composition_rules=["центр композиции — силуэт героя"],
            negative_rules=["перенасыщенные цвета"],
        )

        data = client.get(f"/studio/{session_id}/art-direction/apply").json()["data"]
        assert data["art_direction"]["revision"] == 1

        for shot in data["shots"]:
            prompt = shot["resolved_prompt"]
            assert "ночная северная сказка" in prompt
            assert "иней" in prompt
            assert "центр композиции — силуэт героя" in prompt
            assert "перенасыщенные цвета" in shot["resolved_negative"]

        # Секции изменения видны режиссёру (что изменилось в правилах)
        assert set(data["episode"]["last_change_sections"]) == {
            "style",
            "palette",
            "composition_rules",
            "negative_rules",
        }

    def test_character_and_location_matched_by_name(self, client, isolated_session_store):
        ad = client.get("/studio/art-direction").json()["data"]
        ad["characters"] = [{"knowledge_key": "Велик", "name": "Велик", "note": "в шубе"}]
        ad["locations"] = [{"knowledge_key": "Гиперборея", "name": "Гиперборея", "palette": []}]
        assert client.put("/studio/art-direction", json=ad).status_code == 200

        session_id = _make_session_with_shots()
        data = client.get(f"/studio/{session_id}/art-direction/apply").json()["data"]
        first = data["shots"][0]
        assert first["applied"]["characters"], "персонажи сцены сматчены по имени"
        assert first["applied"]["characters"][0]["knowledge_key"] == "Велик"
        assert first["applied"]["location"]["knowledge_key"] == "Гиперборея"
        assert "Велик" in first["resolved_prompt"]
        assert "Гиперборея" in first["resolved_prompt"]

    def test_local_shot_override_wins_and_is_visible(self, client, isolated_session_store):
        session_id = _make_session_with_shots()

        # Общие правила заданы — локальный override должен их перебить
        _put_rules(client, palette=["иней"], style_prompt="общий стиль фильма")

        # Правка локального списка шота строкой через существующий /modify
        resp = client.post(
            f"/studio/{session_id}/modify",
            params={
                "target": "video_scenario",
                "field_path": "shots.0.palette_override",
                "new_value": "золото, бирюза",
            },
        )
        assert resp.status_code == 200, resp.text

        resp2 = client.post(
            f"/studio/{session_id}/modify",
            params={
                "target": "video_scenario",
                "field_path": "shots.0.style_override",
                "new_value": "снежная эпика",
            },
        )
        assert resp2.status_code == 200, resp2.text

        data = client.get(f"/studio/{session_id}/art-direction/apply").json()["data"]
        first = data["shots"][0]
        # Локальное видно отдельно (правки шота не затёрты общими правилами)
        assert first["local_overrides"]["palette_override"] == ["золото", "бирюза"]
        assert first["local_overrides"]["style_override"] == "снежная эпика"
        # В итоговом промпте — локальное, не общее
        assert "золото" in first["resolved_prompt"]
        assert "снежная эпика" in first["resolved_prompt"]
        assert "общий стиль фильма" not in first["resolved_prompt"]
        assert "иней" not in first["resolved_prompt"]

        # Соседние шоты продолжают использовать общие правила
        second = data["shots"][1]
        assert second["local_overrides"] == {}
        assert "иней" in second["resolved_prompt"]


# ── 3. Затронутые изменениями правил артефакты ───────────────────


class TestAffectedArtifacts:
    @staticmethod
    def _save_completed_image(store, scene_id: str, prompt: str, gen_rev=None):
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
            generation=GenerationParams(art_direction_revision=gen_rev),
        )
        import asyncio as _aio

        return _aio.run(store.save(asset))

    def test_completed_asset_flagged_after_rules_change(self, client, isolated_session_store, isolated_assets):
        session_id = _make_session_with_shots()
        # Артефакт создан ДО правил (revision поля нет → None)
        self._save_completed_image(isolated_assets, SCENE, prompt="КАДР_ПРОМПТ_ИЗМЕНЁН", gen_rev=None)

        # Правила изменены → артефакт затронут, но НЕ удаляется/не пересоздаётся
        _put_rules(client, palette=["бурый янтарь"])

        data = client.get(f"/studio/{session_id}/art-direction/apply").json()["data"]
        affected = data["affected_artifacts"]
        assert len(affected) == 1
        entry = affected[0]
        assert entry["asset_type"] == "image"
        assert entry["status"] == "completed"
        assert any("до введения общих правил" in r for r in entry["reasons"])

    def test_asset_at_current_revision_not_flagged(self, client, isolated_session_store, isolated_assets):
        session_id = _make_session_with_shots()
        _put_rules(client, palette=["бурый янтарь"])  # revision 1

        # Артефакт создан ПОСЛЕ правил (revision=1) и промпт совпадает
        self._save_completed_image(isolated_assets, SCENE, prompt="КАДР_ПРОМПТ_ИЗМЕНЁН", gen_rev=1)

        data = client.get(f"/studio/{session_id}/art-direction/apply").json()["data"]
        assert data["affected_artifacts"] == []

    def test_generation_params_carries_art_direction_revision(self, client, isolated_session_store, isolated_assets):
        """Новое задание на генерацию фиксирует текущую ревизию правил."""
        _put_rules(client, palette=["морозный белый"])  # revision 1

        resp = client.post(
            "/studio/image-jobs",
            json={
                "chapter": 1,
                "scene_id": SCENE,
                "prompt": "ТЕСТОВЫЙ_ПРОМПТ",
                "title": "тест",
            },
        )
        assert resp.status_code == 200, resp.text
        asset_id = resp.json()["data"]["asset_id"]

        meta = client.get(f"/book/assets/{asset_id}")
        assert meta.status_code == 200, meta.text
        gen = meta.json()["data"]["generation"]
        assert gen["art_direction_revision"] == 1
