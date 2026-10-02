"""M5 — competing claims and conflict lifecycle tests."""

from __future__ import annotations

import sys
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

import pytest
from pydantic import ValidationError

from knowledge.conflict_repository import ConflictRepository
from schemas.conflict import ConflictRecord, ConflictStatus, ConflictType


def record(**overrides) -> ConflictRecord:
    data = {
        "id": "conflict_1",
        "conflict_type": ConflictType.DIRECT_CONTRADICTION,
        "subject_id": "entity_1",
        "claim_ids": ["claim_1", "claim_2"],
        "evidence_ids": ["evidence_1", "evidence_2"],
        "world_entity_ids": ["region_arkaim"],
        "temporal_reference_ids": ["temporal_1"],
        "explanation": "Sources disagree.",
    }
    data.update(overrides)
    return ConflictRecord(**data)


def test_competing_claims_remain_distinct_and_unresolved_by_default():
    conflict = record()
    assert conflict.status is ConflictStatus.UNRESOLVED
    assert conflict.claim_ids == ["claim_1", "claim_2"]
    assert conflict.evidence_ids == ["evidence_1", "evidence_2"]
    assert conflict.resolution_claim_id is None


def test_duplicate_claim_ids_are_rejected():
    with pytest.raises(ValidationError):
        record(claim_ids=["claim_1", "claim_1"])


def test_resolution_requires_explicit_claim_and_reason():
    with pytest.raises(ValidationError):
        record(status=ConflictStatus.RESOLVED_WITH_EVIDENCE, resolution_claim_id="claim_3")
    resolved = record(
        status=ConflictStatus.RESOLVED_WITH_EVIDENCE,
        resolution_claim_id="claim_3",
        resolution_reason="A later verified interpretation reconciles the claims.",
        resolved_at="2026-10-01T00:00:00Z",
    )
    assert resolved.resolution_claim_id == "claim_3"


def test_non_resolved_record_cannot_claim_resolution():
    with pytest.raises(ValidationError):
        record(resolution_claim_id="claim_3")


def test_perspective_status_does_not_select_a_winner():
    conflict = record(status=ConflictStatus.ACCEPTED_AS_PERSPECTIVES)
    assert conflict.status is ConflictStatus.ACCEPTED_AS_PERSPECTIVES
    assert conflict.resolution_claim_id is None


def test_repository_round_trip_preserves_lineage(tmp_path):
    repository = ConflictRepository(tmp_path)
    repository.add(record())
    loaded = repository.get("conflict_1")
    assert loaded is not None
    assert loaded.claim_ids == ["claim_1", "claim_2"]
    assert loaded.evidence_ids == ["evidence_1", "evidence_2"]


def test_resolution_updates_metadata_without_removing_competing_claims(tmp_path):
    repository = ConflictRepository(tmp_path)
    repository.add(record())
    resolved = repository.resolve_with_evidence(
        "conflict_1",
        resolution_claim_id="claim_3",
        resolution_reason="Evidence-backed correction.",
        resolved_at="2026-10-01T00:00:00Z",
    )
    assert resolved.status is ConflictStatus.RESOLVED_WITH_EVIDENCE
    assert resolved.claim_ids == ["claim_1", "claim_2"]
    assert resolved.evidence_ids == ["evidence_1", "evidence_2"]
    assert repository.get("conflict_1").resolution_claim_id == "claim_3"


def test_perspectives_can_be_marked_without_fabricated_resolution(tmp_path):
    repository = ConflictRepository(tmp_path)
    repository.add(record())
    updated = repository.accept_as_perspectives("conflict_1")
    assert updated.status is ConflictStatus.ACCEPTED_AS_PERSPECTIVES
    assert updated.resolution_claim_id is None


def test_filtering_by_subject_and_status(tmp_path):
    repository = ConflictRepository(tmp_path)
    repository.add(record())
    repository.add(record(id="conflict_2", subject_id="entity_2", claim_ids=["claim_3", "claim_4"]))
    assert len(repository.list(subject_id="entity_1")) == 1
    assert len(repository.list(status="UNRESOLVED")) == 2