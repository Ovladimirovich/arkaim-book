"""Tests for visualization/meaning_to_visual.py"""
import pytest
import sys
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
sys.path.insert(0, str(CORE_DIR))

from visualization.meaning_to_visual import (
    generate_visuals_from_meaning,
    EMOTION_MAP,
    PALETTE_MAP,
)


class TestGenerateVisualsFromMeaning:
    def test_returns_scenes_and_presets(self):
        genome = {
            "modules": {
                "themes": [{"name": "Утрата", "description": "потеря и смирение"}],
                "values": [{"name": "Надежда", "description": "вера в лучшее"}],
            },
        }
        scenes, presets = generate_visuals_from_meaning(genome)
        assert len(scenes) >= 1
        assert len(presets) >= 1

    def test_emotion_detected(self):
        genome = {
            "modules": {
                "themes": [{"name": "Мистика", "description": "тайна и магия"}],
                "values": [{"name": "Просветление", "description": "озарение"}],
            },
        }
        scenes, presets = generate_visuals_from_meaning(genome)
        primary_emotion = presets[0]["preset_id"]
        assert "мистика" in primary_emotion or "просветление" in primary_emotion

    def test_no_emotions_returns_empty(self):
        genome = {"modules": {}}
        scenes, presets = generate_visuals_from_meaning(genome)
        assert scenes == []
        assert presets == []

    def test_palette_has_colors(self):
        genome = {
            "modules": {
                "themes": [{"name": "Утрата", "description": "потеря"}],
            },
        }
        scenes, presets = generate_visuals_from_meaning(genome)
        for scene in scenes:
            palette = scene.get("color_palette", [])
            assert len(palette) >= 1
            for color in palette:
                assert color.startswith("#")

    def test_style_preset_has_required_fields(self):
        genome = {
            "modules": {
                "themes": [{"name": "Надежда", "description": "вера"}],
            },
        }
        scenes, presets = generate_visuals_from_meaning(genome)
        for preset in presets:
            assert "preset_id" in preset
            assert "prompt_suffix" in preset
            assert "negative_prompt" in preset

    def test_scene_has_meaning_tags(self):
        genome = {
            "author_intent": {
                "main_message": "утрата и надежда",
                "core_values": ["память", "духовность"],
            },
        }
        scenes, presets = generate_visuals_from_meaning(genome)
        for scene in scenes:
            tags = scene.get("meaning_tags", [])
            assert len(tags) >= 1

    def test_respects_chapter_count(self):
        genome = {
            "modules": {
                "timeline": [{"chapter": 1}, {"chapter": 2}, {"chapter": 3}],
                "themes": [{"name": "Рассвет", "description": "начало"}],
            },
        }
        scenes, presets = generate_visuals_from_meaning(genome)
        assert len(scenes) == 3  # min(5, 3)

    def test_caps_at_5_chapters(self):
        genome = {
            "modules": {
                "timeline": [{"chapter": i} for i in range(1, 20)],
                "themes": [{"name": "Эволюция", "description": "рост"}],
            },
        }
        scenes, presets = generate_visuals_from_meaning(genome)
        assert len(scenes) <= 5  # cap

    def test_emotion_map_all_values(self):
        for emotion, visual in EMOTION_MAP.items():
            assert isinstance(visual, str)
            assert len(visual) > 0

    def test_palette_map_all_values(self):
        for emotion, palette in PALETTE_MAP.items():
            assert isinstance(palette, list)
            assert len(palette) >= 1
            for color in palette:
                assert color.startswith("#")
