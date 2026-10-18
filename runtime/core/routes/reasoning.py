"""M6 — Public API for deterministic cross-source reasoning.

Endpoints create, retrieve and list deterministic reasoning results through
the existing DeterministicReasoner and ReasoningRepository. Reasoning results
are derived (DERIVED / RECONSTRUCTION / HYPOTHESIS) and never become canon.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from auth.rbac import require_role
from knowledge.reasoning import DeterministicReasoner
from knowledge.reasoning_repository import ReasoningRepository
from narrative_engine.source_levels import ProvenanceCategory
from schemas.reasoning import ReasoningInput, ReasoningResult, ReasoningStatus

router = APIRouter(prefix="/knowledge/reasoning", tags=["Reasoning"])


def _default_data_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "reasoning"


def get_reasoning_repository() -> ReasoningRepository:
    """Factory for the existing ReasoningRepository (no new inference logic)."""
    return ReasoningRepository(data_dir=_default_data_dir())


def get_reasoner() -> DeterministicReasoner:
    """Factory for the existing DeterministicReasoner (no new aggregation logic)."""
    return DeterministicReasoner()


@router.post(
    "",
    summary="Создать детерминированный производный вывод",
    response_model=ReasoningResult,
)
async def create_reasoning(
    output_claim_id: str = Body(..., min_length=1),
    output_text: str = Body(..., min_length=1),
    inputs: list[ReasoningInput] = Body(..., min_length=2),
    confidence: float = Body(..., ge=0.0, le=1.0),
    uncertainty_reasons: list[str] = Body(default_factory=list),
    category: ProvenanceCategory = Body(ProvenanceCategory.DERIVED),
    metadata: dict[str, Any] | None = None,
    reasoner: DeterministicReasoner = Depends(get_reasoner),
    _: None = Depends(require_role("reader")),
) -> ReasoningResult:
    """Создать детерминированный производный вывод из нескольких претензий.

    Требует минимум двух различных claim_id. Результат получает категорию
    DERIVED/RECONSTRUCTION/HYPOTHESIS и никогда не становится каноном.
    """
    try:
        return reasoner.aggregate(
            output_claim_id=output_claim_id,
            output_text=output_text,
            inputs=inputs,
            confidence=confidence,
            uncertainty_reasons=uncertainty_reasons,
            category=category,
            metadata=metadata or {},
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get(
    "/{reasoning_id}",
    summary="Получить производный вывод",
    response_model=ReasoningResult,
)
async def get_reasoning(
    reasoning_id: str,
    repo: ReasoningRepository = Depends(get_reasoning_repository),
    _: None = Depends(require_role("reader")),
) -> ReasoningResult:
    """Получить запись производного вывода по идентификатору."""
    result = repo.get(reasoning_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"reasoning not found: {reasoning_id}")
    return result


@router.get(
    "",
    summary="Список производных выводов с фильтрами",
    response_model=list[ReasoningResult],
)
async def list_reasoning(
    subject_id: Optional[str] = Query(default=None),
    status: Optional[ReasoningStatus] = Query(default=None),
    repo: ReasoningRepository = Depends(get_reasoning_repository),
    _: None = Depends(require_role("reader")),
) -> list[ReasoningResult]:
    """Список производных выводов с опциональными фильтрами по субъекту и статусу."""
    return repo.list(subject_id=subject_id, status=status.value if status else None)
