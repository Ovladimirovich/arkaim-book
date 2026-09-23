"""Tests for visualization/conflict_palettes.py"""
import pytest
import sys
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
sys.path.insert(0, str(CORE_DIR))

from visualization.conflict_palettes import (
    resolve_conflict_key,
    generate_conflict_scene,
    generate_all_conflict_scenes,
    CONFLICT_TEMPLATES,
    DEFAULT_CONFLICT,
)


class TestResolveConflictKey:
    def test_known_conflict(self):
        key = resolve_conflict_key("Гиперборея", "Атлантида")
        assert key == "гиперборея_атлантида"

    def test_reversed_order(self):
        key = resolve_conflict_key("Атлантида", "Гиперборея")
        assert key == "гиперборея_атлантида"

    def test_unknown_conflict(self):
        key = resolve_conflict_key("Несуществующий", "Тоже")
        assert key is None

    def test_normalizes_spaces(self):
        key = resolve_conflict_key("Кали Юга", "Сати Юга")
        assert key == "кали_юга_сати_юга"


class TestGenerateConflictScene:
    def test_known_entities(self):
        a = {"name": "Гиперборея", "type": "civilization"}
        b = {"name": "Атлантида", "type": "civilization"}
        scene = generate_conflict_scene(a, b, chapter=3)
        assert scene["chapter"] == 3
        assert scene["emotion"] == "conflict_civilizations"
        assert scene["visual_style_hint"] == "duality_contrast"
        assert len(scene["palette_a"]) == 3
        assert len(scene["palette_b"]) == 3

    def test_unknown_entities_fallback(self):
        a = {"name": "Foo"}
        b = {"name": "Bar"}
        scene = generate_conflict_scene(a, b)
        assert scene["emotion"] == DEFAULT_CONFLICT["emotion"]
        assert scene["visual_style_hint"] == DEFAULT_CONFLICT["visual_style_hint"]

    def test_scene_id_format(self):
        a = {"name": "Гиперборея"}
        b = {"name": "Атлантида"}
        scene = generate_conflict_scene(a, b)
        assert scene["scene_id"] == "conflict_гиперборея_атлантида"

    def test_meaning_tags(self):
        a = {"name": "Материя"}
        b = {"name": "Дух"}
        scene = generate_conflict_scene(a, b)
        assert "конфликт:материя" in scene["meaning_tags"]
        assert "конфликт:дух" in scene["meaning_tags"]

    def test_default_chapter(self):
        a = {"name": "A"}
        b = {"name": "B"}
        scene = generate_conflict_scene(a, b)
        assert scene["chapter"] == 1

    def test_palette_from_match(self):
        a = {"name": "Хаос"}
        b = {"name": "Гармония"}
        scene = generate_conflict_scene(a, b)
        assert scene["emotion"] == "struggle_of_opposites"
        assert "#8B0000" in scene["palette_a"]
        assert "#90EE90" in scene["palette_b"]


class TestGenerateAllConflictScenes:
    def test_returns_conflict_scenes(self):
        genome = {
            "world_entities": [
                {"name": "Гиперборея", "type": "civilization", "conflict_with": ["Атлантида"]},
                {"name": "Атлантида", "type": "civilization", "conflict_with": []},
            ]
        }
        scenes = generate_all_conflict_scenes(genome)
        assert len(scenes) == 1
        assert scenes[0]["emotion"] == "conflict_civilizations"

    def test_no_duplicates(self):
        genome = {
            "world_entities": [
                {"name": "A", "conflict_with": ["B"]},
                {"name": "B", "conflict_with": ["A"]},
            ]
        }
        scenes = generate_all_conflict_scenes(genome)
        assert len(scenes) == 1

    def test_empty_genome(self):
        scenes = generate_all_conflict_scenes({})
        assert scenes == []

    def test_no_conflicts(self):
        genome = {
            "world_entities": [
                {"name": "A", "conflict_with": []},
                {"name": "B"},
            ]
        }
        scenes = generate_all_conflict_scenes(genome)
        assert scenes == []

    def test_missing_target_entity(self):
        genome = {
            "world_entities": [
                {"name": "A", "conflict_with": ["MissingEntity"]},
            ]
        }
        scenes = generate_all_conflict_scenes(genome)
        assert len(scenes) == 1
        assert scenes[0]["emotion"] != "conflict_civilizations"  # fallback

    def test_all_templates_accessible(self):
        for key in CONFLICT_TEMPLATES:
            parts = key.split("_")
            if len(parts) >= 2:
                a_name = parts[0]
                b_name = "_".join(parts[1:])
                key_check = resolve_conflict_key(a_name, b_name)
                assert key_check is not None
