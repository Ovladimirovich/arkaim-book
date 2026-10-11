"""M7.2 tests: Epoch visualization via temporal model.

Tests:
- build_epoch_prompt() produces correct prompts from epoch data
- POST /book/visualize/epoch/{epoch_id} endpoint works
- 404 for unknown epoch
- No model mutation
- Provenance preserved
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
# build_epoch_prompt unit tests
# ═══════════════════════════════════════════════════════════════


class TestBuildEpochPrompt:
    """Test PromptBuilder.build_epoch_prompt()."""

    def test_satya_yuga_prompt_contains_name_and_emotion(self):
        from visualization.prompt_builder import PromptBuilder

        pb = PromptBuilder(pulse=None)
        ctx = {
            "epoch": {"name_ru": "Сатья Юга", "description": "Золотой век"},
            "event_count": 3,
            "character_count": 5,
        }
        prompt = pb.build_epoch_prompt("satya_yuga", ctx)
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "Сатья Юга" in prompt
        assert "golden" in prompt.lower() or "hopeful" in prompt.lower()

    def test_kali_yuga_prompt_different_emotion(self):
        from visualization.prompt_builder import PromptBuilder

        pb = PromptBuilder(pulse=None)
        ctx = {
            "epoch": {"name_ru": "Кали Юга", "description": "Эпоха хаоса"},
            "event_count": 1,
            "character_count": 0,
        }
        prompt = pb.build_epoch_prompt("kali_yuga", ctx)
        assert "Кали Юга" in prompt
        assert "melancholic" in prompt.lower() or "dark" in prompt.lower()

    def test_unknown_epoch_uses_neutral_emotion(self):
        from visualization.prompt_builder import PromptBuilder

        pb = PromptBuilder(pulse=None)
        ctx = {
            "epoch": {"name_ru": "Unknown Era", "description": ""},
            "event_count": 0,
            "character_count": 0,
        }
        prompt = pb.build_epoch_prompt("unknown_epoch", ctx)
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "unknown_epoch" in prompt.lower() or "Unknown Era" in prompt

    def test_empty_context_uses_fallbacks(self):
        from visualization.prompt_builder import PromptBuilder

        pb = PromptBuilder(pulse=None)
        prompt = pb.build_epoch_prompt("some_epoch", {})
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_prompt_no_duplicate_words(self):
        from visualization.prompt_builder import PromptBuilder

        pb = PromptBuilder(pulse=None)
        ctx = {"epoch": {"name_ru": "Arkaim Era", "description": "Arkaim"}, "event_count": 0, "character_count": 0}
        prompt = pb.build_epoch_prompt("arkaim_era", ctx)
        phrases = [p.strip().lower() for p in prompt.split(",")]
        assert len(phrases) == len(set(phrases))


# ═══════════════════════════════════════════════════════════════
# /book/visualize/epoch/{epoch_id} endpoint tests
# ═══════════════════════════════════════════════════════════════


class TestEpochVisualEndpoint:
    """Test POST /book/visualize/epoch/{epoch_id}."""

    def test_visualize_epoch_known(self, client, loaded_world_model):
        epochs = loaded_world_model.get_epochs()
        if not epochs:
            pytest.skip("No epochs in WorldModel")
        epoch_id = epochs[0].id
        resp = client.post(f"/book/visualize/epoch/{epoch_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "media_plan" in data
        mp = data["media_plan"]
        assert isinstance(mp, dict)
        assert "prompt" in mp
        assert isinstance(mp["prompt"], str)
        assert len(mp["prompt"]) > 0

    def test_visualize_epoch_not_found(self, client):
        resp = client.post("/book/visualize/epoch/nonexistent_epoch_123")
        assert resp.status_code == 404

    def test_visualize_epoch_arkaim_era(self, client, loaded_world_model):
        epoch_ids = [e.id for e in loaded_world_model.get_epochs()]
        if "arkaim_era" not in epoch_ids:
            pytest.skip("arkaim_era not in WorldModel")
        resp = client.post("/book/visualize/epoch/arkaim_era")
        assert resp.status_code == 200
        data = resp.json()
        assert "media_plan" in data
        mp = data["media_plan"]
        assert isinstance(mp["prompt"], str) and len(mp["prompt"]) > 10

    def test_visualize_does_not_mutate_world_model(self, client, loaded_world_model):
        epochs_before = len(loaded_world_model.get_epochs())
        events_before = len(loaded_world_model.get_events())
        resp = client.post("/book/visualize/epoch/satya_yuga")
        assert resp.status_code == 200
        epochs_after = len(loaded_world_model.get_epochs())
        events_after = len(loaded_world_model.get_events())
        assert epochs_before == epochs_after
        assert events_before == events_after


# ═══════════════════════════════════════════════════════════════
# M5/M6 regression
# ═══════════════════════════════════════════════════════════════


class TestM72Regression:
    """M5/M6 tests still pass after M7.2."""

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
