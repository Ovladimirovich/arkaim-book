"""M6 — typed cross-source reasoning tests."""

from __future__ import annotations

import sys
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

import pytest
from fastapi import HTTPException

from evidence.repository import EvidenceRepository
from knowledge.reasoning import DeterministicReasoner
from knowledge.reasoning_repository import ReasoningRepository
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


# ── API endpoint tests (M6) ─────────────────────────────────────────────────


class TestReasoningAPI:
    """Endpoint tests for POST/GET /knowledge/reasoning and list.

    Calls endpoint functions directly with a fake reasoner/repository;
    no HTTP stack or authentication infrastructure is needed.
    """

    @pytest.fixture
    def tmp_repo(self, tmp_path):
        return ReasoningRepository(data_dir=tmp_path)

    @pytest.fixture
    def reasoner(self):
        return DeterministicReasoner()

    def _input_list(self) -> list[ReasoningInput]:
        return [
            ReasoningInput(claim_id="claim_book", evidence_ids=["evidence_book"]),
            ReasoningInput(claim_id="claim_external", evidence_ids=["evidence_external"]),
        ]

    def _call_create(self, repo: ReasoningRepository, reasoner: DeterministicReasoner):
        from core.routes.reasoning import create_reasoning

        return create_reasoning(
            output_claim_id="derived_1",
            output_text="The sources converge on a cautious interpretation.",
            inputs=self._input_list(),
            confidence=0.72,
            uncertainty_reasons=["independent source coverage is incomplete"],
            category=ProvenanceCategory.DERIVED,
            reasoner=reasoner,
        )

    async def test_endpoint_create_reasoning_derived(self, tmp_repo: ReasoningRepository, reasoner: DeterministicReasoner) -> None:
        result = await self._call_create(tmp_repo, reasoner)
        assert result.status is ReasoningStatus.RESOLVED
        assert result.category is ProvenanceCategory.DERIVED
        assert result.method_id == "deterministic.source_aggregation"
        assert result.method_version == "1.0"
        assert result.input_claim_ids == ["claim_book", "claim_external"]
        assert result.input_evidence_ids == ["evidence_book", "evidence_external"]
        assert result.uncertainty_reasons == ["independent source coverage is incomplete"]

    async def test_endpoint_get_reasoning(self, tmp_repo: ReasoningRepository, reasoner: DeterministicReasoner) -> None:
        result = await self._call_create(tmp_repo, reasoner)
        repo = tmp_repo
        repo.add(result)
        from core.routes.reasoning import get_reasoning

        loaded = await get_reasoning(reasoning_id=result.id, repo=repo)
        assert loaded is not None
        assert loaded.id == result.id
        assert loaded.output_claim_id == "derived_1"

    def test_endpoint_get_missing_reasoning_raises(self, tmp_repo: ReasoningRepository) -> None:
        import asyncio
        from fastapi import HTTPException

        from core.routes.reasoning import get_reasoning

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_reasoning(reasoning_id="no_such_reasoning", repo=tmp_repo))
        assert exc_info.value.status_code == 404

    def test_endpoint_list_reasoning(self, tmp_repo: ReasoningRepository, reasoner: DeterministicReasoner) -> None:
        import asyncio

        from core.routes.reasoning import create_reasoning, list_reasoning

        first = asyncio.run(
            create_reasoning(
                output_claim_id="derived_1",
                output_text="First derivation.",
                inputs=self._input_list(),
                confidence=0.72,
                uncertainty_reasons=["scope limitation"],
                category=ProvenanceCategory.DERIVED,
                reasoner=reasoner,
            )
        )
        second = asyncio.run(
            create_reasoning(
                output_claim_id="derived_2",
                output_text="Second derivation.",
                inputs=self._input_list(),
                confidence=0.6,
                uncertainty_reasons=["partial coverage"],
                category=ProvenanceCategory.HYPOTHESIS,
                reasoner=reasoner,
            )
        )
        tmp_repo.add(first)
        tmp_repo.add(second)
        all_results = tmp_repo.list()
        assert len(all_results) == 2
        resolved = tmp_repo.list(status="RESOLVED")
        assert len(resolved) == 1
        hypothesis = tmp_repo.list(status="HYPOTHESIS")
        assert len(hypothesis) == 1

    def test_endpoint_create_single_source_rejected(self, reasoner: DeterministicReasoner) -> None:
        import asyncio

        from core.routes.reasoning import create_reasoning

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                create_reasoning(
                    output_claim_id="derived_1",
                    output_text="Invalid.",
                    inputs=self._input_list()[:1],
                    confidence=0.7,
                    uncertainty_reasons=["missing input"],
                    reasoner=reasoner,
                )
            )
        assert exc_info.value.status_code == 400

    def test_endpoint_create_empty_uncertainty_rejected(self, reasoner: DeterministicReasoner) -> None:
        import asyncio

        from core.routes.reasoning import create_reasoning

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                create_reasoning(
                    output_claim_id="derived_1",
                    output_text="Invalid.",
                    inputs=self._input_list(),
                    confidence=0.7,
                    uncertainty_reasons=[],
                    reasoner=reasoner,
                )
            )
        assert exc_info.value.status_code == 400

