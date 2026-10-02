"""M4 — typed references from Knowledge claims to existing Temporal data.

This contract attaches a Knowledge claim to an existing temporal node/event/era
without changing the Temporal graph. It keeps source time, assertion time and
world time separate, preserves temporal precision/provenance, and never fills an
unknown time with the present anchor.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from narrative_engine.temporal.precision import TemporalPrecision


class TemporalReferenceStatus(str, Enum):
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"
    UNKNOWN = "UNKNOWN"


class TemporalTimeBasis(str, Enum):
    """What kind of time a reference asserts; values are not interchangeable."""

    WORLD = "WORLD_TIME"
    SOURCE_PUBLICATION = "SOURCE_PUBLICATION"
    INGESTION = "INGESTION"
    ASSERTION = "ASSERTION"


class TemporalReference(BaseModel):
    """A non-mutating Knowledge -> Temporal reference."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(min_length=1)
    time_basis: TemporalTimeBasis
    status: TemporalReferenceStatus
    temporal_node_id: Optional[str] = None
    event_id: Optional[str] = None
    era_id: Optional[str] = None
    precision: TemporalPrecision = TemporalPrecision.UNKNOWN
    bounds: Optional[dict] = None
    temporal_provenance: Optional[list[dict]] = None
    reason: str = ""
    resolution_method: str = ""

    @model_validator(mode="after")
    def validate_reference(self) -> "TemporalReference":
        if self.status is TemporalReferenceStatus.RESOLVED:
            if not any((self.temporal_node_id, self.event_id, self.era_id)):
                raise ValueError("resolved Temporal reference requires node, event, or era ID")
        elif any((self.temporal_node_id, self.event_id, self.era_id)):
            raise ValueError("non-resolved Temporal reference must not claim a temporal ID")
        if self.status is TemporalReferenceStatus.UNKNOWN and self.precision is not TemporalPrecision.UNKNOWN:
            raise ValueError("UNKNOWN Temporal reference must use UNKNOWN precision")
        if self.time_basis is not TemporalTimeBasis.WORLD and any(
            (self.temporal_node_id, self.event_id, self.era_id, self.bounds)
        ):
            raise ValueError("only WORLD_TIME may carry canonical temporal position")
        return self

    @property
    def is_resolved(self) -> bool:
        return self.status is TemporalReferenceStatus.RESOLVED


__all__ = ["TemporalReferenceStatus", "TemporalTimeBasis", "TemporalReference"]