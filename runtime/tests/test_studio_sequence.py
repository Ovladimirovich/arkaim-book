"""Film Sequence (Фаза 4): план сборки последовательности фильма.

Offline (сеть не используется). Два уровня:
  - unit-тесты чистых функций studio.sequence (build_plan / segment_kind /
    executor_label / executor_key / fmt_timecode / render_plan_text);
  - интеграционные тесты маршрута GET /studio/sequence (область, тайминг,
    разрывы, исполнители, текст плана).

Ключевые проверки (OWNER-GO):
  1. Порядок отрезков берётся из канонических данных ленты (геном → сцены,
     сценарий → планы) и не переупорядочивается.
  2. Накопительный тайминг: start/end каждого отрезка монотонны.
  3. «Готов к сборке» — только реальный клип; mock, кадр, placeholder и
     устаревший клип — разрыв.
  4. Разрывы — непрерывные группы не-готовых отрезков.
  5. Сводка исполнителей по готовым клипам; флаг «смешанные исполнители».
  6. Текстовый план (раскадровка) — для внешнего монтажа, без MP4/ffmpeg.

Запуск (из runtime/):
  python -m pytest tests/test_studio_sequence.py -v
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

SCENE_MEETING = "test_meeting"  # index 4 главы 1


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture()
def isolated_session_store(tmp_path, monkeypatch):
    from studio import store as studio_store_mod

    monkeypatch.setattr(studio_store_mod, "_DB_PATH", tmp_path / "studio_sequence_test.db")
    yield


@pytest.fixture()
def isolated_assets(tmp_path, monkeypatch):
    from core.adc_deps import registry
    from visual_assets import storage as storage_mod

    monkeypatch.setattr(storage_mod, "_DATA_DIR", tmp_path / "visual_assets")
    store = storage_mod.AssetStorage(db_path=tmp_path / "sequence_assets.db")
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
    shot_approved: dict | None = None,
) -> str:
    from studio.scenario_schemas import ScenarioShot, VideoScenario
    from studio.store import StudioStore

    async def _inner():
        store = StudioStore()
        try:
            session = await store.create_session(user_id=user_id, title="sequence-тест", chapter=1, scene_id=scene_id)
            shot_list = []
            for i in range(shots):
                sid = f"shot_{i + 1:03d}"
                shot_list.append(
                    ScenarioShot(
                        shot_id=sid,
                        order=i,
                        shot_type="medium",
                        duration_sec=3.0,
                        transition_to_next="dissolve" if i == 0 else "",
                        approved_image_asset_id=(shot_approved or {}).get(sid),
                    )
                )
            scenario = VideoScenario(
                scenario_id="sc_seq",
                scene_id=scene_id,
                title="Сцена последовательности",
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
            return session.session_id
        finally:
            await store.close()

    return _run(_inner())


def _save_video(
    store,
    scene_id: str,
    shot_id: str | None,
    *,
    provider: str = "agnes",
    reference_image_id: str | None = None,
    prompt_used: str = "",
):
    from visual_assets.schemas import AssetStatus, AssetType, GenerationParams, VisualAsset
    from visual_assets.storage import generate_asset_id

    asset = VisualAsset(
        asset_id=generate_asset_id(),
        asset_type=AssetType.VIDEO,
        chapter=1,
        scene_id=scene_id,
        title="тестовый клип",
        status=AssetStatus.COMPLETED,
        prompt_used=prompt_used,
        generation=GenerationParams(
            provider=provider,
            backend=provider,
            shot_id=shot_id,
            reference_image_id=reference_image_id,
            art_direction_revision=None,
        ),
    )
    _run(store.save(asset))
    return asset


# ── Unit: чистые функции studio.sequence ─────────────────────────


def _shot(
    shot_id: str,
    index: int,
    *,
    duration: float = 3.0,
    clip_status: str = "none",
    frame_status: str = "none",
    frame_asset_id: str | None = None,
    transition: str = "",
    executor: dict | None = None,
    mock: bool = False,
) -> dict:
    return {
        "shot_id": shot_id,
        "order": index,
        "index": index,
        "duration_sec": duration,
        "transition_to_next": transition,
        "description": "",
        "frame": {"status": frame_status, "asset_id": frame_asset_id},
        "video": {
            "status": clip_status,
            "asset_id": f"clip_{shot_id}" if clip_status in ("ready", "mock", "stale") else None,
            "mock": mock,
            "stale_reasons": [],
            "executor": executor,
        },
    }


def _scene(scene_id: str, chapter: int, index_in_episode: int, shots: list[dict]) -> dict:
    return {
        "scene_id": scene_id,
        "chapter": chapter,
        "index_in_episode": index_in_episode,
        "shots": shots,
    }


class TestSegmentKindUnit:
    def test_clip_kind(self):
        from studio import sequence

        assert sequence.segment_kind("ready", "approved", "img") == sequence.SEG_KIND_CLIP
        assert sequence.segment_kind("mock", "none", None) == sequence.SEG_KIND_CLIP

    def test_frame_kind(self):
        from studio import sequence

        assert sequence.segment_kind("none", "approved", "img") == sequence.SEG_KIND_FRAME
        assert sequence.segment_kind("none", "none", "img") == sequence.SEG_KIND_FRAME

    def test_placeholder_kind(self):
        from studio import sequence

        assert sequence.segment_kind("none", "none", None) == sequence.SEG_KIND_PLACEHOLDER


class TestExecutorUnit:
    def test_label_provider_only(self):
        from studio import sequence

        assert sequence.executor_label({"provider": "agnes"}) == "agnes"

    def test_label_with_model(self):
        from studio import sequence

        assert sequence.executor_label({"provider": "comfyicu", "model": "ltx"}) == "comfyicu · ltx"

    def test_label_none(self):
        from studio import sequence

        assert sequence.executor_label(None) is None
        assert sequence.executor_label({}) is None

    def test_key_groups_by_full_identity(self):
        from studio import sequence

        a = sequence.executor_key({"provider": "agnes", "model": "m1"})
        b = sequence.executor_key({"provider": "agnes", "model": "m2"})
        assert a != b
        assert a == sequence.executor_key({"provider": "agnes", "model": "m1"})


class TestBuildPlanUnit:
    def test_empty_plan(self):
        from studio import sequence

        plan = sequence.build_plan([])
        assert plan["summary"]["segment_count"] == 0
        assert plan["segments"] == []
        assert plan["gaps"] == []
        assert plan["executor_mixed"] is False
        assert "План сборки" in sequence.render_plan_text(plan)

    def test_cumulative_timing(self):
        from studio import sequence

        scenes = [_scene("s1", 1, 0, [_shot("sh1", 0), _shot("sh2", 1), _shot("sh3", 2)])]
        plan = sequence.build_plan(scenes)
        assert [s["start_sec"] for s in plan["segments"]] == [0.0, 3.0, 6.0]
        assert [s["end_sec"] for s in plan["segments"]] == [3.0, 6.0, 9.0]
        assert plan["summary"]["total_duration_sec"] == 9.0

    def test_kind_counts(self):
        from studio import sequence

        scenes = [
            _scene(
                "s1",
                1,
                0,
                [
                    _shot("sh1", 0, clip_status="ready"),
                    _shot("sh2", 1, frame_status="approved", frame_asset_id="img2"),
                    _shot("sh3", 2),
                ],
            )
        ]
        plan = sequence.build_plan(scenes)
        assert plan["summary"]["clip_count"] == 1
        assert plan["summary"]["frame_count"] == 1
        assert plan["summary"]["placeholder_count"] == 1

    def test_only_real_clip_is_ready(self):
        from studio import sequence

        scenes = [
            _scene(
                "s1",
                1,
                0,
                [
                    _shot("ready1", 0, clip_status="ready", executor={"provider": "agnes"}),
                    _shot("mock1", 1, clip_status="mock", mock=True, executor={"provider": "mock"}),
                    _shot("stale1", 2, clip_status="stale", executor={"provider": "agnes"}),
                ],
            )
        ]
        plan = sequence.build_plan(scenes)
        assert plan["summary"]["ready_count"] == 1
        assert plan["summary"]["assembled_count"] == 1
        assert plan["assembled"][0]["shot_id"] == "ready1"
        assert plan["summary"]["mock_count"] == 1
        assert plan["summary"]["stale_count"] == 1

    def test_gaps_group_contiguous_non_ready(self):
        from studio import sequence

        scenes = [
            _scene(
                "s1",
                1,
                0,
                [
                    _shot("ready1", 0, clip_status="ready", executor={"provider": "agnes"}),
                    _shot("gap1", 1, frame_status="approved", frame_asset_id="i1"),
                    _shot("gap2", 2),
                    _shot("ready2", 3, clip_status="ready", executor={"provider": "agnes"}),
                ],
            )
        ]
        plan = sequence.build_plan(scenes)
        assert plan["summary"]["gap_count"] == 1
        gap = plan["gaps"][0]
        assert gap["start_index"] == 1
        assert gap["end_index"] == 2
        assert gap["segment_count"] == 2
        assert gap["start_sec"] == 3.0
        assert gap["end_sec"] == 9.0
        assert set(gap["kinds"]) == {"frame", "placeholder"}

    def test_executor_rollup_and_mixed_flag(self):
        from studio import sequence

        scenes = [
            _scene(
                "s1",
                1,
                0,
                [
                    _shot("a1", 0, clip_status="ready", executor={"provider": "agnes"}),
                    _shot("a2", 1, clip_status="ready", executor={"provider": "agnes"}),
                    _shot("b1", 2, clip_status="ready", executor={"provider": "comfyicu", "model": "ltx"}),
                ],
            )
        ]
        plan = sequence.build_plan(scenes)
        assert plan["executor_mixed"] is True
        assert plan["summary"]["executor_count"] == 2
        by_label = {e["label"]: e for e in plan["executors"]}
        assert by_label["agnes"]["count"] == 2
        assert by_label["comfyicu · ltx"]["count"] == 1
        assert by_label["agnes"]["duration_sec"] == 6.0

    def test_single_executor_not_mixed(self):
        from studio import sequence

        scenes = [_scene("s1", 1, 0, [_shot("a1", 0, clip_status="ready", executor={"provider": "agnes"})])]
        plan = sequence.build_plan(scenes)
        assert plan["executor_mixed"] is False
        assert plan["summary"]["executor_count"] == 1

    def test_scene_boundary_flag(self):
        from studio import sequence

        scenes = [
            _scene("s1", 1, 0, [_shot("a1", 0), _shot("a2", 1)]),
            _scene("s2", 1, 1, [_shot("b1", 0)]),
        ]
        plan = sequence.build_plan(scenes)
        flags = [s["scene_boundary_after"] for s in plan["segments"]]
        assert flags == [False, True, False]  # границы внутри s1 → s2, последний отрезок фильма — нет

    def test_transitions_between_segments(self):
        from studio import sequence

        scenes = [
            _scene("s1", 1, 0, [_shot("a1", 0, transition="dissolve"), _shot("a2", 1)]),
        ]
        plan = sequence.build_plan(scenes)
        assert len(plan["transitions"]) == 1
        assert plan["transitions"][0]["transition"] == "dissolve"
        assert plan["transitions"][0]["from_shot_id"] == "a1"

    def test_plan_does_not_reorder_scenes(self):
        from studio import sequence

        scenes = [
            _scene("s1", 1, 0, [_shot("a1", 0)]),
            _scene("s2", 2, 0, [_shot("b1", 0)]),
        ]
        plan = sequence.build_plan(scenes)
        assert [s["scene_id"] for s in plan["segments"]] == ["s1", "s2"]
        assert plan["summary"]["scene_count"] == 2


class TestTimecodeUnit:
    def test_timecode(self):
        from studio import sequence

        assert sequence.fmt_timecode(0) == "00:00:00"
        assert sequence.fmt_timecode(63) == "00:01:03"
        assert sequence.fmt_timecode(3661) == "01:01:01"


class TestRenderPlanTextUnit:
    def test_contains_header_and_lines(self):
        from studio import sequence

        scenes = [
            _scene(
                "s1",
                1,
                0,
                [
                    _shot("a1", 0, clip_status="ready", executor={"provider": "agnes"}, transition="cut"),
                    _shot("a2", 1),
                ],
            )
        ]
        plan = sequence.build_plan(scenes)
        text = sequence.render_plan_text(plan)
        assert "План сборки последовательности фильма" in text
        assert "эп.1 сцена s1 → план a1" in text
        assert "готово" in text
        assert "Разрывы (нет готового клипа)" in text
        assert "a2" in text

    def test_mixed_executors_note(self):
        from studio import sequence

        scenes = [
            _scene(
                "s1",
                1,
                0,
                [
                    _shot("a1", 0, clip_status="ready", executor={"provider": "agnes"}),
                    _shot("a2", 1, clip_status="ready", executor={"provider": "comfyicu"}),
                ],
            )
        ]
        text = sequence.render_plan_text(sequence.build_plan(scenes))
        assert "Смешанные исполнители" in text


# ── Интеграция: GET /studio/sequence ─────────────────────────────


class TestSequenceRoute:
    def test_scope_scene_empty(self, client, isolated_session_store, isolated_assets):
        _make_session("test-user", SCENE_MEETING, shots=2)
        resp = client.get("/studio/sequence", params={"chapter": 1, "scene_id": SCENE_MEETING})
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["scope"] == "scene"
        assert data["summary"]["segment_count"] == 2
        assert data["summary"]["ready_count"] == 0
        assert data["summary"]["gap_count"] == 1
        assert data["summary"]["total_duration_sec"] == 6.0
        assert data["plan_text"]

    def test_ready_clip_is_assembled(self, client, isolated_session_store, isolated_assets):
        _make_session("test-user", SCENE_MEETING, shots=2, shot_approved={"shot_001": "img_1"})
        video = _save_video(isolated_assets, SCENE_MEETING, "shot_001", provider="agnes", reference_image_id="img_1")

        data = client.get("/studio/sequence", params={"chapter": 1, "scene_id": SCENE_MEETING}).json()["data"]
        assert data["summary"]["clip_count"] == 1
        assert data["summary"]["ready_count"] == 1
        assert data["summary"]["assembled_count"] == 1
        assert data["summary"]["assembled_duration_sec"] == 3.0
        assert len(data["assembled"]) == 1
        assert data["assembled"][0]["shot_id"] == "shot_001"
        assert data["assembled"][0]["clip_asset_id"] == video.asset_id
        # Второй план без клипа — разрыв.
        assert data["summary"]["gap_count"] == 1

    def test_mock_clip_is_gap_not_assembled(self, client, isolated_session_store, isolated_assets):
        _make_session("test-user", SCENE_MEETING, shots=1, shot_approved={"shot_001": "img_1"})
        _save_video(isolated_assets, SCENE_MEETING, "shot_001", provider="mock")

        data = client.get("/studio/sequence", params={"chapter": 1, "scene_id": SCENE_MEETING}).json()["data"]
        assert data["summary"]["clip_count"] == 1
        assert data["summary"]["mock_count"] == 1
        assert data["summary"]["ready_count"] == 0
        assert data["summary"]["assembled_count"] == 0
        assert data["summary"]["gap_count"] == 1

    def test_film_scope_by_default(self, client, isolated_session_store, isolated_assets):
        _make_session("test-user", SCENE_MEETING, shots=2)
        data = client.get("/studio/sequence").json()["data"]
        assert data["scope"] == "film"
        assert data["chapter"] is None
        assert data["summary"]["segment_count"] == 2
        # Без параметров — весь фильм: все эпизоды генома (главы 1..5).
        assert data["film"]["episode_count"] == 5

    def test_unknown_scene_404(self, client, isolated_session_store, isolated_assets):
        resp = client.get("/studio/sequence", params={"chapter": 1, "scene_id": "нет_такой"})
        assert resp.status_code == 404

    def test_missing_scene_in_limitations(self, client, isolated_session_store, isolated_assets):
        data = client.get("/studio/sequence", params={"chapter": 1, "scene_ids": f"{SCENE_MEETING},нет_такой"}).json()["data"]
        assert data["scope"] == "sequence"
        assert any("нет_такой" in lim for lim in data["limitations"])

    def test_edl_xml_present_with_ready_clip(self, client, isolated_session_store, isolated_assets):
        _make_session("test-user", SCENE_MEETING, shots=1, shot_approved={"shot_001": "img_1"})
        _save_video(isolated_assets, SCENE_MEETING, "shot_001", provider="agnes", reference_image_id="img_1")

        data = client.get("/studio/sequence", params={"chapter": 1, "scene_id": SCENE_MEETING}).json()["data"]
        assert data.get("edl_xml")
        assert "<?xml version" in data["edl_xml"]
        assert "<ready_clips>1</ready_clips>" in data["edl_xml"]
        assert "<clip_001>" in data["edl_xml"] or "shot_001" in data["edl_xml"]

    def test_edl_xml_empty_when_no_ready_clips(self, client, isolated_session_store, isolated_assets):
        _make_session("test-user", SCENE_MEETING, shots=2)

        data = client.get("/studio/sequence", params={"chapter": 1, "scene_id": SCENE_MEETING}).json()["data"]
        assert data.get("edl_xml")
        assert "<ready_clips>0</ready_clips>" in data["edl_xml"]
        assert "<clips>" in data["edl_xml"]


# ── Unit: render_edl ────────────────────────────────────────────


class TestRenderEdlUnit:
    def test_empty_assembled(self):
        from studio import sequence

        plan = sequence.build_plan([])
        edl = sequence.render_edl(plan)
        assert "<?xml version" in edl
        assert "<ready_clips>0</ready_clips>" in edl
        assert "<clips>" in edl
        assert "</clips>" in edl

    def test_single_ready_clip(self):
        from studio import sequence

        scenes = [
            _scene(
                "s1",
                1,
                0,
                [
                    _shot("sh1", 0, clip_status="ready", executor={"provider": "agnes"}, transition="cut"),
                ],
            )
        ]
        plan = sequence.build_plan(scenes)
        edl = sequence.render_edl(plan, book_title="Тестовый фильм")
        assert "Тестовый фильм" in edl
        assert "<ready_clips>1</ready_clips>" in edl
        assert "<shot_id>sh1</shot_id>" in edl
        assert "<executor>agnes</executor>" in edl
        assert "<transition>cut</transition>" in edl
        assert "<start_sec>0.0</start_sec>" in edl
        assert "<duration_sec>3.0</duration_sec>" in edl

    def test_mock_clip_not_in_edl(self):
        from studio import sequence

        scenes = [
            _scene(
                "s1",
                1,
                0,
                [
                    _shot("sh1", 0, clip_status="mock", mock=True, executor={"provider": "mock"}),
                ],
            )
        ]
        plan = sequence.build_plan(scenes)
        edl = sequence.render_edl(plan)
        assert "<ready_clips>0</ready_clips>" in edl
        # Mock-клип не попадает в assembled → нет записи <clip>
        assert plan["summary"]["ready_count"] == 0
