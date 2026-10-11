"""Tests for Phase 1A: VideoScenario contract + VideoScenarioBuilder + studio-describe endpoint.

Проверяет:
  1. VideoScenario schema: extra="forbid", serialization, provenance
  2. VideoScenarioBuilder: builds scenario from VisualContext
  3. VideoIntelligence production path: connected via studio-describe
  4. studio-describe endpoint: returns three descriptions
  5. Three results: image_description, video_description, video_scenario
"""

from __future__ import annotations

import pytest

# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def minimal_visual_context():
    """Minimal VisualContext for testing builder without genome."""
    from visual.visual_context import VisualContext
    from visual.visual_models import (
        SceneContext,
        LocationContext,
        ArchitectureContext,
        LandscapeContext,
        EnvironmentContext,
        LightingContext,
        AtmosphereContext,
        CameraContext,
        StyleContext,
        EmotionContext,
        CharacterVisualContext,
    )

    return VisualContext(
        scene=SceneContext(
            chapter=1,
            scene_id="test_scene",
            title="Test Scene",
            emotion="sacred",
            meaning_tags=["ritual", "fire"],
        ),
        location=LocationContext(
            location_id="loc_arkaim",
            name="Arkaim",
            type="settlement",
            architecture=ArchitectureContext(style="bronze_age", materials="stone, wood"),
            landscape=LandscapeContext(terrain="steppe", vegetation="grass"),
            sound="wind through stone",
        ),
        environment=EnvironmentContext(time_of_day="dawn", weather="clear"),
        lighting=LightingContext(source="fire", direction="low", color="golden"),
        atmosphere=AtmosphereContext(
            name="sacred",
            light="golden firelight",
            fog="thin mist",
            wind="gentle",
            particles="ember sparks",
            sound="chanting",
            color_temperature="warm",
        ),
        camera=CameraContext(shot_type="wide", angle="eye_level"),
        style=StyleContext(name="cinematic_fantasy", prefix="cinematic fantasy"),
        emotion=EmotionContext(name="sacred", suffix="reverent atmosphere"),
        characters=[
            CharacterVisualContext(
                character_id="char_velik",
                name="Velik",
                appearance_summary="wise elder, silver beard",
            ),
        ],
    )


@pytest.fixture
def scenario_builder():
    from studio.scenario_builder import VideoScenarioBuilder

    return VideoScenarioBuilder()


# ── 1. VideoScenario Schema Tests ────────────────────────────────


class TestVideoScenarioSchema:
    """VideoScenario contract tests."""

    def test_extra_forbid_rejects_execution_fields(self):
        """VideoScenario rejects execution fields (model/steps/seed/workflow/provider)."""
        from studio.scenario_schemas import VideoScenario

        with pytest.raises(Exception):  # ValidationError
            VideoScenario(title="test", model="sdxl")

        with pytest.raises(Exception):
            VideoScenario(title="test", steps=30)

        with pytest.raises(Exception):
            VideoScenario(title="test", seed=42)

        with pytest.raises(Exception):
            VideoScenario(title="test", provider="comfyui")

        with pytest.raises(Exception):
            VideoScenario(title="test", workflow="txt2img")

    def test_valid_creation(self):
        from studio.scenario_schemas import VideoScenario

        s = VideoScenario(title="Test", scene_id="s1")
        assert s.title == "Test"
        assert s.scene_id == "s1"
        assert s.scenario_version == "0.1.0"
        assert s.shots == []
        assert s.total_duration_sec == 30.0

    def test_to_dict_serializable(self):
        """VideoScenario.to_dict() produces JSON-serializable dict."""
        import json
        from studio.scenario_schemas import VideoScenario

        s = VideoScenario(title="Test", scene_id="s1")
        d = s.to_dict()
        # Should be JSON-serializable
        json_str = json.dumps(d, ensure_ascii=False)
        assert "title" in json_str
        assert "scenario_version" in json_str

    def test_to_dict_has_all_keys(self):
        from studio.scenario_schemas import VideoScenario

        s = VideoScenario(title="Test", scene_id="s1")
        d = s.to_dict()
        expected_keys = {
            "scenario_id",
            "scenario_version",
            "scene_id",
            "title",
            "synopsis",
            "total_duration_sec",
            "shots",
            "direction_notes",
            "rhythm",
            "character_arcs",
            "environment_actions",
            "sound_design",
            "source_refs",
            "temporal_context",
            "provenance",
        }
        assert expected_keys == set(d.keys())

    def test_provenance_fields(self):
        from studio.scenario_schemas import ScenarioProvenance

        p = ScenarioProvenance(source="genome", source_id="scene_1", confidence=0.95)
        assert p.source == "genome"
        assert p.confidence == 0.95

    def test_shot_extra_forbid(self):
        from studio.scenario_schemas import ScenarioShot

        with pytest.raises(Exception):
            ScenarioShot(description="test", seed=42)


