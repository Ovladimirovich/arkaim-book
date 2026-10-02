"""M7 — temporal provenance correction lineage.

A correction is a proposal plus an auditable decision. It never mutates
WorldModel/Temporal state directly: the existing M10 confirmation manager remains
the sole canonical mutation boundary.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CorrectionStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class CorrectionRecord(BaseModel):
    """Lineage record for one temporal interpretation correction."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    finding_id: str = Field(min_length=1)
    status: CorrectionStatus = CorrectionStatus.PENDING
    subject_id: str = Field(min_length=1)
    superseded_claim_ids: list[str] = Field(default_factory=list)
    replacement_claim_id: Optional[str] = None
    evidence_ids: list[str] = Field(default_factory=list)
    temporal_reference_ids: list[str] = Field(default_factory=list)
    affected_reasoning_ids: list[str] = Field(default_factory=list)
    reason: str = ""
    decision_by: Optional[str] = None
    created_at: str = ""
    decided_at: Optional[str] = None

    @model_validator(mode="after")
    def validate_correction(self) -> "CorrectionRecord":
        if self.status is CorrectionStatus.PENDING:
            if self.replacement_claim_id:
                raise ValueError("pending correction cannot claim replacement claim")
        elif self.status is CorrectionStatus.CONFIRMED:
            if not self.replacement_claim_id or not self.decision_by or not self.decided_at:
                raise ValueError("confirmed correction requires replacement, decision owner and timestamp")
        elif self.status is CorrectionStatus.REJECTED:
            if not self.reason or not self.decision_by or not self.decided_at:
                raise ValueError("rejected correction requires reason, decision owner and timestamp")
        return self


__all__ = ["CorrectionStatus", "CorrectionRecord"]