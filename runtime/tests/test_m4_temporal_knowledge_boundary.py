"""M4 — Knowledge ↔ Temporal boundary tests."""

from __future__ import annotations

import sys
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

import pytest
from pydantic import ValidationError

from knowledge.temporal_resolver import KnowledgeTemporalResolver
from narrative_engine.source_levels import ProvenanceCategory, ProvenanceTag, SourceLevel
from narrative_engine.temporal.node import TemporalBounds, TemporalNode
from narrative_engine.temporal.precision import TemporalPrecision
from schemas.temporal_reference import TemporalReference, TemporalReferenceStatus, TemporalTimeBasis


class FakeTemporalEngine:
    def __init__(self, nodes: dict[str, TemporalNode]):
        self.nodes = nodes

    def get_node(self, node_id: str):
        return self.nodes.get(node_id)


def _node() -> TemporalNode:
    return TemporalNode(
        id="temporal_arkaim_era",
        label="Аркаим",
        precision=TemporalPrecision.YEAR_RANGE,
        era_id="arkaim_era",
        event_ids=["event_arkaim_construction"],
        bounds=TemporalBounds(start="2500 BCE", end="2000 BCE", uncertainty="±200 лет"),
        provenance=[ProvenanceTag(
            source_level=SourceLevel.CANON,
            category=ProvenanceCategory.AUTHOR_CANON,
            confidence=1.0,
        )],
    )


def test_existing_node_is_resolved_with_precision_and_bounds():
    resolver = KnowledgeTemporalResolver(FakeTemporalEngine({"temporal_arkaim_era": _node()}))
    result = resolver.resolve("claim_1", "temporal_arkaim_era")
    assert result.status is TemporalReferenceStatus.RESOLVED
    assert result.temporal_node_id == "temporal_arkaim_era"
    assert result.event_id == "event_arkaim_construction"
    assert result.era_id == "arkaim_era"
    assert result.precision is TemporalPrecision.YEAR_RANGE
    assert result.bounds["start"] == "2500 BCE"
    assert result.temporal_provenance[0]["category"] == "AUTHOR_CANON"
    assert result.time_basis is TemporalTimeBasis.WORLD


def test_missing_node_is_unresolved_and_does_not_invent_time():
    resolver = KnowledgeTemporalResolver(FakeTemporalEngine({}))
    result = resolver.resolve("claim_1", "temporal_missing")
    assert result.status is TemporalReferenceStatus.UNRESOLVED
    assert result.temporal_node_id is None
    assert result.precision is TemporalPrecision.UNKNOWN
    assert result.bounds is None


def test_missing_id_is_unknown_not_assumed_present_anchor():
    resolver = KnowledgeTemporalResolver(FakeTemporalEngine({}))
    result = resolver.resolve("claim_1", "")
    assert result.status is TemporalReferenceStatus.UNKNOWN
    assert result.time_basis is TemporalTimeBasis.WORLD
    assert result.temporal_node_id is None
    assert result.precision is TemporalPrecision.UNKNOWN


def test_non_world_time_basis_cannot_claim_temporal_position():
    with pytest.raises(ValidationError):
        TemporalReference(
            claim_id="claim_1",
            time_basis=TemporalTimeBasis.ASSERTION,
            status=TemporalReferenceStatus.RESOLVED,
            temporal_node_id="temporal_arkaim_era",
        )


def test_resolved_reference_requires_a_temporal_id():
    with pytest.raises(ValidationError):
        TemporalReference(
            claim_id="claim_1",
            time_basis=TemporalTimeBasis.WORLD,
            status=TemporalReferenceStatus.RESOLVED,
        )


def test_unknown_must_use_unknown_precision():
    with pytest.raises(ValidationError):
        TemporalReference(
            claim_id="claim_1",
            time_basis=TemporalTimeBasis.WORLD,
            status=TemporalReferenceStatus.UNKNOWN,
            precision=TemporalPrecision.EXACT,
        )


def test_resolver_rejects_empty_claim_id():
    resolver = KnowledgeTemporalResolver(FakeTemporalEngine({}))
    with pytest.raises(ValueError):
        resolver.resolve("", "temporal_missing")