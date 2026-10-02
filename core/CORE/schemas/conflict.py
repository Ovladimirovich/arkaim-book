"""M5 — typed competing claims and conflict records.

This model preserves competing claims as data. It does not select a true source,
delete a claim, or modify WorldModel/Temporal state. Existing Book OS
``Conflict`` objects are ingestion diagnostics and are adapted explicitly.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConflictType(str, Enum):
    DIRECT_CONTRADICTION = "DIRECT_CONTRADICTION"
    TEMPORAL_INCOMPATIBILITY = "TEMPORAL_INCOMPATIBILITY"
    INCOMPATIBLE_INTERPRETATION = "INCOMPATIBLE_INTERPRETATION"
    SOURCE_PERSPECTIVE = "SOURCE_PERSPECTIVE"
    NARRATIVE_CONSISTENCY = "NARRATIVE_CONSISTENCY"


class ConflictStatus(str, Enum):
    UNRESOLVED = "UNRESOLVED"
    ACCEPTED_AS_PERSPECTIVES = "ACCEPTED_AS_PERSPECTIVES"
    RESOLVED_WITH_EVIDENCE = "RESOLVED_WITH_EVIDENCE"
    REJECTED = "REJECTED"


class ConflictRecord(BaseModel):
    """A durable record linking competing claims without rewriting them."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    conflict_type: ConflictType
    status: ConflictStatus = ConflictStatus.UNRESOLVED
    subject_id: str = Field(min_length=1)
    claim_ids: list[str] = Field(min_length=2)
    evidence_ids: list[str] = Field(default_factory=list)
    world_entity_ids: list[str] = Field(default_factory=list)
    temporal_reference_ids: list[str] = Field(default_factory=list)
    explanation: str = ""
    severity: Optional[str] = None
    resolution_claim_id: Optional[str] = None
    resolution_reason: str = ""
    created_at: str = ""
    resolved_at: Optional[str] = None

    @model_validator(mode="after")
    def validate_resolution(self) -> "ConflictRecord":
        if len(set(self.claim_ids)) < 2:
            raise ValueError("conflict requires at least two distinct claim IDs")
        if self.status is ConflictStatus.RESOLVED_WITH_EVIDENCE:
            if not self.resolution_claim_id or not self.resolution_reason:
                raise ValueError("resolved conflict requires resolution claim and reason")
        if self.status is not ConflictStatus.RESOLVED_WITH_EVIDENCE and self.resolution_claim_id:
            raise ValueError("non-resolved conflict cannot claim a resolution")
        return self


__all__ = ["ConflictType", "ConflictStatus", "ConflictRecord"]