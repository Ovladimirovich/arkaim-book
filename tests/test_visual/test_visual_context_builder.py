"""Tests for VisualContextBuilder."""
import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "core" / "CORE"))
from visual.visual_context_builder import VisualContextBuilder

@pytest.fixture
def genome():
    return {
        "modules": {
            "scenes": [{"chapter": 1, "scene_id": "scene_01", "title": "Рассвет", "characters": ["Велик"], "location": "Аркаим", "emotion": "sacred_glow", "meaning_tags": ["stone_circle"]}],
            "character_visuals": [{"character_id": "Велик", "age_range": "25-30", "face": "angular"}],
            "location_visuals": [{"location_id": "Аркаим", "type": "ancient_settlement"}],
            "characters": [{"id": "Велик", "name": "Велик"}],
        },
        "world_entities": [{"id": "Аркаим", "description": "Древнее поселение"}],
    }

@pytest.fixture
def builder(genome):
    return VisualContextBuilder(genome=genome)

class TestVisualContextBuilder:
    @pytest.mark.asyncio
    async def test_build_returns_visual_context(self, builder):
        ctx = await builder.build(chapter=1, scene_id="scene_01")
        assert ctx is not None
        assert ctx.scene is not None
        assert ctx.location is not None
        assert ctx.emotion is not None

    @pytest.mark.asyncio
    async def test_build_with_time_of_day(self, builder):
        ctx = await builder.build(chapter=1, scene_id="scene_01", time_of_day="night")
        assert ctx is not None