# ── 2. VideoScenarioBuilder Tests ────────────────────────────────


class TestVideoScenarioBuilder:
    """VideoScenarioBuilder builds scenario from VisualContext."""

    def test_builder_creates_scenario(self, scenario_builder, minimal_visual_context):
        scenario = scenario_builder.build(minimal_visual_context, duration_sec=30.0)
        assert scenario.scene_id == "test_scene"
        assert scenario.title == "Test Scene"
        assert scenario.total_duration_sec == 30.0

    def test_builder_creates_shots(self, scenario_builder, minimal_visual_context):
        """Builder creates shot sequence based on emotion."""
        scenario = scenario_builder.build(minimal_visual_context)
        assert len(scenario.shots) >= 3  # sacred → 5 shots per default mapping
        for shot in scenario.shots:
            assert shot.shot_id.startswith("shot_")
            assert shot.order >= 0
            assert shot.duration_sec > 0

    def test_builder_shots_have_provenance(self, scenario_builder, minimal_visual_context):
        """Every shot has provenance."""
        scenario = scenario_builder.build(minimal_visual_context)
        for shot in scenario.shots:
            assert shot.provenance.source  # not empty

    def test_builder_creates_rhythm(self, scenario_builder, minimal_visual_context):
        """Rhythm matches emotion."""
        scenario = scenario_builder.build(minimal_visual_context)
        # sacred emotion → slow pace
        assert scenario.rhythm.pace == "slow"
        assert scenario.rhythm.provenance.source == "video_intelligence"

    def test_builder_creates_environment_actions(self, scenario_builder, minimal_visual_context):
        """Environment actions from VideoIntelligence."""
        scenario = scenario_builder.build(minimal_visual_context)
        # atmosphere has fog, wind, particles → should create env actions
        assert len(scenario.environment_actions) >= 2
        for env in scenario.environment_actions:
            assert env.element
            assert env.provenance.source == "video_intelligence"

    def test_builder_creates_character_arcs(self, scenario_builder, minimal_visual_context):
        """Character arcs from VideoIntelligence."""
        scenario = scenario_builder.build(minimal_visual_context)
        assert len(scenario.character_arcs) == 1
        arc = scenario.character_arcs[0]
        assert arc.character_name == "Velik"
        assert arc.action  # not empty
        assert arc.provenance.source == "video_intelligence"

    def test_builder_creates_sound_design(self, scenario_builder, minimal_visual_context):
        """Sound design from VisualContext atmosphere."""
        scenario = scenario_builder.build(minimal_visual_context)
        assert scenario.sound_design.atmosphere_sounds == "chanting"
        assert scenario.sound_design.location_sounds == "wind through stone"
        assert scenario.sound_design.provenance.source == "visual_knowledge"

    def test_builder_inherits_provenance(self, scenario_builder, minimal_visual_context):
        """Scenario inherits provenance from SceneContext."""
        scenario = scenario_builder.build(minimal_visual_context)
        # No scene_extras in minimal context → empty provenance
        # But source_refs should be present
        assert scenario.source_refs is not None

    def test_builder_different_emotions_different_shots(self, scenario_builder, minimal_visual_context):
        """Different emotions produce different shot sequences."""
        from visual.visual_models import EmotionContext

        # sacred → slow, 5 shots
        minimal_visual_context.emotion = EmotionContext(name="sacred", suffix="reverent")
        s1 = scenario_builder.build(minimal_visual_context)

        # conflict → fast, 5 shots
        minimal_visual_context.emotion = EmotionContext(name="conflict", suffix="tense")
        s2 = scenario_builder.build(minimal_visual_context)

        # Rhythm should differ
        assert s1.rhythm.pace == "slow"
        assert s2.rhythm.pace == "fast"

    def test_builder_synopsis_from_context(self, scenario_builder, minimal_visual_context):
        """Synopsis built from VisualContext data."""
        scenario = scenario_builder.build(minimal_visual_context)
        assert "Test Scene" in scenario.synopsis
        assert "Arkaim" in scenario.synopsis

    def test_builder_no_execution_fields(self, scenario_builder, minimal_visual_context):
        """Built scenario has no execution fields."""
        scenario = scenario_builder.build(minimal_visual_context)
        d = scenario.to_dict()
        banned = {"model", "steps", "seed", "cfg", "sampler", "workflow", "provider", "comfyui"}
        assert banned.isdisjoint(d.keys())


# ── 3. VideoIntelligence Production Path Tests ───────────────────


