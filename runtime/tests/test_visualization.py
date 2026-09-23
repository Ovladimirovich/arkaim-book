"""Visualization Layer tests."""
import sys
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "ARKAIM_DIGITAL_CONSCIOUSNESS" / "CORE"
sys.path.insert(0, str(CORE_DIR))

import pytest
import asyncio


def test_image_provider_mock():
    """MockImageProvider возвращает SVG."""
    from providers.image.mock import MockImageProvider
    provider = MockImageProvider()

    async def _check():
        health = await provider.health()
        assert health is True
        data = await provider.generate("test")
        assert b"<svg" in data
    asyncio.run(_check())


def test_scene_engine_no_genome():
    """SceneEngine возвращает None при пустом геноме."""
    from visualization.scene_engine import SceneEngine
    engine = SceneEngine(genome={})
    assert engine.get_scene(1, "s1") is None


def test_character_visualizer_fallback():
    """CharacterVisualizer строит визуал из character."""
    from visualization.character_visualizer import CharacterVisualizer
    genome = {"modules": {"characters": [{"id": "c1", "description": "Hero"}]}}
    viz = CharacterVisualizer(genome)
    result = viz.visualize("c1")
    assert result["character_id"] == "c1"
    assert "clothing" in result


def test_world_visualizer_fallback():
    """WorldVisualizer строит локацию из world_entity."""
    from visualization.world_visualizer import WorldVisualizer
    genome = {"world_entities": [{"name": "Arcadia", "description": "Mountain"}]}
    viz = WorldVisualizer(genome)
    result = viz.visualize("Arcadia")
    assert result["location_id"] == "Arcadia"
    assert "architecture" in result


def test_prompt_builder_default():
    """PromptBuilder возвращает полноценный промпт из Visual Genome."""
    from visualization.prompt_builder import PromptBuilder
    from pulse.layers import BaseLayer
    class FakePulse:
        layers = {"visual_style": BaseLayer({})}
    pb = PromptBuilder(FakePulse())
    scene = {"title": "Battle at Dawn", "characters": ["hero"], "emotion": "hopeful_golden"}
    cv = {"hero": {"age_range": "25", "clothing": "steel armor", "color_palette": ["#FFD700"]}}
    loc = {"type": "mountain", "architecture": "rocky peaks", "atmosphere": "misty"}
    prompt = pb.build_scene_prompt(scene, cv, loc)
    assert "Battle at Dawn" in prompt
    assert "steel armor" in prompt
    assert "rocky peaks" in prompt
    assert "misty" in prompt

def test_prompt_builder_negative():
    """build_negative_prompt возвращает непустой negative prompt."""
    from visualization.prompt_builder import PromptBuilder
    class FakePulse:
        layers = {}
    pb = PromptBuilder(FakePulse())
    neg = pb.build_negative_prompt({})
    assert len(neg) > 50
    assert "blurry" in neg
    assert "cartoon" in neg

def test_prompt_builder_full_pair():
    """build_full_prompt_pair возвращает (positive, negative)."""
    from visualization.prompt_builder import PromptBuilder
    class FakePulse:
        layers = {}
    pb = PromptBuilder(FakePulse())
    pos, neg = pb.build_full_prompt_pair({"title": "Test", "characters": ["ch1"]}, {"ch1": {}}, {})
    assert isinstance(pos, str)
    assert isinstance(neg, str)
    assert len(pos) > 20
    assert len(neg) > 50

def test_prompt_builder_emotion_mapping():
    """Все эмоции из EMOTION_MAP имеют визуальное описание."""
    from visualization.prompt_builder import EMOTION_TO_VISUAL, EMOTION_SUFFIX
    for emotion, visual in EMOTION_TO_VISUAL.items():
        assert len(visual) > 5, f"Emotion {emotion} has no visual description"
    for emotion, suffix in EMOTION_SUFFIX.items():
        assert len(suffix) > 5, f"Emotion {emotion} has no suffix"

def test_prompt_builder_location_types():
    """Все типы локаций имеют визуальное описание."""
    from visualization.prompt_builder import LOCATION_TYPE_VISUALS
    for loc_type, visual in LOCATION_TYPE_VISUALS.items():
        assert len(visual) > 5, f"Location {loc_type} has no visual"

def test_prompt_builder_uses_all_fields():
    """Промпт содержит данные из всех полей."""
    from visualization.prompt_builder import PromptBuilder, EMOTION_TO_VISUAL
    class FakePulse:
        layers = {}
    pb = PromptBuilder(FakePulse())
    scene = {
        "title": "Test Scene",
        "characters": ["ch1"],
        "emotion": "dark_mystical",
        "meaning_tags": ["theme:wisdom"],
        "visual_style_hint": "chiaroscuro",
        "color_palette": ["#1A1A2E", "#533483"],
    }
    cv = {"ch1": {
        "age_range": "40", "build": "muscular", "hair": "long black",
        "eyes": "amber", "clothing": "dark robes",
        "accessories": ["ring", "staff"], "color_palette": ["#2C3E50"],
        "style_constants": ["dramatic shadow"],
    }}
    loc = {
        "type": "cave", "architecture": "crystalline formations",
        "atmosphere": "eerie", "lighting": "dim blue glow",
        "palette": ["#0F3460"],
    }
    prompt = pb.build_scene_prompt(scene, cv, loc)
    # Все поля должны быть в промпте
    assert "dark robes" in prompt
    assert "long black" in prompt  # hair
    assert "amber" in prompt  # eyes
    assert "muscular" in prompt  # build
    assert "ring" in prompt and "staff" in prompt  # accessories
    assert "crystalline formations" in prompt  # architecture
    assert "eerie" in prompt  # atmosphere
    assert "dim blue glow" in prompt  # lighting
    assert "dramatic shadow" in prompt  # style_constants


pytest.register_assert_rewrite("runtime.tests.test_visualization")