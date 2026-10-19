"""M8c — контракт секции конфликтов Knowledge trace.

``trace.conflicts`` содержит только канонические ``ConflictRecord``;
заметки ``ContradictionNote`` вынесены в отдельную секцию ``conflict_notes``
со стабильными id. Эти тесты фиксируют границу между двумя типами.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE_DIR = ROOT / "core" / "CORE"
for import_root in (ROOT, CORE_DIR):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))


def _note(description: str, involved: list[str], **extra: str) -> dict:
    return {"description": description, "involved_claims": involved, **extra}


def test_normalize_notes_only_records_become_conflict_notes():
    from core.routes.knowledge_cards import _normalize_conflict_notes

    notes = _normalize_conflict_notes(
        [_note("Противоречие A/B", ["claim_a", "claim_b"])],
        [],
        "entity_1",
    )
    assert len(notes) == 1
    row = notes[0]
    assert row["kind"] == "contradiction"
    assert row["id"].startswith("note:")
    assert row["description"] == "Противоречие A/B"
    assert row["involved_claims"] == ["claim_a", "claim_b"]
    assert "status" not in row, "заметка не должна притворяться каноническим конфликтом"
    assert set(row) <= {"id", "kind", "description", "involved_claims", "source_1_claim", "source_2_claim", "resolution"}


def test_normalize_conflict_notes_empty_when_no_notes():
    from core.routes.knowledge_cards import _normalize_conflict_notes

    canonical = [{"id": "conflict_1", "status": "UNRESOLVED", "claim_ids": ["claim_a", "claim_b"]}]
    assert _normalize_conflict_notes([], canonical, "entity_1") == []
    assert _normalize_conflict_notes([], [], "entity_1") == []


def test_normalize_conflict_notes_drops_duplicates_of_canonical_conflict():
    from core.routes.knowledge_cards import _normalize_conflict_notes

    canonical = [{"id": "conflict_1", "status": "UNRESOLVED", "claim_ids": ["claim_a", "claim_b"]}]
    notes = [
        _note("та же пара", ["claim_a", "claim_b"]),
        _note("другая пара", ["claim_c", "claim_d"]),
    ]
    result = _normalize_conflict_notes(notes, canonical, "entity_1")
    assert [row["description"] for row in result] == ["другая пара"]


def test_normalize_conflict_notes_deduplicates_by_stable_id():
    from core.routes.knowledge_cards import _normalize_conflict_notes

    note = _note("одна и та же заметка", ["claim_a", "claim_b"])
    result = _normalize_conflict_notes([dict(note), dict(note)], [], "entity_1")
    assert len(result) == 1


def test_normalize_conflict_notes_id_is_deterministic_and_entity_scoped():
    from core.routes.knowledge_cards import _normalize_conflict_notes

    note = _note("стабильно", ["claim_a", "claim_b"])
    first = _normalize_conflict_notes([note], [], "entity_1")[0]["id"]
    second = _normalize_conflict_notes([note], [], "entity_1")[0]["id"]
    other = _normalize_conflict_notes([note], [], "entity_2")[0]["id"]
    assert first == second
    assert first != other


def test_conflict_projection_uses_shared_config_path(tmp_path, monkeypatch):
    from config import config
    from core.routes.knowledge_cards import _conflict_projection
    from knowledge.conflict_repository import ConflictRepository
    from schemas.conflict import ConflictRecord, ConflictType

    assert config.knowledge_repo_dir("KNOWLEDGE_CONFLICT_DIR_ABSENT_XYZ") == config.KNOWLEDGE_RUNTIME_DATA_DIR

    ConflictRepository(tmp_path).add(
        ConflictRecord(
            id="conflict_entity_1",
            conflict_type=ConflictType.DIRECT_CONTRADICTION,
            subject_id="entity_1",
            claim_ids=["claim_a", "claim_b"],
        )
    )
    monkeypatch.setenv("KNOWLEDGE_CONFLICT_DIR", str(tmp_path))
    projected = _conflict_projection("entity_1")
    assert [row["id"] for row in projected] == ["conflict_entity_1"]
    assert projected[0]["status"] == "UNRESOLVED"


def test_trace_response_exposes_conflict_notes_section():
    from core.dto.knowledge import KnowledgeTraceResponse

    data = KnowledgeTraceResponse(
        entity_id="entity_1",
        status="PARTIAL",
        conflicts=[{"id": "conflict_1", "status": "UNRESOLVED"}],
        conflict_notes=[{"id": "note:abc", "kind": "contradiction"}],
    ).model_dump()
    assert data["conflicts"][0]["id"] == "conflict_1"
    assert data["conflict_notes"][0]["kind"] == "contradiction"
