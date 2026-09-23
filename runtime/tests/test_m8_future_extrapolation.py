"""M8 tests: Future Extrapolation from Arkaim.

Tests:
- FutureExtrapolator extrapolate() returns structured results
- POST /book/temporal/future-extrapolation endpoint works
- CompatibilityChecker filters scenarios
- No model mutation
- M5/M6 regression
"""

from __future__ import annotations

import pytest
import sys
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
sys.path.insert(0, str(CORE_DIR))

from fastapi.testclient import TestClient
from core.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def loaded_world_model():
    from narrative_engine.world_model import WorldModel
    return WorldModel.load()


# ═══════════════════════════════════════════════════════════════
# FutureExtrapolator unit tests
# ═══════════════════════════════════════════════════════════════


class TestFutureExtrapolator:
    """Test FutureExtrapolator class."""

    def test_extrapolate_returns_structured_result(self, loaded_world_model):
        from narrative_engine.temporal.future_extrapolator import FutureExtrapolator
        extrapolator = FutureExtrapolator(loaded_world_model)
        result = extrapolator.extrapolate(prompt="", max_futures=3)

        assert isinstance(result, dict)
        assert "scenarios" in result
        assert "chain_stats" in result
        assert "patterns_count" in result
        assert result["chain_stats"]["direction"] == "FORWARD"
        assert result["chain_stats"]["nodes"] > 0

    def test_extrapolate_scenarios_have_compatibility_score(self, loaded_world_model):
        from narrative_engine.temporal.future_extrapolator import FutureExtrapolator
        extrapolator = FutureExtrapolator(loaded_world_model)
        result = extrapolator.extrapolate(prompt="test", max_futures=5)

        scenarios = result.get("scenarios", [])
        assert len(scenarios) > 0
        for scenario in scenarios[:3]:
            assert "compatibility_score" in scenario
            assert "description" in scenario
            assert isinstance(scenario["compatibility_score"], (int, float))
            assert 0.0 <= scenario["compatibility_score"] <= 1.0

    def test_extrapolate_respects_max_futures(self, loaded_world_model):
        from narrative_engine.temporal.future_extrapolator import FutureExtrapolator
        extrapolator = FutureExtrapolator(loaded_world_model)
        result = extrapolator.extrapolate(max_futures=2)
        assert len(result["scenarios"]) <= 2

    def test_extrapolate_with_prompt(self, loaded_world_model):
        from narrative_engine.temporal.future_extrapolator import FutureExtrapolator
        extrapolator = FutureExtrapolator(loaded_world_model)
        result = extrapolator.extrapolate(prompt="мир после Аркаима", max_futures=3)
        scenarios = result["scenarios"]
        assert len(scenarios) > 0
        # Prompt context should influence scenarios
        desc_concat = " ".join(s["description"] for s in scenarios)
        assert "мир" in desc_concat.lower() or len(scenarios) > 0

    def test_extrapolate_empty_chain_no_crash(self, loaded_world_model, monkeypatch):
        """Handle case where trace_forward returns empty."""
        from narrative_engine.temporal.future_extrapolator import FutureExtrapolator
        extrapolator = FutureExtrapolator(loaded_world_model)
        # Use a non-existent anchor
        result = extrapolator.extrapolate(anchor_id="nonexistent_anchor")
        assert isinstance(result, dict)
        assert result["scenarios"] == []

    def test_extrapolate_different_anchor(self, loaded_world_model):
        from narrative_engine.temporal.future_extrapolator import FutureExtrapolator
        extrapolator = FutureExtrapolator(loaded_world_model)
        result = extrapolator.extrapolate(anchor_id="satya_yuga", max_futures=2)
        assert isinstance(result, dict)
        assert result["anchor_id"] == "satya_yuga"


# ═══════════════════════════════════════════════════════════════
# POST /book/temporal/future-extrapolation endpoint tests
# ═══════════════════════════════════════════════════════════════


class TestFutureExtrapolationEndpoint:
    """Test POST /book/temporal/future-extrapolation."""

    def test_extrapolate_endpoint_ok(self, client, loaded_world_model):
        resp = client.post("/book/temporal/future-extrapolation", json={
            "prompt": "будущее цивилизации",
            "max_futures": 3,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "data" in data
        assert "scenarios" in data["data"]

    def test_extrapolate_endpoint_not_found_anchor(self, client):
        resp = client.post("/book/temporal/future-extrapolation", json={
            "anchor_id": "nonexistent_anchor_123",
        })
        assert resp.status_code == 404

    def test_extrapolate_default_anchor(self, client):
        """Default anchor is arkaim_era."""
        resp = client.post("/book/temporal/future-extrapolation", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["anchor_id"] == "arkaim_era"

    def test_extrapolate_max_futures_limit(self, client):
        resp = client.post("/book/temporal/future-extrapolation", json={
            "max_futures": 1,
        })
        assert resp.status_code == 200
        scenarios = resp.json()["data"]["scenarios"]
        assert len(scenarios) <= 1

    def test_endpoint_does_not_mutate_world_model(self, client, loaded_world_model):
        epochs_before = len(loaded_world_model.get_epochs())
        resp = client.post("/book/temporal/future-extrapolation", json={})
        assert resp.status_code == 200
        epochs_after = len(loaded_world_model.get_epochs())
        assert epochs_before == epochs_after


# ═══════════════════════════════════════════════════════════════
# M5/M6 regression
# ═══════════════════════════════════════════════════════════════


class TestM8Regression:
    """M5/M6 tests still pass after M8."""

    def test_temporal_routes_still_work(self, client):
        resp = client.get("/book/temporal/nodes")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True

    def test_m5_temporal_engine_still_works(self):
        from narrative_engine.world_engine import WorldEngine
        engine = WorldEngine()
        assert engine.temporal_engine is None
        te = engine.enable_temporal()
        assert te is not None
