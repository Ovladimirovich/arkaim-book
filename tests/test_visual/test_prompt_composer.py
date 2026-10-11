"""Tests for PromptComposer."""
import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "core" / "CORE"))
from visual.prompt_composer import PromptComposer
from visual.visual_context import VisualContext
from visual.visual_models import *

def _make_context():
    return VisualContext(
        scene=SceneContext(chapter=1, scene_id="s1", title="Dawn over Arkaim"),
        location=LocationContext(location_id="arkaim", name="Arkaim",
            architecture=ArchitectureContext(style="Bronze Age stone", materials="stone", features=["walls"], age="3500 BC"),
            landscape=LandscapeContext(terrain="steppe", vegetation="grass", water="river", sky="vast")),
        environment=EnvironmentContext(weather="clear", season="summer", time_of_day="dawn"),
        lighting=LightingContext(source="sun", direction="east", color="golden", intensity="soft"),
        palette=PaletteContext(primary=["#DAA520", "#8B4513"], description="warm earth tones"),
        atmosphere=AtmosphereContext(name="pre_dawn", light="golden", fog="mist", wind="still", particles="dust", sound="silence", color_temperature="warm", contrast="soft", camera_dynamics="slow pan"),
        symbols=[], historical=HistoricalContext(era="Bronze Age", civilization="Arkaic"),
        camera=CameraContext(shot_type="wide", angle="eye_level", movement="static", lens="24mm", composition="rule_of_thirds"),
        style=StyleContext(name="cinematic_fantasy", prefix="cinematic fantasy, epic film still"),
        emotion=EmotionContext(name="sacred", visual="golden light", suffix="divine", intensity=0.8),
        characters=[CharacterVisualContext(character_id="velik", name="Velik", appearance_summary="young warrior")],
        negative_prompt=NegativePromptContext(base=["ugly", "blurry"], extra=[]),
    )

class TestPromptComposer:
    def test_comfyui(self):
        prompt, negative = PromptComposer(generator="comfyui").compose_pair(_make_context())
        assert len(prompt) > 50
        assert isinstance(negative, str)

    def test_flux(self):
        prompt, _ = PromptComposer(generator="flux").compose_pair(_make_context())
        assert len(prompt) > 30

    def test_kling(self):
        prompt, _ = PromptComposer(generator="kling").compose_pair(_make_context())
        assert len(prompt) > 30

    def test_runway(self):
        prompt, _ = PromptComposer(generator="runway").compose_pair(_make_context())
        assert len(prompt) > 30

    def test_hailuo(self):
        prompt, _ = PromptComposer(generator="hailuo").compose_pair(_make_context())
        assert len(prompt) > 20
