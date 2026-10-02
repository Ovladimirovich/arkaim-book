"""M8 — read-only Knowledge trace DTO contract tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE_DIR = ROOT / "core" / "CORE"
for import_root in (ROOT, CORE_DIR):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from core.dto.knowledge import KnowledgeTraceResponse, TraceabilityStatus


def test_trace_response_preserves_traceability_sections():
    response = KnowledgeTraceResponse(
        entity_id="region_arkaim",
        status=TraceabilityStatus.PARTIAL,
        claims=[{"text": "claim"}],
        evidence=[{"evidence_id": "evidence_1", "status": "RESOLVED"}],
        world={"canonical_id": "region_arkaim"},
        temporal=[{"temporal_node_id": "temporal_arkaim_era"}],
        conflicts=[{"claim_ids": ["claim_1", "claim_2"]}],
        reasoning=[{"input_claim_ids": ["claim_1", "claim_2"]}],
        corrections=[{"finding_id": "finding_1", "status": "PENDING"}],
        uncertainty={"has_unknowns": True},
        limitations=["partial projection"],
    )
    data = response.model_dump()
    assert data["entity_id"] == "region_arkaim"
    assert data["claims"][0]["text"] == "claim"
    assert data["evidence"][0]["evidence_id"] == "evidence_1"
    assert data["world"]["canonical_id"] == "region_arkaim"
    assert data["temporal"][0]["temporal_node_id"] == "temporal_arkaim_era"
    assert data["conflicts"][0]["claim_ids"] == ["claim_1", "claim_2"]
    assert data["reasoning"][0]["input_claim_ids"] == ["claim_1", "claim_2"]
    assert data["corrections"][0]["status"] == "PENDING"
    assert data["limitations"] == ["partial projection"]


def test_trace_response_has_no_mutation_fields():
    fields = set(KnowledgeTraceResponse.model_fields)
    assert not ({"create", "update", "delete", "confirm", "reject"} & fields)


def test_trace_status_vocabulary_is_explicit():
    assert TraceabilityStatus.COMPLETE == "COMPLETE"
    assert TraceabilityStatus.PARTIAL == "PARTIAL"
    assert TraceabilityStatus.UNKNOWN == "UNKNOWN"


def test_trace_query_filters_and_pagination_are_stable():
    from core.routes.knowledge_cards import _matches, _page

    claims = [{"id": f"claim_{index}", "provenance": {"category": "DERIVED" if index % 2 else "AUTHOR_CANON"}} for index in range(5)]
    filtered = [claim for claim in claims if _matches(claim["provenance"]["category"], "DERIVED")]
    page, next_offset = _page(filtered, 1, 1)
    assert [claim["id"] for claim in page] == ["claim_3"]
    assert next_offset is None


def test_trace_projection_includes_persisted_m7_corrections(tmp_path, monkeypatch):
    from knowledge.correction_repository import CorrectionRepository
    from schemas.correction import CorrectionRecord
    from core.routes.knowledge_cards import _correction_projection

    CorrectionRepository(tmp_path).add(
        CorrectionRecord(
            id="correction_entity_1",
            finding_id="finding_1",
            subject_id="entity_1",
            superseded_claim_ids=["claim_old"],
            evidence_ids=["evidence_1"],
            temporal_reference_ids=["temporal_1"],
        )
    )
    monkeypatch.setenv("KNOWLEDGE_CORRECTION_DIR", str(tmp_path))
    projected = _correction_projection("entity_1")
    assert projected[0]["id"] == "correction_entity_1"
    assert projected[0]["status"] == "PENDING"
    assert projected[0]["superseded_claim_ids"] == ["claim_old"]


def test_evidence_projection_resolves_book_chunks_via_catalog(tmp_path, monkeypatch):
    """M2 resolver outcome drives the trace evidence rows: RESOLVED / UNAVAILABLE / UNKNOWN."""
    import json

    from core.routes.knowledge_cards import _evidence_projection

    catalog = tmp_path / "enriched_catalog.json"
    catalog.write_text(
        json.dumps([{"id": "chunk_p_0001_16fc149672e4", "text": "Fragment text", "chapter_title": "Часть 0"}]),
        encoding="utf-8",
    )
    monkeypatch.setenv("KNOWLEDGE_EVIDENCE_CATALOG", str(catalog))

    payload = {
        "sources": [
            {
                "source_name": "book",
                "claims": [
                    {
                        "id": "claim_book_hit",
                        "source_ref": "book:chunk_p_0001_16fc149672e4",
                        "chunk_id": "chunk_p_0001_16fc149672e4",
                        "provenance": {"source_title": "Наследие Аркаима"},
                    },
                    {
                        "id": "claim_book_miss",
                        "source_ref": "book:chunk_missing",
                        "chunk_id": "chunk_missing",
                        "provenance": {"source_title": "Наследие Аркаима"},
                    },
                    {"id": "claim_book_no_chunk", "source_ref": "book:chunk", "chunk_id": None, "provenance": {}},
                ],
            },
            {
                "source_name": "world",
                "claims": [{"id": "claim_world", "source_ref": "world_model:region_arkaim", "chunk_id": None, "provenance": {}}],
            },
        ]
    }

    rows = {row["source_ref"]: row for row in _evidence_projection(payload)}
    resolved = rows["book:chunk_p_0001_16fc149672e4"]
    assert resolved["status"] == "RESOLVED"
    assert resolved["evidence_id"], "RESOLVED row must expose the evidence record id"
    assert resolved["chunk_id"] == "chunk_p_0001_16fc149672e4"
    assert resolved["source_title"] == "Наследие Аркаима"

    missing = rows["book:chunk_missing"]
    assert missing["status"] == "UNAVAILABLE"
    assert missing["evidence_id"] is None
    assert "chunk_missing" in missing["reason"]

    assert rows["book:chunk"]["status"] == "UNKNOWN"
    assert rows["world_model:region_arkaim"]["status"] == "UNKNOWN"
    # unsupported locator schemes never get silently upgraded to a resolved state
    assert rows["world_model:region_arkaim"]["evidence_id"] is None


def test_evidence_projection_never_fabricates_rows(tmp_path, monkeypatch):
    from core.routes.knowledge_cards import _evidence_projection

    monkeypatch.setenv("KNOWLEDGE_EVIDENCE_CATALOG", str(tmp_path / "does_not_exist.json"))
    payload = {"sources": [{"source_name": "book", "claims": [{"id": "claim", "source_ref": "", "chunk_id": None}]}]}
    assert _evidence_projection(payload) == []


def test_trace_projection_includes_persisted_m5_conflicts(tmp_path, monkeypatch):
    from knowledge.conflict_repository import ConflictRepository
    from schemas.conflict import ConflictRecord, ConflictType
    from core.routes.knowledge_cards import _conflict_projection

    ConflictRepository(tmp_path).add(
        ConflictRecord(
            id="conflict_entity_1",
            conflict_type=ConflictType.SOURCE_PERSPECTIVE,
            subject_id="entity_1",
            claim_ids=["claim_1", "claim_2"],
            evidence_ids=["evidence_1", "evidence_2"],
            explanation="Two source perspectives remain separate.",
        )
    )
    monkeypatch.setenv("KNOWLEDGE_CONFLICT_DIR", str(tmp_path))

    projected = _conflict_projection("entity_1")
    assert len(projected) == 1
    assert projected[0]["id"] == "conflict_entity_1"
    assert projected[0]["status"] == "UNRESOLVED"
    assert projected[0]["claim_ids"] == ["claim_1", "claim_2"]
    assert projected[0]["evidence_ids"] == ["evidence_1", "evidence_2"]
