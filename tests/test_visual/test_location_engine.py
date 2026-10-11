"""Tests for LocationEngine."""
import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "core" / "CORE"))
from visual.location_engine import LocationEngine

@pytest.fixture
def genome():
    return {
        "modules": {"location_visuals": [{"location_id": "Аркаим", "type": "ancient_settlement"}]},
        "world_entities": [{"id": "Аркаим", "description": "Древнее поселение"}]
    }

@pytest.fixture
def engine(genome):
    return LocationEngine(genome)

class TestLocationEngine:
    def test_get_location_context(self, engine):
        ctx = engine.get_location_context("Аркаим")
        assert ctx is not None
        assert ctx.location_id == "Аркаим"

    def test_unknown_location_falls_back(self, engine):
        ctx = engine.get_location_context("Неизвестное_место")
        assert ctx is not None
