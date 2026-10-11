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


def test_evidence_row_carries_the_same_claim_id_as_the_claim(tmp_path, monkeypatch):
    """A bridged book claim yields one identity, identical in claims and evidence."""
    import json

    from narrative_engine.provenance.claim import CanonClaim
    from core.routes.knowledge_cards import _card_claim_id, _evidence_projection

    catalog = tmp_path / "enriched_catalog.json"
    catalog.write_text(
        json.dumps([{"id": "chunk_t4_hit", "text": "Fragment text", "chapter_title": "Часть 0"}]),
        encoding="utf-8",
    )
    monkeypatch.setenv("KNOWLEDGE_EVIDENCE_CATALOG", str(catalog))

    claim = {
        "id": "claim_t4_book",
        "source_ref": "book:chunk_t4_hit",
        "chunk_id": "chunk_t4_hit",
        "text": "Fragment text",
        "provenance": {"source_title": "Наследие Аркаима"},
    }
    payload = {"sources": [{"source_name": "book", "claims": [claim]}]}
    rows = _evidence_projection(payload)

    expected = CanonClaim.make_id("Fragment text", source_id="book", location="chunk:chunk_t4_hit")
    assert rows[0]["claim_id"] == expected
    assert rows[0]["claim_id"] == _card_claim_id(claim), "claims and evidence sections must agree on identity"
    assert rows[0]["status"] == "RESOLVED"


def test_evidence_claim_id_is_independent_of_resolution_status(tmp_path, monkeypatch):
    """RESOLVED / UNAVAILABLE / UNKNOWN outcomes never create or drop an identity."""
    import json

    from core.routes.knowledge_cards import _evidence_projection

    catalog = tmp_path / "enriched_catalog.json"
    catalog.write_text(
        json.dumps([{"id": "chunk_t4_hit", "text": "Fragment text", "chapter_title": "Часть 0"}]),
        encoding="utf-8",
    )
    monkeypatch.setenv("KNOWLEDGE_EVIDENCE_CATALOG", str(catalog))

    payload = {
        "sources": [
            {
                "source_name": "book",
                "claims": [
                    {"id": "hit", "source_ref": "book:chunk_t4_hit", "chunk_id": "chunk_t4_hit", "text": "Fragment text", "provenance": {}},
                    {"id": "missing", "source_ref": "book:chunk_t4_absent", "chunk_id": "chunk_t4_absent", "text": "Absent text", "provenance": {}},
                    {"id": "no_chunk", "source_ref": "book:chunk", "chunk_id": None, "text": "No chunk text", "provenance": {}},
                ],
            }
        ]
    }
    rows = {row["source_ref"]: row for row in _evidence_projection(payload)}

    # identity comes from the claim bridge, not from the resolver outcome:
    # RESOLVED and UNAVAILABLE rows carry the same bridged claim_id
    assert rows["book:chunk_t4_hit"]["status"] == "RESOLVED" and rows["book:chunk_t4_hit"]["claim_id"]
    assert rows["book:chunk_t4_absent"]["status"] == "UNAVAILABLE"
    assert rows["book:chunk_t4_absent"]["evidence_id"] is None, "UNAVAILABLE keeps no evidence record"
    assert rows["book:chunk_t4_absent"]["claim_id"], "identity survives a missing evidence record"
    # UNKNOWN without a stable chunk stays unlinked: the status never invents an identity
    assert rows["book:chunk"]["status"] == "UNKNOWN" and rows["book:chunk"]["claim_id"] is None


def test_evidence_row_exposes_claim_id_for_external_archaeology_ref(tmp_path, monkeypatch):
    """A canonical external locator bridges to the same external identity as the claim."""
    from narrative_engine.provenance.claim import CanonClaim
    from core.routes.knowledge_cards import _card_claim_id, _evidence_projection

    monkeypatch.setenv("KNOWLEDGE_EVIDENCE_CATALOG", str(tmp_path / "does_not_exist.json"))

    claim = {
        "id": "claim_t4_arch",
        "source_ref": "ARCHAEOLOGY.json:sinta_sha",
        "chunk_id": None,
        "text": "Синташта — город бронзового века",
        "provenance": {},
    }
    rows = _evidence_projection({"sources": [{"source_name": "archaeology", "claims": [claim]}]})

    expected = CanonClaim.make_id(claim["text"], source_id="archaeology", location="external:archaeology:sinta_sha")
    assert rows[0]["claim_id"] == expected == _card_claim_id(claim)


def test_evidence_claim_id_stays_null_without_reliable_bridge(tmp_path, monkeypatch):
    """Genome/world refs, chunk-less book refs and empty text get no guessed identity."""
    from core.routes.knowledge_cards import _evidence_projection

    monkeypatch.setenv("KNOWLEDGE_EVIDENCE_CATALOG", str(tmp_path / "does_not_exist.json"))

    payload = {
        "sources": [
            {
                "source_name": "mixed",
                "claims": [
                    {"id": "genome", "source_ref": "genome:theme:theme_129", "chunk_id": None, "text": "Тема генома", "provenance": {}},
                    {"id": "world", "source_ref": "world_model:region_arkaim", "chunk_id": None, "text": "Границы региона", "provenance": {}},
                    {"id": "no_chunk", "source_ref": "book:chunk", "chunk_id": None, "text": "Текст без чанка", "provenance": {}},
                    {"id": "no_text", "source_ref": "book:chunk_no_text", "chunk_id": "chunk_no_text", "text": "", "provenance": {}},
                ],
            }
        ]
    }
    rows = _evidence_projection(payload)

    assert len(rows) == 4, "rows stay projected, only identity is withheld"
    assert all(row["claim_id"] is None for row in rows)
    assert all("claim_id" in row for row in rows), "claim_id is always present, null when unbridgeable"


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


