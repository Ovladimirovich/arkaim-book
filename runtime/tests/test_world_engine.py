"""Tests for WorldEngine."""

import pytest
import sys

sys.path.insert(0, "../core/CORE")

from narrative_engine.world_engine import WorldEngine


@pytest.fixture
def engine():
    return WorldEngine()


class TestWorldEngine:
    def test_build_from_world_model(self, engine):
        assert len(engine._world_model._data) > 0

    def test_search(self, engine):
        results = engine.search("Аркаим")
        assert results["total"] > 0

    def test_get_entity(self, engine):
        engine.initialize()
        entity = engine.get_entity("region_arkaim")
        assert entity is not None
        assert entity["id"] == "region_arkaim"

    def test_get_entity_context(self, engine):
        context = engine.get_entity_context("region_arkaim")
        assert "entity" in context
        assert "relations" in context

    def test_summary(self, engine):
        summary = engine.summary()
        assert "сущностей" in summary

    def test_get_stats(self, engine):
        stats = engine.get_stats()
        assert "world_model" in stats
        assert "relation_graph" in stats
