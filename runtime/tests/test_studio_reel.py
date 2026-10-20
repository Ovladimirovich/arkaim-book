"""Story Reel (Фаза 3): лента «Эпизод → Сцена → План → Кадр → Клип».

Offline (сеть не используется). Два уровня:
  - unit-тесты чистых функций studio.reel (frame_state / clip_state /
    video_for_shot) — детерминированные;
  - интеграционные тесты маршрута GET /studio/reel (область scene / sequence /
    episode, статусы кадров и клипов, границы планов и сцен, метка переноса).

Ключевые проверки (OWNER-GO):
  1. Порядок берётся из канонических данных (геном → сцены, сценарий → планы),
     а не из порядка ассетов; лента не переупорядочивает сцены/планы.
  2. Кадр: утверждён / отсутствует / требует обновления (промпт изменился).
  3. Клип: отсутствует / mock / реальный / устарел (кадр, промпт или правила).
  4. Привязка клипа к плану по shot_id, иначе по reference_image_id.
  5. Границы: состояние continuity для перехода План N → N+1 и между сценами.
  6. Применённый перенос ограничений отображается на сцене-приёмнике.

Запуск (из runtime/):
  python -m pytest tests/test_studio_reel.py -v
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

# Каталог 0..118: канонический порядок Studio.
SCENE_FIRST = "scene_000"  # index 0
SCENE_A = "scene_001"  # index 1
SCENE_B = "scene_002"  # index 2
SCENE_MEETING = "scene_000"  # каноническая сцена для одиночных проверок


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture()
def isolated_session_store(tmp_path, monkeypatch):
    from studio import store as studio_store_mod

    monkeypatch.setattr(studio_store_mod, "_DB_PATH", tmp_path / "studio_reel_test.db")
    yield


@pytest.fixture()
def isolated_assets(tmp_path, monkeypatch):
    from core.adc_deps import registry
    from visual_assets import storage as storage_mod

    monkeypatch.setattr(storage_mod, "_DATA_DIR", tmp_path / "visual_assets")
    store = storage_mod.AssetStorage(db_path=tmp_path / "reel_assets.db")
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


def _make_session(
    user_id: str,
    scene_id: str,
    *,
    shots: int = 2,
    approved_image: str | None = None,
    shot_approved: dict | None = None,
    lighting: str = "warm side light",
) -> str:
    from studio.scenario_schemas import ScenarioShot, VideoScenario
    from studio.store import StudioStore

    async def _inner():
        store = StudioStore()
        try:
            session = await store.create_session(user_id=user_id, title="reel-тест", chapter=0, scene_id=scene_id)
            shot_list = []
            for i in range(shots):
                sid = f"shot_{i + 1:03d}"
                shot_list.append(
                    ScenarioShot(
                        shot_id=sid,
                        order=i,
                        shot_type="medium",
                        duration_sec=3.0,
                        lighting_note=lighting,
                        approved_image_asset_id=(shot_approved or {}).get(sid),
                    )
                )
            scenario = VideoScenario(
                scenario_id="sc_reel",
                scene_id=scene_id,
                title="Сцена ленты",
                total_duration_sec=3.0 * shots,
                shots=shot_list,
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

    return _run(_inner())


def _save_video(
    store,
    scene_id: str,
    shot_id: str | None,
    *,
    status=None,
    provider: str = "agnes",
    reference_image_id: str | None = None,
    art_direction_revision: int | None = None,
    prompt_used: str = "",
):
    from visual_assets.schemas import AssetStatus, AssetType, GenerationParams, VisualAsset
    from visual_assets.storage import generate_asset_id

    asset = VisualAsset(
        asset_id=generate_asset_id(),
        asset_type=AssetType.VIDEO,
        chapter=0,
        scene_id=scene_id,
        title="тестовый клип",
        status=status or AssetStatus.COMPLETED,
        prompt_used=prompt_used,
        generation=GenerationParams(
            provider=provider,
            backend=provider,
            shot_id=shot_id,
            reference_image_id=reference_image_id,
            art_direction_revision=art_direction_revision,
        ),
    )
    _run(store.save(asset))
    return asset


def _shot(payload: dict, shot_id: str) -> dict:
    for s in payload["scenes"]:
        for sh in s["shots"]:
            if sh["shot_id"] == shot_id:
                return sh
    raise AssertionError(f"shot {shot_id!r} not found")


# ── Unit: чистые функции studio.reel ─────────────────────────────


class TestFrameStateUnit:
    def test_none_when_frame_not_approved(self):
        from studio import reel
        from studio.scenario_schemas import ScenarioShot

        assert reel.frame_state(ScenarioShot(shot_id="s1", order=0), None, "prompt")["status"] == reel.FRAME_NONE

    def test_approved(self):
        from studio import reel
        from studio.scenario_schemas import ScenarioShot

        shot = ScenarioShot(shot_id="s1", order=0, approved_image_asset_id="img_1")
        state = reel.frame_state(shot, None, "prompt")
        assert state == {"status": reel.FRAME_APPROVED, "asset_id": "img_1"}

    def test_needs_update_when_prompt_changed(self):
        from types import SimpleNamespace

        from studio import reel
        from studio.scenario_schemas import ScenarioShot

        shot = ScenarioShot(shot_id="s1", order=0, approved_image_asset_id="img_1")
        asset = SimpleNamespace(status=SimpleNamespace(value="completed"), prompt_used="old prompt")
        state = reel.frame_state(shot, asset, "new   prompt")
        assert state["status"] == reel.FRAME_NEEDS_UPDATE

    def test_no_update_flag_without_prompt_data(self):
        from types import SimpleNamespace

        from studio import reel
        from studio.scenario_schemas import ScenarioShot

        shot = ScenarioShot(shot_id="s1", order=0, approved_image_asset_id="img_1")
        asset = SimpleNamespace(status=SimpleNamespace(value="completed"), prompt_used="")
        assert reel.frame_state(shot, asset, "new prompt")["status"] == reel.FRAME_APPROVED


class TestClipStateUnit:
    def test_none(self):
        from studio import reel

        assert reel.clip_state(None, shot_frame_id=None, resolved_prompt="", art_direction_revision=0)["status"] == reel.CLIP_NONE

    def test_mock(self):
        from types import SimpleNamespace

        from studio import reel

        asset = SimpleNamespace(
            status=SimpleNamespace(value="completed"),
            asset_id="v1",
            prompt_used="",
            generation=SimpleNamespace(provider="mock", backend=None, reference_image_id=None, art_direction_revision=0),
        )
        state = reel.clip_state(asset, shot_frame_id=None, resolved_prompt="", art_direction_revision=0)
        assert state["status"] == reel.CLIP_MOCK
        assert state["mock"] is True

    def test_ready(self):
        from types import SimpleNamespace

        from studio import reel

        asset = SimpleNamespace(
            status=SimpleNamespace(value="completed"),
            asset_id="v1",
            prompt_used="",
            generation=SimpleNamespace(provider="agnes", backend="agnes", reference_image_id="img_1", art_direction_revision=2),
        )
        state = reel.clip_state(asset, shot_frame_id="img_1", resolved_prompt="", art_direction_revision=2)
        assert state["status"] == reel.CLIP_READY
        assert state["stale_reasons"] == []

    def test_stale_on_frame_mismatch(self):
        from types import SimpleNamespace

        from studio import reel

        asset = SimpleNamespace(
            status=SimpleNamespace(value="completed"),
            asset_id="v1",
            prompt_used="",
            generation=SimpleNamespace(provider="agnes", backend="agnes", reference_image_id="img_other", art_direction_revision=0),
        )
        state = reel.clip_state(asset, shot_frame_id="img_1", resolved_prompt="", art_direction_revision=0)
        assert state["status"] == reel.CLIP_STALE
        assert state["stale_reasons"]

    def test_stale_on_revision_bump(self):
        from types import SimpleNamespace

        from studio import reel

        asset = SimpleNamespace(
            status=SimpleNamespace(value="completed"),
            asset_id="v1",
            prompt_used="",
            generation=SimpleNamespace(provider="agnes", backend="agnes", reference_image_id=None, art_direction_revision=1),
        )
        state = reel.clip_state(asset, shot_frame_id=None, resolved_prompt="", art_direction_revision=5)
        assert state["status"] == reel.CLIP_STALE


class TestVideoForShotUnit:
    def _video(self, shot_id, ref, created="2024-01-01T00:00:00Z"):
        from types import SimpleNamespace

        return SimpleNamespace(
            asset_id=f"v_{shot_id}_{ref}",
            created_at=created,
            generation=SimpleNamespace(shot_id=shot_id, reference_image_id=ref),
        )

    def test_match_by_shot_id(self):
        from studio import reel
        from studio.scenario_schemas import ScenarioShot

        shot = ScenarioShot(shot_id="s1", order=0, approved_image_asset_id="img_1")
        videos = [self._video("s2", "img_1"), self._video("s1", None)]
        assert reel.video_for_shot(videos, shot).asset_id.endswith("s1_None")

    def test_match_by_reference_image_for_legacy(self):
        from studio import reel
        from studio.scenario_schemas import ScenarioShot

        shot = ScenarioShot(shot_id="s1", order=0, approved_image_asset_id="img_1")
        videos = [self._video(None, "img_1")]
        assert reel.video_for_shot(videos, shot) is videos[0]

    def test_no_match_returns_none(self):
        from studio import reel
        from studio.scenario_schemas import ScenarioShot

        shot = ScenarioShot(shot_id="s1", order=0, approved_image_asset_id="img_1")
        assert reel.video_for_shot([self._video("s9", "img_x")], shot) is None


# ── Интеграция: GET /studio/reel ─────────────────────────────────


class TestReelScope:
    def test_scene_scope_single_scene(self, client, isolated_session_store, isolated_assets):
        _make_session("test-user", SCENE_MEETING, shots=2)
        resp = client.get("/studio/reel", params={"scene_id": SCENE_MEETING})
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["scope"] == "scene"
        assert [s["scene_id"] for s in data["scenes"]] == [SCENE_MEETING]

    def test_episode_scope_all_chapter_scenes_in_canonical_order(self, client, isolated_session_store, isolated_assets):
        resp = client.get("/studio/reel", params={"chapter": 0})
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["scope"] == "episode"
        ids = [s["scene_id"] for s in data["scenes"]]
        assert len(ids) == 119
        assert ids[:3] == [SCENE_FIRST, SCENE_A, SCENE_B]
        assert ids[-1] == "scene_118"

    def test_sequence_scope_preserves_canonical_order(self, client, isolated_session_store, isolated_assets):
        """Порядок входных сцен не влияет: лента сортирует канонически."""
        resp = client.get("/studio/reel", params={"scene_ids": f"{SCENE_B},{SCENE_A}"})
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["scope"] == "sequence"
        assert [s["scene_id"] for s in data["scenes"]] == [SCENE_A, SCENE_B]

    def test_sequence_scope_reports_missing(self, client, isolated_session_store, isolated_assets):
        resp = client.get("/studio/reel", params={"scene_ids": f"{SCENE_A},нет_такой"})
        data = resp.json()["data"]
        assert [s["scene_id"] for s in data["scenes"]] == [SCENE_A]
        assert any("нет_такой" in lim for lim in data["limitations"])

    def test_unknown_scene_404(self, client, isolated_session_store, isolated_assets):
        resp = client.get("/studio/reel", params={"scene_id": "нет_такой"})
        assert resp.status_code == 404

    def test_film_scope_all_scenes_canonical_order(self, client, isolated_session_store, isolated_assets):
        """Без параметров — лента всего фильма: все 119 сцен каталога.

        Порядок канонический: scene_000 ... scene_118.
        """
        resp = client.get("/studio/reel")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["scope"] == "film"
        assert data["chapter"] is None
        ids = [s["scene_id"] for s in data["scenes"]]
        assert len(ids) == 119
        assert ids[:3] == [SCENE_FIRST, SCENE_A, SCENE_B]
        assert ids[-1] == "scene_118"
        chapters = [s["chapter"] for s in data["scenes"]]
        assert set(chapters) == {0}
        assert [s["order_global"] for s in data["scenes"]] == list(range(len(ids)))
        assert data["scene_ids"] == ids

    def test_film_scope_reports_episode_count(self, client, isolated_session_store, isolated_assets):
        data = client.get("/studio/reel").json()["data"]
        assert data["film"]["episode_count"] == 1
        assert data["summary"]["scene_count"] == 119
        assert data["summary"]["scene_count"] == len(data["scenes"])

    def test_scene_scope_reports_single_episode(self, client, isolated_session_store, isolated_assets):
        data = client.get("/studio/reel", params={"chapter": 0, "scene_id": SCENE_MEETING}).json()["data"]
        assert data["film"]["episode_count"] == 1
        assert data["chapter"] == 0


class TestReelSequence:
    def test_shot_order_and_transitions(self, client, isolated_session_store, isolated_assets):
        """Планы идут в порядке сценария; переход сохранён; сводка по длительности."""
        _make_session("test-user", SCENE_MEETING, shots=3)
        resp = client.get("/studio/reel", params={"scene_id": SCENE_MEETING})
        data = resp.json()["data"]
        seq = data["sequence"]
        assert [s["shot_id"] for s in seq] == ["shot_001", "shot_002", "shot_003"]
        assert all(s["kind"] == "placeholder" for s in seq)  # нет кадров и клипов
        assert data["summary"]["shot_count"] == 3
        assert data["summary"]["placeholder_count"] == 3
        assert data["summary"]["total_duration_sec"] == 9.0

    def test_clip_attached_by_shot_id(self, client, isolated_session_store, isolated_assets):
        _make_session("test-user", SCENE_MEETING, shots=2, shot_approved={"shot_001": "img_1"})
        _save_video(isolated_assets, SCENE_MEETING, "shot_001", provider="mock")

        data = client.get("/studio/reel", params={"scene_id": SCENE_MEETING}).json()["data"]
        assert data["scenes"][0]["shots"][0]["video"]["status"] == "mock"
        assert data["summary"]["clip_count"] == 1
        assert data["summary"]["mock_count"] == 1
        seq0 = data["sequence"][0]
        assert seq0["kind"] == "clip"
        assert seq0["clip_status"] == "mock"

    def test_frame_approved_becomes_frame_kind(self, client, isolated_session_store, isolated_assets):
        _make_session("test-user", SCENE_MEETING, shots=1, shot_approved={"shot_001": "img_1"})
        data = client.get("/studio/reel", params={"scene_id": SCENE_MEETING}).json()["data"]
        assert data["scenes"][0]["shots"][0]["frame"]["status"] == "approved"
        assert data["sequence"][0]["kind"] == "frame"
        assert data["sequence"][0]["frame_asset_id"] == "img_1"

    def test_continuity_next_between_shots(self, client, isolated_session_store, isolated_assets):
        _make_session("test-user", SCENE_MEETING, shots=2)
        data = client.get("/studio/reel", params={"scene_id": SCENE_MEETING}).json()["data"]
        cont = data["scenes"][0]["shots"][0]["continuity_next"]
        assert cont is not None
        assert cont["relation"] == "shots_within_scene"
        assert data["scenes"][0]["shots"][1]["continuity_next"] is None  # последний план сцены

    def test_cross_scene_boundary_relation(self, client, isolated_session_store, isolated_assets):
        _make_session("test-user", SCENE_A, shots=1)
        _make_session("test-user", SCENE_B, shots=1)
        data = client.get("/studio/reel", params={"scene_ids": f"{SCENE_A},{SCENE_B}"}).json()["data"]
        last_of_a = data["scenes"][0]["shots"][0]["continuity_next"]
        assert last_of_a["relation"] == "scene_boundary_shots"
        assert data["scenes"][1]["continuity_from_prev_scene"] is not None

    def test_transfer_marker_after_apply(self, client, isolated_session_store, isolated_assets):
        session_id = _make_session("test-user", SCENE_B, shots=2)
        client.post(f"/studio/{session_id}/continuity/apply", json={"note": "подогнать"})
        data = client.get("/studio/reel", params={"scene_id": SCENE_B}).json()["data"]
        transfer = data["scenes"][0]["transfer"]
        assert transfer is not None
        assert transfer["applied"] is True
        assert transfer["from_scene_id"] == SCENE_A


class TestReelVideoJobShotBinding:
    def test_video_job_request_accepts_shot_id(self):
        from core.dto.requests import VideoJobRequest

        req = VideoJobRequest(chapter=1, scene_id="s", prompt="p", shot_id="shot_001")
        assert req.shot_id == "shot_001"

    def test_shot_id_optional(self):
        from core.dto.requests import VideoJobRequest

        assert VideoJobRequest(chapter=1, scene_id="s", prompt="p").shot_id is None
