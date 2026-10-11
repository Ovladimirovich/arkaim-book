"""Tests for ContinuityEngine."""
import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "core" / "CORE"))
from visual.continuity_engine import ContinuityEngine
from visual.continuity_state import ContinuityState

class TestContinuityState:
    def test_create_state(self):
        state = ContinuityState(architecture_style="Bronze Age", character_appearances={"velik": "hash1"}, weather="clear", season="summer", lighting_angle="east", color_temperature=3200, props=["torches"])
        assert state.architecture_style == "Bronze Age"
        assert "velik" in state.character_appearances

class TestContinuityEngine:
    def test_first_shot_no_continuity(self):
        engine = ContinuityEngine()
        assert engine._states == {}
