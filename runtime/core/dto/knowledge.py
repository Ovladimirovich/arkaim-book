"""M8 — read-only DTOs for Knowledge trace/query API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TraceabilityStatus(str):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"


class KnowledgeTraceResponse(BaseModel):
    entity_id: str
    status: str
    claims: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    world: dict[str, Any] = Field(default_factory=dict)
    temporal: list[dict[str, Any]] = Field(default_factory=list)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    reasoning: list[dict[str, Any]] = Field(default_factory=list)
    corrections: list[dict[str, Any]] = Field(default_factory=list)
    lineage: list[dict[str, Any]] = Field(default_factory=list)
    uncertainty: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=100)
    totals: dict[str, int] = Field(default_factory=dict)
    next_offset: int | None = None


__all__ = ["TraceabilityStatus", "KnowledgeTraceResponse"]
