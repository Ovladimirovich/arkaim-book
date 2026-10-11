"""Tests for CameraEngine."""
import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "core" / "CORE"))
from visual.camera_engine import CameraEngine

@pytest.fixture
def engine():
    return CameraEngine()

class TestCameraEngine:
    def test_close_up(self, engine):
        ctx = engine.get_camera("close_up")
        assert ctx is not None
        assert ctx.shot_type == "close_up"

    def test_default_movement(self, engine):
        ctx = engine.get_camera("wide")
        assert ctx is not None
        assert ctx.movement is not None
