"""M3 — Knowledge ↔ World boundary tests."""

from __future__ import annotations

import sys
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

import pytest
from pydantic import ValidationError

from knowledge.world_resolver import WorldKnowledgeResolver
from schemas.world_reference import WorldEntityReference, WorldReferenceStatus, WorldRelationReference


class FakeEngine:
    def __init__(self, entities: dict[str, dict], search: dict[str, list[dict]] | None = None):
        self.entities = entities
        self.search_results = search or {}

    def get_entity(self, entity_id: str) -> dict | None:
        return self.entities.get(entity_id)

    def search(self, query: str):
        return {"world_model": self.search_results.get(query, [])}


def resolver(entities, approved=None, search=None) -> WorldKnowledgeResolver:
    instance = WorldKnowledgeResolver(world_engine=FakeEngine(entities, search))
    instance._approved = approved or {}
    return instance


def test_direct_canonical_id_is_resolved_without_crosswalk():
    result = resolver({"region_arkaim": {"id": "region_arkaim", "name": "Аркаим", "provenance": {"status": "available"}}}).resolve("region_arkaim")
    assert result.status is WorldReferenceStatus.RESOLVED
    assert result.canonical_id == "region_arkaim"
    assert result.resolution_method == "canonical_id"
    assert result.world_provenance == {"status": "available"}


def test_approved_alias_resolves_to_canonical_entity():
    result = resolver(
        {"region_arkaim": {"id": "region_arkaim", "name": "Аркаим"}},
        approved={"аркаим": ["region_arkaim"]},
    ).resolve("аркаим")
    assert result.status is WorldReferenceStatus.RESOLVED
    assert result.canonical_id == "region_arkaim"
    assert result.resolution_method == "approved_crosswalk"


def test_ambiguous_approved_mapping_is_not_resolved():
    result = resolver({}, approved={"location": ["a", "b"]}).resolve("location")
    assert result.status is WorldReferenceStatus.AMBIGUOUS
    assert result.canonical_id is None
    assert "multiple candidates" in result.reason


def test_unresolved_does_not_invent_identity():
    result = resolver({}).resolve("not-in-world")
    assert result.status is WorldReferenceStatus.UNRESOLVED
    assert result.canonical_id is None


def test_exact_known_entity_without_approved_crosswalk_is_unapproved():
    result = resolver({}, search={"candidate": [{"id": "candidate", "name": "Candidate"}]}).resolve("candidate")
    assert result.status is WorldReferenceStatus.CROSSWALK_UNAPPROVED
    assert result.canonical_id is None
    assert result.resolution_method == "unapproved_candidate"


def test_empty_query_is_rejected():
    with pytest.raises(ValueError):
        resolver({}).resolve("  ")


def test_resolved_requires_canonical_id():
    with pytest.raises(ValidationError):
        WorldEntityReference(query="x", status=WorldReferenceStatus.RESOLVED)


def test_non_resolved_cannot_claim_canonical_id():
    with pytest.raises(ValidationError):
        WorldEntityReference(query="x", canonical_id="x", status=WorldReferenceStatus.UNRESOLVED)


def test_knowledge_provenance_cannot_replace_relation_provenance():
    with pytest.raises(ValidationError):
        WorldRelationReference(
            relation_id="relation_1",
            source_entity_id="a",
            target_entity_id="b",
            relation_type="related_to",
            knowledge_provenance={"category": "EXTERNAL_SOURCE"},
        )


def test_relation_provenance_is_independent_and_explicit():
    relation = WorldRelationReference(
        relation_id="relation_1",
        source_entity_id="a",
        target_entity_id="b",
        relation_type="related_to",
        relation_provenance={"category": "DERIVED", "source": "world_engine"},
    )
    assert relation.world_relation is True
    assert relation.knowledge_provenance is None
    assert relation.relation_provenance["category"] == "DERIVED"
