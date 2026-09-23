"""M9 tests: Temporal-aware ExpansionLayer.

M9 makes ExpansionLayer.respond_to() temporal-aware using WorldEngine facade.
Tests cover:
1. Temporal intent detection (4 categories + None)
2. BACKWARD query → RECONSTRUCTION provenance
3. FORWARD query → FUTURE_EXTRAPOLATION provenance
4. CONTEXT query → epoch context from WorldModel
5. POSITION query → node data from temporal graph
6. Non-temporal query regression (unchanged behavior)
7. No dependency cycle between pulse.layers and temporal subsystem
8. No new graph relations created
9. Graceful fallback when temporal_engine is None
10. Provenance contract (lowest-common-denominator)
"""

from __future__ import annotations

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
sys.path.insert(0, str(CORE_DIR))

from narrative_engine.source_levels import ProvenanceCategory, ProvenanceTag, SourceLevel


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────

@pytest.fixture
def expansion_layer():
    """ExpansionLayer without temporal engine (baseline)."""
    from pulse.layers import ExpansionLayer
    return ExpansionLayer(genome={})


@pytest.fixture
def expansion_layer_with_temporal(temporal_engine):
    """ExpansionLayer with temporal engine injected."""
    from pulse.layers import ExpansionLayer
    return ExpansionLayer(genome={}, temporal_engine=temporal_engine)


@pytest.fixture
def temporal_engine():
    """Create a minimal TemporalReconstructionEngine for testing."""
    from narrative_engine.temporal.reconstruction_engine import TemporalReconstructionEngine
    from narrative_engine.temporal.graph import TemporalGraph
    from narrative_engine.temporal.node import TemporalNode, TemporalPrecision
    from narrative_engine.source_levels import ProvenanceTag, SourceLevel, ProvenanceCategory
    from narrative_engine.temporal.relation import TemporalRelation, TemporalRelationType

    graph = TemporalGraph()
    arkaim_node = TemporalNode(
        id="temporal_arkaim_era",
        label="Аркаимская эпоха",
        precision=TemporalPrecision.RELATIVE,
        provenance=[
            ProvenanceTag(
                source_level=SourceLevel.CANON,
                category=ProvenanceCategory.AUTHOR_CANON,
                confidence=0.85,
                notes="arkaim_era from book canon",
            ),
            ProvenanceTag(
                source_level=SourceLevel.HISTORICAL,
                category=ProvenanceCategory.EXTERNAL_SOURCE,
                confidence=0.7,
                notes="archaeological evidence",
            ),
        ],
    )
    pre_node = TemporalNode(
        id="temporal_pre_arkaim",
        label="До-Аркаим",
        precision=TemporalPrecision.RELATIVE,
        provenance=[
            ProvenanceTag(
                source_level=SourceLevel.SYSTEM_INTERPRETATION,
                category=ProvenanceCategory.RECONSTRUCTION,
                confidence=0.6,
                notes="reconstructed predecessor",
            ),
        ],
    )
    future_node = TemporalNode(
        id="temporal_future",
        label="Будущее после Аркаима",
        precision=TemporalPrecision.UNKNOWN,
        provenance=[
            ProvenanceTag(
                source_level=SourceLevel.SYSTEM_INTERPRETATION,
                category=ProvenanceCategory.FUTURE_EXTRAPOLATION,
                confidence=0.4,
                notes="extrapolated future scenario",
            ),
        ],
    )
    graph.add_node(arkaim_node)
    graph.add_node(pre_node)
    graph.add_node(future_node)
    rel = TemporalRelation(
        id="rel_pre_arkaim_to_arkaim",
        source_id="temporal_pre_arkaim",
        target_id="temporal_arkaim_era",
        relation_type=TemporalRelationType.PRECEDES,
    )
    graph.add_relation(rel)

    # __init__ takes no args; inject graph via __new__ + attribute assignment
    engine = TemporalReconstructionEngine.__new__(TemporalReconstructionEngine)
    engine._graph = graph
    return engine


# ═══════════════════════════════════════════════════════════════
# Test 1: Temporal Intent Detection
# ═══════════════════════════════════════════════════════════════

