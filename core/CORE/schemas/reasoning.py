"""M6 — typed cross-source reasoning results.

The contract makes derived knowledge reproducible: exact input claim/evidence IDs,
ordered method/version, output category, confidence and uncertainty are mandatory.
It does not turn generated text into canon or replace the existing
ProvenanceTracker/hypothesis systems.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from narrative_engine.source_levels import ProvenanceCategory


class ReasoningStatus(str, Enum):
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"
    HYPOTHESIS = "HYPOTHESIS"


class ReasoningInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)


class ReasoningResult(BaseModel):
    """A derived/system-interpretation result with complete input lineage."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    status: ReasoningStatus
    output_claim_id: str = Field(min_length=1)
    output_text: str = Field(min_length=1)
    category: ProvenanceCategory
    input_claims: list[ReasoningInput] = Field(min_length=2)
    method_id: str = Field(min_length=1)
    method_version: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    uncertainty_reasons: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""

    @model_validator(mode="after")
    def validate_reasoning(self) -> "ReasoningResult":
        if self.status is ReasoningStatus.RESOLVED and self.category not in {
            ProvenanceCategory.DERIVED,
            ProvenanceCategory.RECONSTRUCTION,
        }:
            raise ValueError("resolved reasoning must be DERIVED or RECONSTRUCTION")
        if self.status is ReasoningStatus.HYPOTHESIS and self.category is not ProvenanceCategory.HYPOTHESIS:
            raise ValueError("hypothesis reasoning must retain HYPOTHESIS category")
        if self.status is ReasoningStatus.RESOLVED and not self.uncertainty_reasons:
            raise ValueError("resolved reasoning must expose uncertainty reasons")
        if len({item.claim_id for item in self.input_claims}) < 2:
            raise ValueError("cross-source reasoning requires at least two distinct input claims")
        return self

    @property
    def input_claim_ids(self) -> list[str]:
        return [item.claim_id for item in self.input_claims]

    @property
    def input_evidence_ids(self) -> list[str]:
        return [evidence_id for item in self.input_claims for evidence_id in item.evidence_ids]


__all__ = ["ReasoningStatus", "ReasoningInput", "ReasoningResult"]