"""Дерево фильма (Фаза 0): контейнер → сцены каталога → план (шот).

Offline (сеть не используется):
  GET /studio/film — read-only проекция фильма. Канонический список сцен
    берётся из read-only каталога киносценария (SYNOPSIS_DOCUMENT.json);
    Studio аннотирует их состоянием (сессия, утверждённый кадр, видео),
    не создавая и не изменяя данные.

Запуск (из runtime/):
  python -m pytest tests/test_studio_film.py -v
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

SCENE = "scene_000"
CHAPTER = 0


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture()
def isolated_session_store(tmp_path, monkeypatch):
    from studio import store as studio_store_mod

    monkeypatch.setattr(studio_store_mod, "_DB_PATH", tmp_path / "studio_film_test.db")
    yield


@pytest.fixture()
def isolated_assets(tmp_path, monkeypatch):
    from core.adc_deps import registry
    from visual_assets import storage as storage_mod

    monkeypatch.setattr(storage_mod, "_DATA_DIR", tmp_path / "visual_assets")
    store = storage_mod.AssetStorage(db_path=tmp_path / "film_assets.db")
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


def _run(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def _make_session_with_shots(user_id: str, scene_id: str, approved_image: str | None = None) -> str:
    """Сессия на временном хранилище + активная версия с тремя шотами."""
    from studio.scenario_schemas import ScenarioShot, VideoScenario
    from studio.store import StudioStore

    async def _run_inner():
        store = StudioStore()
        try:
            session = await store.create_session(user_id=user_id, title="фильм-тест", chapter=CHAPTER, scene_id=scene_id)
            scenario = VideoScenario(
                scenario_id="sc_film",
                scene_id=scene_id,
                title="Тестовая сцена",
                total_duration_sec=9.0,
                shots=[
                    ScenarioShot(shot_id="shot_001", order=0, shot_type="establishing", duration_sec=3.0),
                    ScenarioShot(shot_id="shot_002", order=1, shot_type="medium", duration_sec=3.0),
                    ScenarioShot(shot_id="shot_003", order=2, shot_type="wide", duration_sec=3.0),
                ],
            )
            await store.create_version(
                session_id=session.session_id,
                version_number=1,
                video_scenario=scenario,
                created_by="system",
                note="initial",
            )
            if approved_image:
                await store.set_approved_image(session.session_id, approved_image)
            return session.session_id
        finally:
            await store.close()

    return _run(_run_inner())


def _save_video(store, scene_id: str, shot_id: str | None):
    from visual_assets.schemas import AssetStatus, AssetType, GenerationParams, VisualAsset
    from visual_assets.storage import generate_asset_id

    asset = VisualAsset(
        asset_id=generate_asset_id(),
        asset_type=AssetType.VIDEO,
        chapter=CHAPTER,
        scene_id=scene_id,
        title="тестовое видео",
        status=AssetStatus.COMPLETED,
        prompt_used="video prompt",
        generation=GenerationParams(shot_id=shot_id),
    )
    _run(store.save(asset))
    return asset


def _find_scene(payload: dict, scene_id: str) -> dict:
    for ep in payload["episodes"]:
        for s in ep["scenes"]:
            if s["scene_id"] == scene_id:
                return s
    raise AssertionError(f"scene {scene_id!r} not found")


# ── 1. Канонический список сцен ──────────────────────────────────


class TestFilmCanonical:
    def test_returns_screenplay_catalog_scenes_as_single_container(self, client, isolated_session_store):
        resp = client.get("/studio/film")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]

        assert data["film"]["scene_count"] == 119
        assert data["film"]["book_id"] == "nasledie-arkaima"
        assert data["film"]["episode_count"] == 1
        assert data["film"]["episode_count"] == len(data["episodes"])

        episode = data["episodes"][0]
        assert episode["chapter"] == 0
        assert episode["episode_id"] == "chapter_0"
        assert episode["title"] == "Сценарий"
        assert episode["scene_count"] == 119
        assert episode["scene_count"] == data["film"]["scene_count"]

        scene_ids = [s["scene_id"] for s in episode["scenes"]]
        assert scene_ids[0] == "scene_000"
        assert scene_ids[-1] == "scene_118"
        assert scene_ids == [f"scene_{i:03d}" for i in range(119)]
        assert all(s["chapter"] == 0 for s in episode["scenes"])
        assert all(s["index_in_episode"] == idx for idx, s in enumerate(episode["scenes"]))
        assert all(s["order_global"] == idx for idx, s in enumerate(episode["scenes"]))
        assert not any(s["scene_id"].startswith(("conflict_", "meaning_auto_")) for s in episode["scenes"])
        assert "test_meeting" not in scene_ids
        scene_034 = next(scene for scene in episode["scenes"] if scene["scene_id"] == "scene_034")
        assert scene_034["characters"] == ["Велик"]

        # Без сессий сцены не имеют workspace и помечены no_session.
        for s in episode["scenes"]:
            assert s["has_session"] is False
            assert s["session_id"] is None
            assert s["shot_count"] == 0
            assert s["status"] == "no_session"

    def test_scene_cards_carry_compact_world_link_counts(self, client, isolated_session_store):
        """Дерево фильма получает счётчики связей с миром — без самих связей."""
        resp = client.get("/studio/film")
        assert resp.status_code == 200, resp.text
        payload = resp.json()["data"]

        scene_004 = _find_scene(payload, "scene_004")
        counts = scene_004["world_link_counts"]
        assert set(counts) == {"confirmed", "derived", "unresolved"}
        assert counts["confirmed"] == 2
        assert counts["derived"] == 7
        assert counts["unresolved"] == 1
        # Полные связи в дерево не дублируются.
        assert "world_links" not in scene_004
        assert "world_link_summary" not in scene_004

        # Сцена без разрешённых связей: счётчики нулевые, а не выдуманные.
        scene_013 = _find_scene(payload, "scene_013")
        assert scene_013["world_link_counts"] == {"confirmed": 0, "derived": 0, "unresolved": 1}

        # Счётчики есть у всех сцен дерева.
        for episode in payload["episodes"]:
            for scene in episode["scenes"]:
                assert set(scene["world_link_counts"]) == {"confirmed", "derived", "unresolved"}

    def test_scenes_endpoint_returns_same_catalog(self, client):
        resp = client.get("/studio/scenes")
        assert resp.status_code == 200, resp.text
        scenes = resp.json()["data"]

        assert len(scenes) == 119
        assert scenes[0] == {"scene_id": "scene_000", "chapter": 0, "title": "1. EXT. ГЛУБОКИЙ КОСМОС"}
        assert scenes[-1]["scene_id"] == "scene_118"
        assert all(s["chapter"] == 0 for s in scenes)
        assert not any(s["scene_id"].startswith(("conflict_", "meaning_auto_")) for s in scenes)
        assert "test_meeting" not in {s["scene_id"] for s in scenes}

    def test_film_route_not_shadowed_by_session_route(self, client, isolated_session_store):
        # GET /studio/film не должен попадать в /studio/{session_id}.
        resp = client.get("/studio/film")
        assert resp.status_code == 200, resp.text
        assert "episodes" in resp.json()["data"]


# ── 2. Аннотация состояния Studio ────────────────────────────────


class TestFilmAnnotation:
    def test_scene_annotated_with_session_shots_and_video(self, client, isolated_session_store, isolated_assets):
        session_id = _make_session_with_shots("test-user", SCENE, approved_image="img_approved")
        video = _save_video(isolated_assets, SCENE, shot_id="shot_001")

        resp = client.get("/studio/film")
        assert resp.status_code == 200, resp.text
        scene = _find_scene(resp.json()["data"], SCENE)

        assert scene["has_session"] is True
        assert scene["session_id"] == session_id
        assert scene["approved_image_asset_id"] == "img_approved"
        assert scene["shot_count"] == 3
        assert scene["total_duration_sec"] == 9.0
        assert scene["video_count"] == 1
        assert scene["has_video"] is True
        assert scene["status"] == "video"

        shot1 = next(s for s in scene["shots"] if s["shot_id"] == "shot_001")
        shot2 = next(s for s in scene["shots"] if s["shot_id"] == "shot_002")
        assert shot1["has_video"] is True
        assert shot1["video_asset_id"] == video.asset_id
        assert shot2["has_video"] is False
        assert shot2["video_asset_id"] is None

    def test_frame_approved_status_without_video(self, client, isolated_session_store, isolated_assets):
        _make_session_with_shots("test-user", SCENE, approved_image="img_approved")

        resp = client.get("/studio/film")
        scene = _find_scene(resp.json()["data"], SCENE)
        assert scene["has_video"] is False
        assert scene["status"] == "frame_approved"

    def test_prompts_status_without_approved_frame(self, client, isolated_session_store, isolated_assets):
        _make_session_with_shots("test-user", SCENE, approved_image=None)

        resp = client.get("/studio/film")
        scene = _find_scene(resp.json()["data"], SCENE)
        assert scene["shot_count"] == 3
        assert scene["approved_image_asset_id"] is None
        assert scene["status"] == "prompts"

    def test_other_users_sessions_are_not_visible(self, client, isolated_session_store, isolated_assets):
        # Сессия другого пользователя не должна аннотировать сцену.
        _make_session_with_shots("other-user", SCENE, approved_image="img_x")

        resp = client.get("/studio/film")
        scene = _find_scene(resp.json()["data"], SCENE)
        assert scene["has_session"] is False
        assert scene["status"] == "no_session"
