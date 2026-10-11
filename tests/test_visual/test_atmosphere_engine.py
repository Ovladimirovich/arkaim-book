"""Tests for AtmosphereEngine."""
import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "core" / "CORE"))
from visual.atmosphere_engine import AtmosphereEngine

@pytest.fixture
def engine():
    return AtmosphereEngine()

class TestAtmosphereEngine:
    def test_sacred_atmosphere(self, engine):
        ctx = engine.get_atmosphere("sacred")
        assert ctx is not None
        assert ctx.name == "sacred"
        assert "golden" in ctx.light.lower() or "warm" in ctx.light.lower()

    def test_resolve_from_emotion(self, engine):
        name = engine.resolve_from_emotion("sacred_glow")
        assert name == "sacred"

    def test_unknown_returns_default(self, engine):
        ctx = engine.get_atmosphere("nonexistent")
        assert ctx is not None
        # Unknown atmosphere returns AtmosphereContext with the input name
        assert ctx.name == "nonexistent"

    def test_list_atmospheres(self, engine):
        atmospheres = engine.list_atmospheres()
        assert len(atmospheres) > 0
        assert "sacred" in atmospheres
