"""Tests for VisualValidator."""
import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "core" / "CORE"))
from visual.visual_validator import VisualValidator
from visual.visual_context import VisualContext
from visual.visual_models import *

def _make_valid():
    return VisualContext(
        scene=SceneContext(chapter=1, scene_id="s1", title="Test"),
        location=LocationContext(location_id="test", name="Test",
            architecture=ArchitectureContext(style="stone", materials="stone", features=[], age="old"),
            landscape=LandscapeContext(terrain="plain", vegetation="grass", water="", sky="clear")),
        environment=EnvironmentContext(weather="clear", season="summer", time_of_day="day"),
        lighting=LightingContext(source="sun", direction="east", color="golden", intensity="bright"),
        palette=PaletteContext(primary=["#FF0000"], description="red"),
        atmosphere=AtmosphereContext(name="neutral", light="bright", fog="", wind="", particles="", sound="", color_temperature="neutral", contrast="medium", camera_dynamics="static"),
        symbols=[], historical=HistoricalContext(era="modern", civilization="test"),
        camera=CameraContext(shot_type="wide", angle="eye_level", movement="static", lens="24mm"),
        style=StyleContext(name="realistic", prefix="photorealistic"),
        emotion=EmotionContext(name="neutral", visual="clear", suffix="", intensity=0.5),
        characters=[], negative_prompt=NegativePromptContext(base=[], extra=[]),
    )

class TestVisualValidator:
    def test_valid_context_passes(self):
        result = VisualValidator().validate(_make_valid())
        assert result.ok

    def test_missing_title_fails(self):
        ctx = _make_valid()
        ctx.scene = SceneContext(chapter=1, scene_id="", title="")
        result = VisualValidator().validate(ctx)
        assert not result.ok
