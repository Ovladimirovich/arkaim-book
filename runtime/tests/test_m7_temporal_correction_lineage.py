"""M7 — temporal provenance correction lineage tests."""

from __future__ import annotations

import sys
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

import pytest
from pydantic import ValidationError

from knowledge.correction_repository import CorrectionRepository
from narrative_engine.research.temporal_extractor import TemporalFinding
from narrative_engine.source_levels import ProvenanceCategory
from schemas.correction import CorrectionRecord, CorrectionStatus


def finding() -> TemporalFinding:
    return TemporalFinding(
        id="finding_1",
        kind="absolute_date",
        raw_text="~4000 лет до н.э.",
        value="epoch:arkaim_era",
        line_number=42,
        context="Аркаим появился ~4000 лет до н.э.",
        category=ProvenanceCategory.AUTHOR_CANON,
        confidence=0.9,
    )


def correction() -> CorrectionRecord:
    return CorrectionRecord(
        id="correction_1",
        finding_id=finding().id,
        subject_id="region_arkaim",
        superseded_claim_ids=["claim_old"],
        evidence_ids=["evidence_1"],
        temporal_reference_ids=["temporal_old"],
        affected_reasoning_ids=["reasoning_1"],
        reason="new book evidence changes the interpretation",
        created_at="2026-10-01T00:00:00Z",
    )


def test_pending_correction_has_no_replacement(tmp_path):
    repository = CorrectionRepository(tmp_path)
    pending = repository.add(correction())
    assert pending.status is CorrectionStatus.PENDING
    assert pending.replacement_claim_id is None
    assert pending.decision_by is None


def test_pending_correction_cannot_claim_replacement():
    with pytest.raises(ValidationError):
        CorrectionRecord(
            id="correction_1",
            finding_id="finding_1",
            subject_id="region_arkaim",
            replacement_claim_id="claim_new",
        )


def test_confirmation_requires_owner_replacement_and_timestamp(tmp_path):
    repository = CorrectionRepository(tmp_path)
    repository.add(correction())
    confirmed = repository.confirm(
        "correction_1",
        replacement_claim_id="claim_new",
        decision_by="owner",
        decided_at="2026-10-02T00:00:00Z",
    )
    assert confirmed.status is CorrectionStatus.CONFIRMED
    assert confirmed.replacement_claim_id == "claim_new"
    assert confirmed.superseded_claim_ids == ["claim_old"]
    assert confirmed.finding_id == "finding_1"
    assert confirmed.decision_by == "owner"


def test_confirmed_correction_marks_affected_reasoning_stale(tmp_path):
    repository = CorrectionRepository(tmp_path)
    repository.add(correction())
    repository.confirm(
        "correction_1",
        replacement_claim_id="claim_new",
        decision_by="owner",
        decided_at="2026-10-02T00:00:00Z",
    )
    assert repository.stale_reasoning_ids(subject_id="region_arkaim") == {"reasoning_1"}


def test_rejection_preserves_finding_without_replacement(tmp_path):
    repository = CorrectionRepository(tmp_path)
    repository.add(correction())
    rejected = repository.reject(
        "correction_1",
        reason="finding does not alter interpretation",
        decision_by="owner",
        decided_at="2026-10-02T00:00:00Z",
    )
    assert rejected.status is CorrectionStatus.REJECTED
    assert rejected.finding_id == "finding_1"
    assert rejected.superseded_claim_ids == ["claim_old"]
    assert rejected.replacement_claim_id is None
    assert rejected.reason == "finding does not alter interpretation"


def test_non_pending_correction_cannot_be_decided_twice(tmp_path):
    repository = CorrectionRepository(tmp_path)
    repository.add(correction())
    repository.confirm(
        "correction_1",
        replacement_claim_id="claim_new",
        decision_by="owner",
        decided_at="2026-10-02T00:00:00Z",
    )
    with pytest.raises(ValueError):
        repository.reject(
            "correction_1",
            reason="second decision",
            decision_by="owner",
            decided_at="2026-10-03T00:00:00Z",
        )


def test_correction_round_trip(tmp_path):
    repository = CorrectionRepository(tmp_path)
    repository.add(correction())
    loaded = repository.get("correction_1")
    assert loaded is not None
    assert loaded.evidence_ids == ["evidence_1"]
    assert loaded.temporal_reference_ids == ["temporal_old"]