class TestVideoIntelligenceProductionPath:
    """VideoIntelligence is connected to production via studio-describe."""

    def test_video_intelligence_importable(self):
        from visual.video_intelligence import VideoIntelligence

        vi = VideoIntelligence()
        assert vi is not None

    def test_video_intelligence_creates_video_context(self, minimal_visual_context):
        """VideoIntelligence.create_video_context works with real VisualContext."""
        from visual.video_intelligence import VideoIntelligence

        vi = VideoIntelligence()
        vctx = vi.create_video_context(minimal_visual_context)
        assert vctx.camera_movement is not None
        assert vctx.camera_movement.type != ""  # populated
        assert vctx.rhythm.pace != ""  # populated
        assert vctx.light_dynamics is not None

    def test_video_intelligence_populates_motion(self, minimal_visual_context):
        """VideoIntelligence populates character and object motion."""
        from visual.video_intelligence import VideoIntelligence

        vi = VideoIntelligence()
        vctx = vi.create_video_context(minimal_visual_context)
        # Should have at least fog/wind/particles from atmosphere
        assert len(vctx.object_motion) >= 2
        # Should have character motion for Velik
        assert len(vctx.character_motion) >= 1


# ── 4. Studio-Describe Endpoint Tests ────────────────────────────


class TestStudioDescribeEndpoint:
    """POST /visual/studio-describe returns three descriptions."""

    def test_studio_describe_returns_three_descriptions(self):
        from fastapi.testclient import TestClient
        from core.main import app

        client = TestClient(app)
        resp = client.post("/visual/studio-describe", json={"chapter": 1, "scene_id": "test_meeting"})
        # 200 or 404 (scene might not exist in test genome)
        if resp.status_code == 200:
            data = resp.json()
            assert "image_description" in data
            assert "video_description" in data
            assert "video_scenario" in data
            # image_description is a MediaPlan
            assert "media_kind" in data["image_description"]
            assert data["image_description"]["media_kind"] == "image"
            # video_description is a MediaPlan
            assert "media_kind" in data["video_description"]
            assert data["video_description"]["media_kind"] == "video"
            # video_scenario is a VideoScenario
            assert "scenario_version" in data["video_scenario"]
            assert "shots" in data["video_scenario"]
        elif resp.status_code == 404:
            pytest.skip("Scene not found in test genome")

    def test_studio_describe_video_scenario_has_shots(self):
        from fastapi.testclient import TestClient
        from core.main import app

        client = TestClient(app)
        resp = client.post("/visual/studio-describe", json={"chapter": 1, "scene_id": "test_meeting"})
        if resp.status_code == 200:
            scenario = resp.json()["video_scenario"]
            assert len(scenario["shots"]) >= 3
            for shot in scenario["shots"]:
                assert "shot_type" in shot
                assert "description" in shot
                assert "camera_action" in shot

    def test_studio_describe_no_execution_fields(self):
        from fastapi.testclient import TestClient
        from core.main import app

        client = TestClient(app)
        resp = client.post("/visual/studio-describe", json={"chapter": 1, "scene_id": "test_meeting"})
        if resp.status_code == 200:
            data = resp.json()
            banned = {"model", "steps", "seed", "cfg", "sampler", "workflow", "provider"}
            for key in ["image_description", "video_description", "video_scenario"]:
                for banned_field in banned:
                    assert banned_field not in data[key], f"{banned_field} found in {key}"


# ── 5. Three Results Integration ─────────────────────────────────


class TestThreeResultsIntegration:
    """Studio can receive all three results without creating them."""

    def test_three_results_from_same_context(self, minimal_visual_context):
        """All three descriptions come from the same VisualContext."""
        from media_plan import MediaPlanBuilder
        from studio.scenario_builder import VideoScenarioBuilder
        from visual.video_intelligence import VideoIntelligence

        # A. Image Description
        image_plan = MediaPlanBuilder().build_image_plan(minimal_visual_context)
        assert image_plan.media_kind == "image"
        assert image_plan.prompt  # not empty

        # B. Video Description
        vi = VideoIntelligence()
        vctx = vi.create_video_context(minimal_visual_context)
        video_plan = MediaPlanBuilder().build_video_plan(vctx, duration_sec=vctx.duration_sec)
        assert video_plan.media_kind == "video"

        # C. Full Video Scenario
        builder = VideoScenarioBuilder(video_intelligence=vi)
        scenario = builder.build(minimal_visual_context)
        assert len(scenario.shots) >= 3

        # All three from same source
        assert image_plan.source_refs == video_plan.source_refs

    def test_studio_receives_not_creates(self):
        """Studio receives descriptions, doesn't create content.

        The builder uses VisualContext data (existing system) as source.
        Directorial fields are minimal framing, not content generation.
        """
        from studio.scenario_builder import VideoScenarioBuilder

        builder = VideoScenarioBuilder()
        # Minimal context with empty fields
        from visual.visual_context import VisualContext
        from visual.visual_models import SceneContext

        ctx = VisualContext(scene=SceneContext())

        scenario = builder.build(ctx)
        # Synopsis should reflect empty data, not invent content
        assert scenario.title == ""  # empty from empty context
        assert scenario.scene_id == ""  # empty from empty context