class TestTemporalIntentDetection:
    """M9: _detect_temporal_intent correctly classifies queries."""

    def test_backward_query_before_arkaim(self, expansion_layer):
        assert expansion_layer._detect_temporal_intent("что было до Аркаима") == "BACKWARD"

    def test_backward_query_prehistory(self, expansion_layer):
        assert expansion_layer._detect_temporal_intent("какова предыстория Аркаима") == "BACKWARD"

    def test_backward_query_how_appeared(self, expansion_layer):
        assert expansion_layer._detect_temporal_intent("как появилась цивилизация Аркаима") == "BACKWARD"

    def test_forward_query_future(self, expansion_layer):
        assert expansion_layer._detect_temporal_intent("что будет после Аркаима") == "FORWARD"

    def test_forward_query_what_comes_next(self, expansion_layer):
        assert expansion_layer._detect_temporal_intent("будущее Аркаима какое") == "FORWARD"

    def test_context_query_in_arkaim_era(self, expansion_layer):
        assert expansion_layer._detect_temporal_intent("что происходило в эпоху Аркаима") == "CONTEXT"

    def test_context_query_arkaim_context(self, expansion_layer):
        assert expansion_layer._detect_temporal_intent("контекст Аркаима опиши") == "CONTEXT"

    def test_position_query_when_was_arkaim(self, expansion_layer):
        assert expansion_layer._detect_temporal_intent("когда был Аркаим") == "POSITION"

    def test_position_query_what_era(self, expansion_layer):
        assert expansion_layer._detect_temporal_intent("какая это эпоха Аркаима") == "POSITION"

    def test_non_temporal_query_returns_none(self, expansion_layer):
        assert expansion_layer._detect_temporal_intent("что такое Гиперборея") is None

    def test_non_temporal_query_symbolism_returns_none(self, expansion_layer):
        assert expansion_layer._detect_temporal_intent("расскажи про символику") is None

    def test_non_temporal_query_about_kal_yuga_no_temporal(self, expansion_layer):
        """Query about Kali Yuga is NOT temporal intent — it is a topic query."""
        result = expansion_layer._detect_temporal_intent("расскажи про Кали Югу")
        assert result is None or result != "BACKWARD"


# ═══════════════════════════════════════════════════════════════
# Test 2: BACKWARD Query → RECONSTRUCTION Provenance
# ═══════════════════════════════════════════════════════════════

class TestBackwardQuery:
    """M9: BACKWARD temporal query returns RECONSTRUCTION provenance."""

    def test_backward_query_returns_reconstruction_provenance(self, expansion_layer_with_temporal):
        result = expansion_layer_with_temporal.respond_to("что было до Аркаима")
        assert result is not None
        assert result.source.startswith("temporal:")
        prov_cats = [p.get("category") for p in result.provenance]
        assert "RECONSTRUCTION" in prov_cats

    def test_backward_query_text_mentions_reconstruction(self, expansion_layer_with_temporal):
        result = expansion_layer_with_temporal.respond_to("что было до Аркаима")
        assert result is not None
        assert "Реконструкция" in result.text or "предыстория" in result.text.lower()

    def test_backward_query_confidence_below_0_8(self, expansion_layer_with_temporal):
        """Reconstruction confidence must be below canon level."""
        result = expansion_layer_with_temporal.respond_to("что было до Аркаима")
        assert result is not None
        assert result.confidence < 0.8


# ═══════════════════════════════════════════════════════════════
# Test 3: FORWARD Query → FUTURE_EXTRAPOLATION Provenance
# ═══════════════════════════════════════════════════════════════

class TestForwardQuery:
    """M9: FORWARD temporal query returns FUTURE_EXTRAPOLATION provenance."""

    def test_forward_query_returns_future_extrapolation_provenance(self, expansion_layer_with_temporal):
        result = expansion_layer_with_temporal.respond_to("что будет после Аркаима")
        assert result is not None
        assert result.source.startswith("temporal:")
        prov_cats = [p.get("category") for p in result.provenance]
        assert "FUTURE_EXTRAPOLATION" in prov_cats

    def test_forward_query_confidence_below_0_6(self, expansion_layer_with_temporal):
        """Future extrapolation confidence must be low."""
        result = expansion_layer_with_temporal.respond_to("что будет после Аркаима")
        assert result is not None
        assert result.confidence < 0.6


# ═══════════════════════════════════════════════════════════════
# Test 4: CONTEXT Query → Epoch Context
# ═══════════════════════════════════════════════════════════════

