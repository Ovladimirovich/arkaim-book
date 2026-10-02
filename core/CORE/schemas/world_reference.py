"""M3 — typed references between Knowledge claims and canonical World data.

This module is deliberately a boundary contract, not a second identity system.
Knowledge may reference an existing World Engine entity by its canonical ID and
may report unresolved or unapproved identity explicitly. It never creates or
normalizes a new canonical ID, never expands the approved crosswalk, and never
copies World provenance onto a Knowledge claim.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class WorldReferenceStatus(str, Enum):
    """Status of a Knowledge -> World identity reference."""

    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    CROSSWALK_UNAPPROVED = "CROSSWALK_UNAPPROVED"


class WorldEntityReference(BaseModel):
    """A Knowledge-side reference to an existing canonical World entity.

    ``query`` is preserved for auditability. ``canonical_id`` is populated only
    after an actual World Engine lookup succeeds. ``world_provenance`` is kept
    separate from Knowledge claim provenance by construction.
    """

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    canonical_id: Optional[str] = None
    name: Optional[str] = None
    status: WorldReferenceStatus
    reason: str = ""
    resolution_method: str = ""
    world_provenance: Optional[dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_reference(self) -> "WorldEntityReference":
        if self.status is WorldReferenceStatus.RESOLVED and not self.canonical_id:
            raise ValueError("RESOLVED World reference requires canonical_id")
        if self.status is not WorldReferenceStatus.RESOLVED and self.canonical_id:
            raise ValueError("non-RESOLVED World reference must not claim canonical_id")
        return self

    @property
    def resolved(self) -> bool:
        return self.status is WorldReferenceStatus.RESOLVED


class WorldRelationReference(BaseModel):
    """A relation as seen by Knowledge, without inheriting claim provenance."""

    model_config = ConfigDict(extra="forbid")

    relation_id: str = Field(min_length=1)
    source_entity_id: str = Field(min_length=1)
    target_entity_id: str = Field(min_length=1)
    relation_type: str = Field(min_length=1)
    world_relation: bool = True
    relation_provenance: Optional[dict[str, Any]] = None
    knowledge_provenance: Optional[dict[str, Any]] = None
    notes: str = ""

    @model_validator(mode="after")
    def validate_provenance_boundary(self) -> "WorldRelationReference":
        if self.relation_provenance is None and self.knowledge_provenance is not None:
            raise ValueError("knowledge provenance cannot substitute for relation provenance")
        return self


__all__ = [
    "WorldReferenceStatus",
    "WorldEntityReference",
    "WorldRelationReference",
]