"""Tests for CharacterVisualEngine."""
import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "core" / "CORE"))
from visual.character_visual_engine import CharacterVisualEngine

@pytest.fixture
def genome():
    return {
        "modules": {
            "character_visuals": [{"character_id": "Велик", "age_range": "25-30", "face": "angular"}],
            "characters": [{"id": "Световит", "name": "Световит", "archetype": "Мудрец"}]
        }
    }

@pytest.fixture
def engine(genome):
    return CharacterVisualEngine(genome)

class TestCharacterVisualEngine:
    def test_known_character(self, engine):
        ctx = engine.get_character_context("Велик")
        assert ctx is not None
        assert ctx.character_id == "Велик"

    def test_unknown_character_falls_back(self, engine):
        ctx = engine.get_character_context("Несуществующий")
        assert ctx is not None