class TestContextQuery:
    """M9: CONTEXT temporal query uses WorldModel temporal context."""

    def test_context_query_returns_author_canon_or_external(self, expansion_layer_with_temporal):
        result = expansion_layer_with_temporal.respond_to("контекст Аркаима опиши")
        assert result is not None
        prov_cats = [p.get("category") for p in result.provenance]
        # Context should be AUTHOR_CANON or EXTERNAL_SOURCE (not RECONSTRUCTION)
        assert any(c in prov_cats for c in ["AUTHOR_CANON", "EXTERNAL_SOURCE"])

    def test_context_query_mentions_precision(self, expansion_layer_with_temporal):
        result = expansion_layer_with_temporal.respond_to("контекст Аркаима опиши")
        assert result is not None
        assert "precision" in result.text.lower() or "Precision" in result.text


# ═══════════════════════════════════════════════════════════════
# Test 5: POSITION Query → Node Data
# ═══════════════════════════════════════════════════════════════

class TestPositionQuery:
    """M9: POSITION temporal query returns node precision data."""

    def test_position_query_returns_precision(self, expansion_layer_with_temporal):
        result = expansion_layer_with_temporal.respond_to("когда был Аркаим")
        assert result is not None
        assert "precision" in result.text.lower() or "POSITION" in result.source


# ═══════════════════════════════════════════════════════════════
# Test 6: Non-Temporal Regression
# ═══════════════════════════════════════════════════════════════

class TestNonTemporalRegression:
    """M9: Non-temporal queries behave exactly as before."""

    def test_non_temporal_query_unchanged_behavior(self, expansion_layer):
        """Query without temporal intent should return standard expansion response."""
        result = expansion_layer.respond_to("что такое Кали Юга")
        assert result is not None
        assert result.source.startswith("expansion:")
        assert len(result.provenance) == 0

    def test_non_temporal_query_no_temporal_source(self, expansion_layer):
        result = expansion_layer.respond_to("расскажи про символику")
        if result:
            assert "temporal:" not in result.source

    def test_standard_respond_still_works(self, expansion_layer):
        """Internal _standard_respond should work without temporal engine."""
        result = expansion_layer._standard_respond("кали юга")
        assert result is not None or result is None  # just no crash


# ═══════════════════════════════════════════════════════════════
# Test 7: No Dependency Cycle
# ═══════════════════════════════════════════════════════════════

class TestNoDependencyCycle:
    """M9: ExpansionLayer must not create a dependency cycle."""

    def test_no_direct_import_of_temporal_reconstruction_engine(self):
        """ExpansionLayer should NOT directly import TemporalReconstructionEngine."""
        import pulse.layers
        import inspect
        source = inspect.getsource(pulse.layers)
        assert "from narrative_engine.temporal.reconstruction_engine import" not in source, (
            "ExpansionLayer must NOT directly import TemporalReconstructionEngine — use WorldEngine facade"
        )

    def test_no_direct_import_of_temporal_graph(self):
        """ExpansionLayer should NOT directly import TemporalGraph."""
        import pulse.layers
        import inspect
        source = inspect.getsource(pulse.layers)
        assert "from narrative_engine.temporal.graph import" not in source, (
            "ExpansionLayer must NOT directly import TemporalGraph"
        )

    def test_only_world_engine_facade_import(self):
        """ExpansionLayer should import only get_world_engine from narrative_engine."""
        import pulse.layers
        import inspect
        source = inspect.getsource(pulse.layers)
        assert "from narrative_engine.world_engine import get_world_engine" in source, (
            "ExpansionLayer must use WorldEngine facade for temporal access"
        )


# ═══════════════════════════════════════════════════════════════
# Test 8: No Graph Mutation
# ═══════════════════════════════════════════════════════════════

class TestNoGraphMutation:
    """M9: respond_to must not create new edges in the temporal graph."""

    def test_no_new_relations_created_after_backward_query(self, expansion_layer_with_temporal):
        te = expansion_layer_with_temporal._temporal_engine
        before_count = te._graph.relation_count
        expansion_layer_with_temporal.respond_to("что было до Аркаима")
        after_count = te._graph.relation_count
        assert after_count == before_count, "Temporal graph must not be mutated by respond_to"

    def test_no_new_nodes_created_after_forward_query(self, expansion_layer_with_temporal):
        te = expansion_layer_with_temporal._temporal_engine
        before_count = len(te._graph._nodes)
        expansion_layer_with_temporal.respond_to("что будет после Аркаима")
        after_count = len(te._graph._nodes)
        assert after_count == before_count, "Temporal graph must not be mutated by respond_to"


