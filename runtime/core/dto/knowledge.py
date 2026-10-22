"""M8 — read-only DTOs for Knowledge trace/query API."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# ── Bootstrap CORE/ в sys.path (нужны типизированные схемы резолверов) ──
_CORE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "core" / "CORE"
if _CORE_DIR.exists() and str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))

from schemas.temporal_reference import TemporalReference
from schemas.world_reference import WorldEntityReference

TraceabilityStatusLiteral = Literal["COMPLETE", "PARTIAL", "UNKNOWN"]


class TraceabilityStatus(str):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"


class KnowledgeTraceResponse(BaseModel):
    entity_id: str
    status: TraceabilityStatusLiteral = "UNKNOWN"
    claims: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    world: dict[str, Any] = Field(default_factory=dict)
    world_reference: WorldEntityReference | None = None
    temporal: list[dict[str, Any]] = Field(default_factory=list)
    temporal_reference: TemporalReference | None = None
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    conflict_notes: list[dict[str, Any]] = Field(default_factory=list)
    reasoning: list[dict[str, Any]] = Field(default_factory=list)
    corrections: list[dict[str, Any]] = Field(default_factory=list)
    lineage: list[dict[str, Any]] = Field(default_factory=list)
    uncertainty: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=100)
    totals: dict[str, int] = Field(default_factory=dict)
    next_offset: int | None = None

    @field_validator("world_reference", "temporal_reference", mode="before")
    @classmethod
    def _empty_reference_is_absent(cls, value: object) -> object:
        """Пустой dict означает «ссылки нет» — приводим к None.

        Сохраняет обратную совместимость с прежним DTO, где оба поля были
        ``dict[str, Any]`` с default_factory=dict: вызывающий код, который
        отдаёт ``{}``, не должен получать ошибку валидации.
        """
        if isinstance(value, dict) and not value:
            return None
        return value


__all__ = [
    "TraceabilityStatus",
    "TraceabilityStatusLiteral",
    "KnowledgeTraceResponse",
]
