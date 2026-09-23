"""Tests for visualization/archetype_visuals.py"""
import pytest
import sys
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
sys.path.insert(0, str(CORE_DIR))

from visualization.archetype_visuals import (
    archetype_to_visual,
    fill_missing_archetype_visuals,
    ARCHETYPE_VISUAL_TEMPLATES,
    DEFAULT_TEMPLATE,
)


class TestArchetypeToVisual:
    def test_known_archetype(self):
        char = {"id": "velik", "name": "Велик", "archetype": "Искатель"}
        visual = archetype_to_visual(char)
        assert visual["character_id"] == "velik"
        assert visual["clothing"] == ARCHETYPE_VISUAL_TEMPLATES["Искатель"]["clothing"]
        assert visual["color_palette"] == ["#8B4513", "#2F4F4F", "#6B8E23"]
        assert "поясная сумка" in visual["accessories"]
        assert visual["age_range"] == "не указан"

    def test_unknown_archetype_fallback(self):
        char = {"id": "mystery", "name": "Mystery", "archetype": "Неизвестный"}
        visual = archetype_to_visual(char)
        assert visual["character_id"] == "mystery"
        assert visual["clothing"] == DEFAULT_TEMPLATE["clothing"]
        assert visual["color_palette"] == ["earth tones"]

    def test_no_archetype_field(self):
        char = {"name": "Без_архетипа"}
        visual = archetype_to_visual(char)
        assert visual["character_id"] == "Без_архетипа"
        assert visual["clothing"] == DEFAULT_TEMPLATE["clothing"]

    def test_missing_id_and_name(self):
        char = {"archetype": "Мудрец"}
        visual = archetype_to_visual(char)
        assert visual["character_id"] == "unknown"

    def test_all_archetypes_have_required_fields(self):
        for name, template in ARCHETYPE_VISUAL_TEMPLATES.items():
            char = {"id": f"test_{name}", "archetype": name}
            visual = archetype_to_visual(char)
            assert "character_id" in visual
            assert "clothing" in visual
            assert "color_palette" in visual
            assert len(visual["color_palette"]) >= 1
            assert "accessories" in visual
            assert isinstance(visual["accessories"], list)
            assert "style_constants" in visual

    def test_accessories_not_shared(self):
        char_a = {"id": "a", "archetype": "Искатель"}
        char_b = {"id": "b", "archetype": "Искатель"}
        visual_a = archetype_to_visual(char_a)
        visual_b = archetype_to_visual(char_b)
        visual_a["accessories"].append("новый")
        assert len(visual_b["accessories"]) < len(visual_a["accessories"])


class TestFillMissingArchetypeVisuals:
    def test_fills_missing(self):
        genome = {
            "modules": {
                "characters": [
                    {"id": "velik", "name": "Велик", "archetype": "Искатель"},
                    {"id": "old_one", "name": "Старец", "archetype": "Мудрец"},
                ],
                "character_visuals": [
                    {"character_id": "velik", "clothing": "существующий"},
                ],
            }
        }
        created = fill_missing_archetype_visuals(genome)
        assert created == 1
        visuals = genome["modules"]["character_visuals"]
        assert len(visuals) == 2
        ids = {v["character_id"] for v in visuals}
        assert "old_one" in ids

    def test_no_characters(self):
        genome = {"modules": {}}
        created = fill_missing_archetype_visuals(genome)
        assert created == 0

    def test_all_existing(self):
        genome = {
            "modules": {
                "characters": [{"id": "velik", "archetype": "Искатель"}],
                "character_visuals": [{"character_id": "velik"}],
            }
        }
        created = fill_missing_archetype_visuals(genome)
        assert created == 0

    def test_character_without_id(self):
        genome = {
            "modules": {
                "characters": [{"name": "NoID", "archetype": "Мудрец"}],
                "character_visuals": [],
            }
        }
        created = fill_missing_archetype_visuals(genome)
        assert created == 1

    def test_skips_duplicate(self):
        genome = {
            "modules": {
                "characters": [
                    {"id": "a", "archetype": "Искатель"},
                    {"id": "a", "archetype": "Мудрец"},
                ],
                "character_visuals": [],
            }
        }
        created = fill_missing_archetype_visuals(genome)
        assert created == 1  # второй с тем же id — уже в existing_ids

    def test_genome_without_modules(self):
        genome = {}
        created = fill_missing_archetype_visuals(genome)
        assert created == 0
        assert "modules" in genome  # должен быть создан
