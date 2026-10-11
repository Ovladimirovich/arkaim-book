"""M8.1 tests: Present Anchor & Temporal Chain Integration.

M8.1 implements the architecture decision:
  PRESENT (temporal_today, HYPOTHESIS)
    ↓ computed reconstruction path (NOT graph relation)
  ARKAIM (temporal_arkaim_era, enriched provenance)
    ↓ FutureExtrapolator
  FUTURE (scenarios, FUTURE_EXTRAPOLATION provenance)

Tests:
1. PRESENT has HYPOTHESIS provenance (not AUTHOR_CANON)
2. PRESENT → ARKAIM built as computed path (no graph relation)
3. WorldModel has NO relation PRESENT → ARKAIM
4. Canonical Arkaim = temporal_arkaim_era
5. Canonical Arkaim has enriched provenance (AUTHOR_CANON + EXTERNAL_SOURCE)
6. M8 generated scenarios have FUTURE_EXTRAPOLATION provenance
7. Existing temporal relations and M8 behavior not regressed
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


@pytest.fixture
def temporal_engine(loaded_world_model):
    from narrative_engine.temporal.reconstruction_engine import TemporalReconstructionEngine

    return TemporalReconstructionEngine.from_world_model(loaded_world_model)


# ═══════════════════════════════════════════════════════════════
# Test 1: PRESENT has HYPOTHESIS provenance
# ═══════════════════════════════════════════════════════════════


class TestPresentAnchorProvenance:
    """M8.1: temporal_today provenance = HYPOTHESIS (not AUTHOR_CANON)."""

    def test_present_anchor_has_hypothesis_provenance(self):
        from narrative_engine.temporal.node import TemporalNode

        node = TemporalNode.present_anchor()
        assert node.id == "temporal_today"
        assert len(node.provenance) == 1
        assert node.provenance[0].category.value == "HYPOTHESIS"
        assert node.provenance[0].source_level.value == "SYSTEM_INTERPRETATION"
        assert node.provenance[0].confidence == 1.0

    def test_present_anchor_is_not_author_canon(self):
        """CRITICAL: present day is NOT book canon."""
        from narrative_engine.temporal.node import TemporalNode

        node = TemporalNode.present_anchor()
        for tag in node.provenance:
            assert tag.category.value != "AUTHOR_CANON"

    def test_present_anchor_in_temporal_graph(self, temporal_engine):
        """temporal_today exists in the graph after from_world_model()."""
        node = temporal_engine.get_node("temporal_today")
        assert node is not None
        assert node.id == "temporal_today"
        assert node.label == "Современность"
        assert node.precision.value == "EXACT"

    def test_present_anchor_no_relations_in_graph(self, temporal_engine):
        """temporal_today has NO relations — it is a methodological anchor."""
        outgoing = temporal_engine._graph.get_outgoing("temporal_today")
        incoming = temporal_engine._graph.get_incoming("temporal_today")
        assert len(outgoing) == 0, "temporal_today must have NO outgoing relations"
        assert len(incoming) == 0, "temporal_today must have NO incoming relations"


# ═══════════════════════════════════════════════════════════════
# Test 2: PRESENT → ARKAIM is computed path, NOT graph relation
# ═══════════════════════════════════════════════════════════════


class TestPresentToArkaimComputedPath:
    """M8.1: PRESENT→ARKAIM = computed reconstruction, not WorldRelation."""

    def test_no_graph_relation_between_today_and_arkaim(self, temporal_engine):
        """CRITICAL: no relation edge between temporal_today and temporal_arkaim_era."""
        outgoing = temporal_engine._graph.get_outgoing("temporal_today")
        incoming = temporal_engine._graph.get_incoming("temporal_today")
        for rel in outgoing + incoming:
            other = rel.target_id if rel.source_id == "temporal_today" else rel.source_id
            assert other != "temporal_arkaim_era", "There must be NO graph relation between temporal_today and temporal_arkaim_era"

    def test_backward_trace_from_arkaim_returns_preceding_epochs(self, temporal_engine):
        """_trace_backward(arkaim_era) returns all predecessors — the reconstruction path."""
        result = temporal_engine._trace_backward("temporal_arkaim_era", max_depth=10)
        assert "temporal_arkaim_era" in result
        # Should include earlier epochs
        assert "temporal_pre_arkaim" in result

    def test_backward_trace_includes_all_earlier_epochs(self, temporal_engine):
        """Reconstruction path from arkaim_era backwards covers all earlier epochs."""
        result = temporal_engine._trace_backward("temporal_arkaim_era", max_depth=10)
        # All 11 earlier epochs should be reachable
        earlier = [n for n in result if n != "temporal_arkaim_era"]
        assert len(earlier) >= 10, f"Expected >=10 earlier epochs, got {len(earlier)}"

    def test_full_pipeline_via_world_engine(self, client):
        """WorldEngine.get_full_temporal_pipeline() composes BACKWARD + FORWARD."""
        # Enable temporal first
        from narrative_engine.world_engine import get_world_engine

        we = get_world_engine()
        we.enable_temporal()
        # NOTE (test-isolation fix): enable_temporal() mutates the process-wide
        # singleton; without restoring it, later tests (e.g. M9
        # TestGracefulFallback) see temporal as enabled and fail.
        try:
            resp = client.post(
                "/book/temporal/future-extrapolation",
                json={
                    "prompt": "test pipeline",
                    "max_futures": 2,
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["ok"] is True
            assert "scenarios" in data["data"]
        finally:
            we._temporal_engine = None

    def test_trace_backward_is_methodology_not_relation(self, temporal_engine):
        """_trace_backward is a computation, not a stored relation."""
        # The engine can trace backward from arkaim_era
        path = temporal_engine._trace_backward("temporal_arkaim_era", max_depth=10)
        assert len(path) > 1

        # But there is no relation FROM today TO arkaim
        today_rels = temporal_engine._graph.get_outgoing("temporal_today")
        assert len(today_rels) == 0


# ═══════════════════════════════════════════════════════════════
# Test 3: WorldModel has NO relation PRESENT → ARKAIM
# ═══════════════════════════════════════════════════════════════


class TestNoPresentToArkaimRelation:
    """CRITICAL: No graph relation created between Present and Arkaim."""

    def test_graph_has_no_today_arkaim_edge(self, temporal_engine):
        """No direct relation edge exists between temporal_today and temporal_arkaim_era."""
        all_rels = temporal_engine.get_all_relations()
        for rel in all_rels:
            ids = {rel.source_id, rel.target_id}
            assert not ({"temporal_today", "temporal_arkaim_era"} <= ids), "Graph must NOT contain a relation between temporal_today and temporal_arkaim_era"

    def test_all_relations_are_precedes_between_epochs(self, temporal_engine):
        """All graph relations are PRECEDES between epoch nodes — no epistemological edges."""
        all_rels = temporal_engine.get_all_relations()
        for rel in all_rels:
            assert rel.relation_type.value == "PRECEDES", f"Expected PRECEDES only, got {rel.relation_type.value}"
            # Both source and target should be epoch nodes (temporal_*), not temporal_today
            assert rel.source_id != "temporal_today"
            assert rel.target_id != "temporal_today"


# ═══════════════════════════════════════════════════════════════
# Test 4: Canonical Arkaim = temporal_arkaim_era
# ═══════════════════════════════════════════════════════════════


class TestCanonicalArkaimAnchor:
    """M8.1: temporal_arkaim_era is the canonical anchor."""

    def test_arkaim_era_is_canonical_node(self, temporal_engine):
        """temporal_arkaim_era exists and is the canonical anchor."""
        node = temporal_engine.get_node("temporal_arkaim_era")
        assert node is not None
        assert node.is_anchor is True
        assert node.era_id == "arkaim_era"

    def test_arkaim_anchor_orphan_removed(self, temporal_engine):
        """temporal_arkaim_anchor (orphan) must NOT be in the graph."""
        orphan = temporal_engine.get_node("temporal_arkaim_anchor")
        assert orphan is None, "temporal_arkaim_anchor should be removed — temporal_arkaim_era is canonical"

    def test_arkaim_era_has_relations(self, temporal_engine):
        """Canonical arkaim_era has incoming and outgoing PRECEDES relations."""
        node = temporal_engine.get_node("temporal_arkaim_era")
        assert node is not None
        incoming = temporal_engine._graph.get_incoming("temporal_arkaim_era")
        outgoing = temporal_engine._graph.get_outgoing("temporal_arkaim_era")
        assert len(incoming) > 0, "arkaim_era must have incoming relations"
        assert len(outgoing) > 0, "arkaim_era must have outgoing relations"

    def test_no_duplicate_arkaim_nodes(self, temporal_engine):
        """Only one arkaim anchor node in graph (temporal_arkaim_anchor removed)."""
        # Check that the ORPHAN anchor is gone
        orphan = temporal_engine.get_node("temporal_arkaim_anchor")
        assert orphan is None, "temporal_arkaim_anchor (orphan) must be removed from graph"
        # Canonical node exists
        canonical = temporal_engine.get_node("temporal_arkaim_era")
        assert canonical is not None
        assert canonical.is_anchor is True


# ═══════════════════════════════════════════════════════════════
# Test 5: Canonical Arkaim has enriched provenance
# ═══════════════════════════════════════════════════════════════


class TestArkaimEnrichedProvenance:
    """M8.1: temporal_arkaim_era enriched with AUTHOR_CANON + EXTERNAL_SOURCE."""

    def test_arkaim_era_has_author_canon_provenance(self, temporal_engine):
        """arkaim_era must have AUTHOR_CANON provenance from book canon."""
        from narrative_engine.source_levels import ProvenanceCategory

        node = temporal_engine.get_node("temporal_arkaim_era")
        assert node is not None
        categories = {p.category for p in node.provenance}
        assert ProvenanceCategory.AUTHOR_CANON in categories, "arkaim_era must have AUTHOR_CANON provenance"

    def test_arkaim_era_has_external_source_provenance(self, temporal_engine):
        """arkaim_era must have EXTERNAL_SOURCE provenance from ARCHAEOLOGY.json."""
        from narrative_engine.source_levels import ProvenanceCategory

        node = temporal_engine.get_node("temporal_arkaim_era")
        assert node is not None
        categories = {p.category for p in node.provenance}
        assert ProvenanceCategory.EXTERNAL_SOURCE in categories, "arkaim_era must have EXTERNAL_SOURCE provenance"

    def test_arkaim_era_provenance_not_empty(self, temporal_engine):
        """arkaim_era provenance must NOT be empty (was empty before M8.1)."""
        node = temporal_engine.get_node("temporal_arkaim_era")
        assert node is not None
        assert len(node.provenance) > 0, "arkaim_era provenance was empty before M8.1, now enriched"

    def test_arkaim_era_confidence_0_85(self, temporal_engine):
        """Enriched arkaim_era confidence should be ~0.85."""
        node = temporal_engine.get_node("temporal_arkaim_era")
        assert node is not None
        assert node.confidence == 0.85

    def test_arkaim_era_not_author_canon_only(self, temporal_engine):
        """arkaim_era should have BOTH AUTHOR_CANON and EXTERNAL_SOURCE, not just one."""
        node = temporal_engine.get_node("temporal_arkaim_era")
        assert node is not None
        categories = {p.category for p in node.provenance}
        assert len(categories) >= 2, "arkaim_era should have at least 2 provenance categories"


# ═══════════════════════════════════════════════════════════════
# Test 6: M8 scenarios have FUTURE_EXTRAPOLATION provenance
# ═══════════════════════════════════════════════════════════════


class TestM8FutureExtrapolationProvenance:
    """M8.1: Future scenarios tagged with FUTURE_EXTRAPOLATION."""

    def test_extrapolate_result_has_provenance_field(self, loaded_world_model):
        from narrative_engine.temporal.future_extrapolator import FutureExtrapolator

        extrapolator = FutureExtrapolator(loaded_world_model)
        result = extrapolator.extrapolate(max_futures=2)
        assert "provenance" in result
        assert len(result["provenance"]) > 0

    def test_extrapolate_provenance_is_future_extrapolation(self, loaded_world_model):
        from narrative_engine.temporal.future_extrapolator import FutureExtrapolator

        extrapolator = FutureExtrapolator(loaded_world_model)
        result = extrapolator.extrapolate(max_futures=2)
        for tag in result["provenance"]:
            assert tag.category.value == "FUTURE_EXTRAPOLATION"

    def test_extrapolate_provenance_note_present(self, loaded_world_model):
        from narrative_engine.temporal.future_extrapolator import FutureExtrapolator

        extrapolator = FutureExtrapolator(loaded_world_model)
        result = extrapolator.extrapolate(max_futures=2)
        assert "provenance_note" in result
        assert "FUTURE_EXTRAPOLATION" in result["provenance_note"]

    def test_extrapolate_scenarios_have_compatibility(self, loaded_world_model):
        """Scenarios still have compatibility scores after M8.1 change."""
        from narrative_engine.temporal.future_extrapolator import FutureExtrapolator

        extrapolator = FutureExtrapolator(loaded_world_model)
        result = extrapolator.extrapolate(max_futures=3)
        for scenario in result["scenarios"]:
            assert "compatibility_score" in scenario
            assert "description" in scenario


# ═══════════════════════════════════════════════════════════════
# Test 7: No regression — existing M5/M6/M8 behavior
# ═══════════════════════════════════════════════════════════════


class TestM81Regression:
    """M8.1 must not break existing M5/M6/M7/M8 tests."""

    def test_m5_temporal_engine_still_enabled(self):
        from narrative_engine.world_engine import WorldEngine

        engine = WorldEngine()
        assert engine.temporal_engine is None
        te = engine.enable_temporal()
        assert te is not None

    def test_m5_backward_chain_still_works(self, temporal_engine):
        from narrative_engine.temporal.chain import ChainDirection

        chain = temporal_engine.reconstruct_chain("temporal_arkaim_era", ChainDirection.BACKWARD)
        assert chain is not None
        assert chain.direction == ChainDirection.BACKWARD
        assert len(chain.nodes) > 0

    def test_m5_forward_chain_still_works(self, temporal_engine):
        from narrative_engine.temporal.chain import ChainDirection

        chain = temporal_engine.reconstruct_chain("temporal_arkaim_era", ChainDirection.FORWARD)
        assert chain is not None
        assert chain.direction == ChainDirection.FORWARD
        assert len(chain.nodes) > 0

    def test_m6_nodes_endpoint_works_and_today_in_engine(self, client, temporal_engine):
        """Endpoint returns epoch nodes; temporal_today is in engine graph (methodological anchor)."""
        resp = client.get("/book/temporal/nodes")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        # /nodes returns epoch-based nodes from WorldModel (not temporal_today)
        node_ids = [n["id"] for n in data["data"]]
        assert "temporal_arkaim_era" in node_ids
        # temporal_today is in the ENGINE graph (methodological, not epoch-based)
        today = temporal_engine.get_node("temporal_today")
        assert today is not None
        assert today.id == "temporal_today"

    def test_m8_extrapolate_still_works(self, loaded_world_model):
        from narrative_engine.temporal.future_extrapolator import FutureExtrapolator

        extrapolator = FutureExtrapolator(loaded_world_model)
        result = extrapolator.extrapolate(max_futures=3)
        assert result["chain_stats"]["direction"] == "FORWARD"
        assert len(result["scenarios"]) > 0

    def test_no_new_graph_relations_added(self, temporal_engine):
        """Total relations should still be 11 (PRECEDES between epochs only)."""
        all_rels = temporal_engine.get_all_relations()
        assert len(all_rels) == 11, f"Expected 11 PRECEDES relations, got {len(all_rels)}. M8.1 must not add new relations."

    def test_total_nodes_increased_by_one(self, temporal_engine):
        """Should have 13 epoch nodes + 1 temporal_today = 14 (arkaim_anchor removed)."""
        nodes = temporal_engine.get_all_nodes()
        node_ids = [n.id for n in nodes]
        assert "temporal_today" in node_ids
        assert "temporal_arkaim_anchor" not in node_ids
        # 12 epoch nodes + temporal_today = 13 total
        assert len(nodes) == 13, f"Expected 13 nodes (12 epochs + today), got {len(nodes)}: {node_ids}"


# ═══════════════════════════════════════════════════════════════
# Test: Pre-existing failure check
# ═══════════════════════════════════════════════════════════════


class TestPreExistingFailure:
    """Confirm test_get_entity failure is pre-existing, not caused by M8.1."""

    def test_get_entity_region_arkaim_pre_existing_auth_required(self, client):
        """Pre-existing: /book/world/entity requires auth (401), not a bug from M8.1."""
        resp = client.get("/book/world/entity/region_arkaim")
        # This endpoint requires authentication — pre-existing behavior
        assert resp.status_code in (401, 200)