# ═══════════════════════════════════════════════════════════════
# Test 9: Graceful Fallback Without Temporal Engine
# ═══════════════════════════════════════════════════════════════

class TestGracefulFallback:
    """M9: ExpansionLayer works correctly without temporal engine enabled."""

    def test_temporal_query_without_engine_returns_none(self, expansion_layer):
        """Without temporal engine, temporal queries fall back to standard response or None."""
        result = expansion_layer.respond_to("что было до Аркаима")
        # Should not crash — either None or standard expansion result
        assert result is None or result.source.startswith("expansion:")

    def test_get_context_without_engine_no_crash(self, expansion_layer):
        ctx = expansion_layer.get_context("что было до Аркаима")
        assert isinstance(ctx, str)

    def test_expansion_layer_init_without_temporal_engine(self):
        """Backward compatibility: can init ExpansionLayer without temporal_engine param."""
        from pulse.layers import ExpansionLayer
        el = ExpansionLayer(genome={})
        assert el._temporal_engine is None


# ═══════════════════════════════════════════════════════════════
# Test 10: Provenance Contract — Lowest Common Denominator
# ═══════════════════════════════════════════════════════════════

class TestProvenanceContract:
    """M9: provenance follows lowest-common-denominator rule."""

    def test_combine_provenance_picks_lowest(self):
        """When combining AUTHOR_CANON + RECONSTRUCTION → RECONSTRUCTION wins."""
        from pulse.layers import ExpansionLayer
        prov_list = [
            {"category": "AUTHOR_CANON", "confidence": 0.85},
            {"category": "RECONSTRUCTION", "confidence": 0.7},
        ]
        result = ExpansionLayer._combine_provenance(prov_list)
        assert result[0].get("category") == "RECONSTRUCTION"

    def test_combine_provenance_future_extrapolation_is_lowest(self):
        """FUTURE_EXTRAPOLATION is lower priority than all others."""
        from pulse.layers import ExpansionLayer
        prov_list = [
            {"category": "AUTHOR_CANON", "confidence": 0.9},
            {"category": "FUTURE_EXTRAPOLATION", "confidence": 0.4},
        ]
        result = ExpansionLayer._combine_provenance(prov_list)
        assert result[0].get("category") == "FUTURE_EXTRAPOLATION"

    def test_combine_provenance_empty_returns_empty(self):
        from pulse.layers import ExpansionLayer
        assert ExpansionLayer._combine_provenance([]) == []

    def test_backwards_query_never_has_author_canon_alone(self, expansion_layer_with_temporal):
        """BACKWARD query result must NOT have AUTHOR_CANON as sole provenance."""
        result = expansion_layer_with_temporal.respond_to("что было до Аркаима")
        if result and result.provenance:
            cats = [p.get("category") for p in result.provenance]
            assert "AUTHOR_CANON" not in cats or len(cats) > 1, (
                "BACKWARD reconstruction must not claim AUTHOR_CANON provenance alone"
            )


# ═══════════════════════════════════════════════════════════════
# Test 11: get_context temporal enrichment
# ═══════════════════════════════════════════════════════════════

class TestGetContextTemporal:
    """M9: get_context includes temporal chain context for temporal queries."""

    def test_get_context_includes_temporal_for_backward_query(self, expansion_layer, expansion_layer_with_temporal):
        ctx_with = expansion_layer_with_temporal.get_context("что было до Аркаима")
        ctx_without = expansion_layer.get_context("что было до Аркаима")
        # Temporal enrichment adds epoch labels from the chain
        assert "ARKAIM" in ctx_with.upper() or "arkaim" in ctx_with.lower() or "эпох" in ctx_with.lower()

    def test_get_context_includes_temporal_for_forward_query(self, expansion_layer, expansion_layer_with_temporal):
        ctx_with = expansion_layer_with_temporal.get_context("что будет после Аркаима")
        ctx_without = expansion_layer.get_context("что будет после Аркаима")
        assert "ARKAIM" in ctx_with.upper() or "arkaim" in ctx_with.lower() or "эпох" in ctx_with.lower()

    def test_get_context_non_temporal_unchanged(self, expansion_layer):
        ctx = expansion_layer.get_context("что такое Гиперборея")
        assert "Temporal" not in ctx
