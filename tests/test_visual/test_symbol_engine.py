"""Tests for SymbolEngine."""
import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "core" / "CORE"))
from visual.symbol_engine import SymbolEngine

@pytest.fixture
def engine():
    return SymbolEngine()

class TestSymbolEngine:
    def test_stone_circle(self, engine):
        result = engine.get_symbols(["stone_circle"])
        assert len(result) == 1
        ctx = result[0]
        assert ctx.name == "stone_circle"
        assert len(ctx.colors) > 0
        assert len(ctx.visual_elements) > 0

    def test_multiple_symbols(self, engine):
        result = engine.get_symbols(["stone_circle", "fire_pit", "celestial_alignment"])
        assert len(result) == 3
        names = [s.name for s in result]
        assert "stone_circle" in names
        assert "fire_pit" in names

    def test_unknown_symbol(self, engine):
        result = engine.get_symbols(["unknown_symbol"])
        assert len(result) == 1
        assert result[0].name == "unknown_symbol"

    def test_empty_tags(self, engine):
        result = engine.get_symbols([])
        assert len(result) == 0