# ---------------------------------------------------------------------------
# GO-1 — правило trace.status (зафиксировано 2026-10-11, §2.5 SoT)
# ---------------------------------------------------------------------------


class _FakeCard:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def to_dict(self) -> dict:
        return self._payload


class _FakeBuilder:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def build(self, entity_id: str) -> _FakeCard:
        return _FakeCard(self._payload)


def _trace_status_client(tmp_path, monkeypatch, claims: list[dict]):
    """Trace endpoint поверх фейкового builder'а и изолированных репозиториев."""
    import json

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from core.routes import knowledge_cards as kc

    catalog = tmp_path / "enriched_catalog.json"
    catalog.write_text(
        json.dumps([{"id": "chunk_go1_hit", "text": "Fragment text", "chapter_title": "Часть 0"}]),
        encoding="utf-8",
    )
    monkeypatch.setenv("KNOWLEDGE_EVIDENCE_CATALOG", str(catalog))
    monkeypatch.setenv("KNOWLEDGE_CONFLICT_DIR", str(tmp_path))
    monkeypatch.setenv("KNOWLEDGE_REASONING_DIR", str(tmp_path))
    monkeypatch.setenv("KNOWLEDGE_CORRECTION_DIR", str(tmp_path))

    payload = {
        "primary_entity": {"canonical_id": "entity_go1", "name": "Тестовая сущность"},
        "sources": [{"source_name": "book", "claims": claims}],
        "contradictions": [],
    }
    monkeypatch.setattr("knowledge_card.get_card_builder", lambda: _FakeBuilder(payload))

    app = FastAPI()
    app.include_router(kc.router)
    checker = kc.router.dependencies[0].dependency
    app.dependency_overrides[checker] = lambda: {
        "user_id": "go1-reader",
        "role": "reader",
        "provider": "test",
        "username": "go1_reader",
        "display_name": "GO1 Reader",
    }
    return TestClient(app)


_GO1_RESOLVED_CLAIM = {
    "id": "claim_go1_hit",
    "source_ref": "book:chunk_go1_hit",
    "chunk_id": "chunk_go1_hit",
    "text": "Подтверждённое утверждение",
    "provenance": {"source_title": "Наследие Аркаима"},
}
_GO1_UNAVAILABLE_CLAIM = {
    "id": "claim_go1_miss",
    "source_ref": "book:chunk_go1_miss",
    "chunk_id": "chunk_go1_miss",
    "text": "Недоступное утверждение",
    "provenance": {"source_title": "Наследие Аркаима"},
}
_GO1_UNKNOWN_CLAIM = {
    "id": "claim_go1_unknown",
    "source_ref": "world_model:entity_go1",
    "chunk_id": None,
    "text": "Утверждение мировой модели",
    "provenance": {},
}


def _go1_trace(client, **params) -> dict:
    response = client.get("/knowledge/cards/trace/entity_go1", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_trace_status_complete_when_every_evidence_is_resolved(tmp_path, monkeypatch):
    """GO-1: закрытый путь (все evidence RESOLVED, нет limitations) -> COMPLETE."""
    client = _trace_status_client(tmp_path, monkeypatch, [_GO1_RESOLVED_CLAIM])

    data = _go1_trace(client)
    assert data["limitations"] == []
    assert [row["status"] for row in data["evidence"]] == ["RESOLVED"]
    assert data["status"] == "COMPLETE"


def test_trace_status_partial_on_unavailable_evidence_without_limitations(tmp_path, monkeypatch):
    """GO-1: обрыв пути к source (UNAVAILABLE) -> PARTIAL даже при пустых limitations."""
    client = _trace_status_client(tmp_path, monkeypatch, [_GO1_RESOLVED_CLAIM, _GO1_UNAVAILABLE_CLAIM])

    data = _go1_trace(client)
    assert data["limitations"] == []
    assert {row["status"] for row in data["evidence"]} == {"RESOLVED", "UNAVAILABLE"}
    assert data["status"] == "PARTIAL"

    # статус считается по полному набору: фильтр не поднимает обратно COMPLETE
    filtered = _go1_trace(client, evidence_status="RESOLVED")
    assert [row["status"] for row in filtered["evidence"]] == ["RESOLVED"]
    assert filtered["status"] == "PARTIAL"


def test_trace_status_partial_on_unknown_evidence_live_case(tmp_path, monkeypatch):
    """GO-1/live №1: UNKNOWN evidence больше не даёт COMPLETE (region_arkaim-кейс)."""
    client = _trace_status_client(tmp_path, monkeypatch, [_GO1_RESOLVED_CLAIM, _GO1_UNKNOWN_CLAIM])

    data = _go1_trace(client)
    assert data["limitations"] == []
    assert {row["status"] for row in data["evidence"]} == {"RESOLVED", "UNKNOWN"}
    assert data["status"] == "PARTIAL"
