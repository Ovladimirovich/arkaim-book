"""M6 — deterministic cross-source reasoning service.

This is an intentionally small deterministic rule for creating a derived result.
It does not generate natural language by itself and cannot elevate source claims to
canon. LLM-assisted synthesis can later produce a typed candidate, but it must use
the same ReasoningResult contract and gates.
"""

from __future__ import annotations

from typing import Any, Protocol

from narrative_engine.source_levels import ProvenanceCategory
from schemas.reasoning import ReasoningInput, ReasoningResult, ReasoningStatus


class EvidenceLookup(Protocol):
    def get(self, evidence_id: str) -> Any | None: ...


class DeterministicReasoner:
    """Produce a reproducible derived result from explicit claim/evidence inputs."""

    METHOD_ID = "deterministic.source_aggregation"
    METHOD_VERSION = "1.0"

    def __init__(self, evidence_repository: EvidenceLookup | None = None):
        self.evidence_repository = evidence_repository

    def _evidence_exists(self, evidence_id: str) -> bool:
        if self.evidence_repository is None:
            return True
        try:
            return self.evidence_repository.get(evidence_id) is not None
        except Exception:
            finder = getattr(self.evidence_repository, "find", None)
            if callable(finder):
                try:
                    return finder(evidence_id) is not None
                except Exception:
                    return False
            return False

    def aggregate(
        self,
        *,
        output_claim_id: str,
        output_text: str,
        inputs: list[ReasoningInput],
        confidence: float,
        uncertainty_reasons: list[str],
        category: ProvenanceCategory = ProvenanceCategory.DERIVED,
        metadata: dict[str, Any] | None = None,
    ) -> ReasoningResult:
        if len(inputs) < 2:
            raise ValueError("cross-source reasoning requires at least two inputs")
        if len({item.claim_id for item in inputs}) < 2:
            raise ValueError("cross-source reasoning requires distinct source claims")
        if self.evidence_repository is not None:
            for item in inputs:
                for evidence_id in item.evidence_ids:
                    if not self._evidence_exists(evidence_id):
                        raise ValueError(f"evidence is unavailable: {evidence_id}")
        if not uncertainty_reasons:
            raise ValueError("reasoning must expose uncertainty reasons")
        return ReasoningResult(
            id=f"reasoning_{output_claim_id}",
            status=ReasoningStatus.RESOLVED,
            output_claim_id=output_claim_id,
            output_text=output_text,
            category=category,
            input_claims=inputs,
            method_id=self.METHOD_ID,
            method_version=self.METHOD_VERSION,
            confidence=confidence,
            uncertainty_reasons=uncertainty_reasons,
            metadata=metadata or {},
        )


__all__ = ["EvidenceLookup", "DeterministicReasoner"]