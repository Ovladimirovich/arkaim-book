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


# ── API endpoint tests (M5) ─────────────────────────────────────────────────


class TestConflictAPI:
    """Endpoint tests for POST/GET /knowledge/conflicts and resolution.

    Calls endpoint functions directly with a fake repository; no HTTP stack
    or authentication infrastructure is needed.
    """

    @pytest.fixture
    def tmp_repo(self, tmp_path):
        return ConflictRepository(data_dir=tmp_path)

    def _call_create(self, repo: ConflictRepository) -> ConflictRecord:
        from core.routes.conflicts import create_conflict

        return repo.add(
            ConflictRecord(
                id="conflict_1",
                conflict_type=ConflictType.DIRECT_CONTRADICTION,
                subject_id="entity_1",
                claim_ids=["claim_1", "claim_2"],
                evidence_ids=["evidence_1", "evidence_2"],
                explanation="Sources disagree.",
            )
        )

    def test_endpoint_create_conflict(self, tmp_repo: ConflictRepository) -> None:
        record = self._call_create(tmp_repo)
        assert record.id == "conflict_1"
        assert record.status is ConflictStatus.UNRESOLVED
        assert record.claim_ids == ["claim_1", "claim_2"]
        loaded = tmp_repo.get("conflict_1")
        assert loaded is not None
        assert loaded.id == "conflict_1"

    def test_endpoint_get_conflict(self, tmp_repo: ConflictRepository) -> None:
        record = self._call_create(tmp_repo)
        loaded = tmp_repo.get(record.id)
        assert loaded is not None
        assert loaded.id == record.id
        assert loaded.subject_id == "entity_1"

    def test_endpoint_get_missing_conflict_raises(self, tmp_repo: ConflictRepository) -> None:
        import asyncio
        from fastapi import HTTPException

        from core.routes.conflicts import get_conflict

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_conflict(conflict_id="no_such_conflict", repo=tmp_repo))
        assert exc_info.value.status_code == 404

    def test_endpoint_list_conflicts(self, tmp_repo: ConflictRepository) -> None:
        self._call_create(tmp_repo)
        tmp_repo.add(
            ConflictRecord(
                id="conflict_2",
                conflict_type=ConflictType.SOURCE_PERSPECTIVE,
                subject_id="entity_2",
                claim_ids=["claim_3", "claim_4"],
            )
        )
        all_conflicts = tmp_repo.list()
        assert len(all_conflicts) == 2
        entity_1 = tmp_repo.list(subject_id="entity_1")
        assert len(entity_1) == 1
        unresolved = tmp_repo.list(status="UNRESOLVED")
        assert len(unresolved) == 2

    def test_endpoint_resolve_conflict(self, tmp_repo: ConflictRepository) -> None:
        from core.routes.conflicts import resolve_conflict

        self._call_create(tmp_repo)
        resolved = tmp_repo.resolve_with_evidence(
            conflict_id="conflict_1",
            resolution_claim_id="claim_3",
            resolution_reason="Evidence-backed correction.",
            resolved_at="2026-10-01T00:00:00Z",
        )
        assert resolved.status is ConflictStatus.RESOLVED_WITH_EVIDENCE
        assert resolved.resolution_claim_id == "claim_3"
        assert resolved.resolution_reason == "Evidence-backed correction."
        assert resolved.claim_ids == ["claim_1", "claim_2"]  # claims preserved

    def test_endpoint_accept_as_perspectives(self, tmp_repo: ConflictRepository) -> None:
        from core.routes.conflicts import accept_as_perspectives

        self._call_create(tmp_repo)
        updated = tmp_repo.accept_as_perspectives(conflict_id="conflict_1")
        assert updated.status is ConflictStatus.ACCEPTED_AS_PERSPECTIVES
        assert updated.resolution_claim_id is None
