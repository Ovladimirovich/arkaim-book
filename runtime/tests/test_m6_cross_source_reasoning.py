"""M6 — typed cross-source reasoning tests."""

from __future__ import annotations

import sys
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

import pytest

from evidence.repository import EvidenceRepository
from knowledge.reasoning import DeterministicReasoner
from narrative_engine.source_levels import ProvenanceCategory
from schemas.evidence import Evidence
from schemas.reasoning import ReasoningInput, ReasoningStatus


def inputs() -> list[ReasoningInput]:
    return [
        ReasoningInput(claim_id="claim_book", evidence_ids=["evidence_book"]),
        ReasoningInput(claim_id="claim_external", evidence_ids=["evidence_external"]),
    ]


def test_two_source_reasoning_is_derived_and_reproducible():
    result = DeterministicReasoner().aggregate(
        output_claim_id="derived_1",
        output_text="The sources converge on a cautious interpretation.",
        inputs=inputs(),
        confidence=0.72,
        uncertainty_reasons=["independent source coverage is incomplete"],
    )
    assert result.status is ReasoningStatus.RESOLVED
    assert result.category is ProvenanceCategory.DERIVED
    assert result.input_claim_ids == ["claim_book", "claim_external"]
    assert result.input_evidence_ids == ["evidence_book", "evidence_external"]
    assert result.method_id == "deterministic.source_aggregation"
    assert result.method_version == "1.0"
    assert result.uncertainty_reasons


def test_same_inputs_produce_same_reasoning_id_and_order():
    reasoner = DeterministicReasoner()
    first = reasoner.aggregate(
        output_claim_id="derived_1",
        output_text="Same output",
        inputs=inputs(),
        confidence=0.7,
        uncertainty_reasons=["scope limitation"],
    )
    second = reasoner.aggregate(
        output_claim_id="derived_1",
        output_text="Same output",
        inputs=inputs(),
        confidence=0.7,
        uncertainty_reasons=["scope limitation"],
    )
    assert first.id == second.id
    assert first.input_claim_ids == second.input_claim_ids


def test_single_source_is_not_cross_source_reasoning():
    with pytest.raises(ValueError):
        DeterministicReasoner().aggregate(
            output_claim_id="derived_1",
            output_text="Invalid",
            inputs=inputs()[:1],
            confidence=0.7,
            uncertainty_reasons=["missing input"],
        )


def test_missing_evidence_is_rejected(tmp_path):
    evidence_repo = EvidenceRepository(tmp_path)
    reasoner = DeterministicReasoner(evidence_repo)
    with pytest.raises(ValueError):
        reasoner.aggregate(
            output_claim_id="derived_1",
            output_text="Invalid",
            inputs=inputs(),
            confidence=0.7,
            uncertainty_reasons=["missing evidence"],
        )
    evidence_repo.add(Evidence.from_locator(source_id="book", source_type="book", locator="book:chunk:1", text="book"))
    with pytest.raises(ValueError):
        reasoner.aggregate(
            output_claim_id="derived_1",
            output_text="Invalid",
            inputs=inputs(),
            confidence=0.7,
            uncertainty_reasons=["missing evidence"],
        )


def test_resolved_reasoning_requires_uncertainty_reasons():
    with pytest.raises(ValueError):
        DeterministicReasoner().aggregate(
            output_claim_id="derived_1",
            output_text="Invalid",
            inputs=inputs(),
            confidence=0.7,
            uncertainty_reasons=[],
        )


def test_hypothesis_reasoning_keeps_hypothesis_category():
    from schemas.reasoning import ReasoningResult

    result = ReasoningResult(
        id="reasoning_hypothesis",
        status=ReasoningStatus.HYPOTHESIS,
        output_claim_id="hypothesis_1",
        output_text="Possible interpretation",
        category=ProvenanceCategory.HYPOTHESIS,
        input_claims=inputs(),
        method_id="llm.candidate",
        method_version="0.1",
        confidence=0.3,
        uncertainty_reasons=["speculative"],
    )
    assert result.category is ProvenanceCategory.HYPOTHESIS