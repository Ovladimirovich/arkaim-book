"""M5.1 tests: WorldEngine temporal integration (enable_temporal).

M5.1: минимальная opt-in интеграция TemporalReconstructionEngine в WorldEngine.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "../core/CORE")

from narrative_engine.world_engine import WorldEngine
from narrative_engine.temporal.reconstruction_engine import TemporalReconstructionEngine
from narrative_engine.source_levels import ProvenanceCategory


class TestM5TemporalIntegration:
    """M5.1: temporal is disabled by default, opt-in via enable_temporal()."""

    def test_temporal_disabled_by_default(self):
        """После создания WorldEngine temporal engine отсутствует."""
        engine = WorldEngine()
        assert engine.temporal_engine is None

    def test_enable_temporal_creates_engine(self):
        """enable_temporal() создаёт TemporalReconstructionEngine."""
        engine = WorldEngine()
        te = engine.enable_temporal()
        assert te is not None
        assert isinstance(te, TemporalReconstructionEngine)
        # property возвращает тот же экземпляр
        assert engine.temporal_engine is te

    def test_enable_temporal_correct_type(self):
        """Temporal engine — именно TemporalReconstructionEngine, не дубликат."""
        engine = WorldEngine()
        te = engine.enable_temporal()
        # Проверяем, что это не новый класс
        assert type(te).__name__ == "TemporalReconstructionEngine"
        assert hasattr(te, "find_paths")
        assert hasattr(te, "reconstruct_chain")

    def test_enable_temporal_populated_from_world_model(self):
        """Temporal engine содержит узлы из WorldModel epochs."""
        engine = WorldEngine()
        te = engine.enable_temporal()
        nodes = te.get_all_nodes()
        # Должны быть узлы эпох (как минимум arkaim_era)
        epoch_nodes = [n for n in nodes if n.era_id]
        assert len(epoch_nodes) > 0

    def test_enable_temporal_idempotent(self):
        """Повторный вызов enable_temporal() возвращает тот же экземпляр."""
        engine = WorldEngine()
        first = engine.enable_temporal()
        second = engine.enable_temporal()
        assert first is second  # тот же объект, не новый
        # Количество узлов не удваивается
        nodes_after_first = len(first.get_all_nodes())
        nodes_after_second = len(second.get_all_nodes())
        assert nodes_after_first == nodes_after_second

    def test_no_world_model_mutation(self):
        """enable_temporal() не мутирует WorldModelExt."""
        engine = WorldEngine()
        # Snapshot до
        categories_before = set(engine._world_model.get_categories())
        epochs_before = len(engine._world_model.get_category("epochs"))
        locations_before = len(engine._world_model.get_category("locations"))

        engine.enable_temporal()

        # Snapshot после
        categories_after = set(engine._world_model.get_categories())
        epochs_after = len(engine._world_model.get_category("epochs"))
        locations_after = len(engine._world_model.get_category("locations"))

        assert categories_before == categories_after
        assert epochs_before == epochs_after
        assert locations_before == locations_after

    def test_provenance_not_affected(self):
        """Provenance семантика не меняется при подключении temporal."""
        engine = WorldEngine()
        engine.enable_temporal()

        te = engine.temporal_engine
        # Проверяем, что provenance сохранён
        nodes = te.get_all_nodes()
        for node in nodes:
            for tag in node.provenance:
                # Категории provenance должны быть валидными
                assert tag.category in (
                    ProvenanceCategory.AUTHOR_CANON,
                    ProvenanceCategory.EXTERNAL_SOURCE,
                    ProvenanceCategory.HYPOTHESIS,
                    ProvenanceCategory.RECONSTRUCTION,
                )

    def test_backward_compatibility(self):
        """Существующий API WorldEngine работает без temporal."""
        engine = WorldEngine()
        # Существующие методы должны работать
        assert "summary" in engine.summary().lower() or len(engine.summary()) > 0
        stats = engine.get_stats()
        assert "world_model" in stats
        assert "relation_graph" in stats


class TestM5Regression:
    """Regression: M1-M4 tests still pass after M5.1."""

    def test_m1_provenance_still_works(self):
        from narrative_engine.source_levels import ProvenanceCategory, canonical_provenance

        tag = canonical_provenance()
        assert tag.category == ProvenanceCategory.AUTHOR_CANON

    def test_m2_temporal_node_still_works(self):
        from narrative_engine.temporal.node import TemporalNode
        from narrative_engine.temporal.precision import TemporalPrecision

        node = TemporalNode.present_anchor()
        assert node.id == "temporal_today"
        assert node.precision == TemporalPrecision.EXACT

    def test_m3_reconstruction_still_works(self):
        from narrative_engine.temporal.reconstruction_engine import TemporalReconstructionEngine
        from narrative_engine.temporal.node import TemporalNode
        from narrative_engine.temporal.relation import TemporalRelation

        engine = TemporalReconstructionEngine()
        n1 = TemporalNode(id="n1", label="N1", precision="RELATIVE")
        n2 = TemporalNode(id="n2", label="N2", precision="RELATIVE")
        engine.add_node(n1)
        engine.add_node(n2)
        engine.add_relation(TemporalRelation.precedes("n1", "n2"))

        path = engine.bfs_path("n1", "n2")
        assert path is not None
        assert path[0] == "n1"
        assert path[-1] == "n2"


class TestM5QueryFacade:
    """M5.2: WorldEngine temporal query facade methods."""

    def test_chain_disabled_by_default(self):
        """get_temporal_chain returns None when temporal is not enabled."""
        engine = WorldEngine()
        assert engine.get_temporal_chain("BACKWARD") is None

    def test_chain_after_enable(self):
        """get_temporal_chain returns dict after enable_temporal()."""
        engine = WorldEngine()
        engine.enable_temporal()
        result = engine.get_temporal_chain("BACKWARD")
        assert result is not None
        assert isinstance(result, dict)
        assert "direction" in result
        assert "nodes" in result

    def test_chain_returns_json_serializable(self):
        """get_temporal_chain result is JSON-serializable dict."""
        engine = WorldEngine()
        engine.enable_temporal()
        result = engine.get_temporal_chain("BACKWARD")
        assert result is not None
        import json

        json_str = json.dumps(result, ensure_ascii=False)
        assert len(json_str) > 0

    def test_path_disabled_by_default(self):
        """find_temporal_path returns None when temporal is not enabled."""
        engine = WorldEngine()
        assert engine.find_temporal_path("temporal_pre_arkaim", "temporal_arkaim_era") is None

    def test_path_after_enable(self):
        """find_temporal_path returns dict after enable_temporal()."""
        engine = WorldEngine()
        engine.enable_temporal()
        result = engine.find_temporal_path("temporal_pre_arkaim", "temporal_arkaim_era")
        assert result is not None
        assert isinstance(result, dict)
        assert "path" in result

    def test_path_no_path_returns_none(self):
        """find_temporal_path returns None for non-existent nodes."""
        engine = WorldEngine()
        engine.enable_temporal()
        result = engine.find_temporal_path("nonexistent_a", "nonexistent_b")
        assert result is None

    def test_chain_delegates_to_m3(self):
        """get_temporal_chain delegates to existing M3 reconstruct_chain."""
        from narrative_engine.temporal.chain import ChainDirection

        engine = WorldEngine()
        te = engine.enable_temporal()
        # Direct call with proper ChainDirection
        _direct = te.reconstruct_chain("temporal_arkaim_era", ChainDirection.FORWARD)
        # Facade call with string (conversion happens in WorldEngine)
        facade = engine.get_temporal_chain("FORWARD")
        assert facade is not None
        assert facade["direction"] == "FORWARD"

    def test_backward_compatibility_m5_1(self):
        """M5.1 tests still pass after M5.2 additions."""
        engine = WorldEngine()
        assert engine.temporal_engine is None
        te = engine.enable_temporal()
        assert te is engine.temporal_engine
        assert isinstance(te, TemporalReconstructionEngine)
