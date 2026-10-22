"""M7 — Public API for Knowledge correction proposals.

Предложения исправления (correction proposals) приходят из находок M10.
Каждое предложение создаётся в статусе PENDING: решение принимает человек.
Мутация WorldModel остаётся исключительно за менеджером подтверждения M10 —
этот модуль WorldModel не трогает.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from auth.rbac import require_role
from knowledge.correction_repository import CorrectionRepository
from schemas.correction import CorrectionRecord, CorrectionStatus

router = APIRouter(prefix="/knowledge/corrections", tags=["Corrections"])


def get_correction_repository() -> CorrectionRepository:
    """Factory for the existing CorrectionRepository (no new decision logic)."""
    from config import config

    return CorrectionRepository(data_dir=config.knowledge_repo_dir("KNOWLEDGE_CORRECTION_DIR"))


@router.get(
    "",
    summary="Список предложений исправления",
    response_model=list[CorrectionRecord],
)
async def list_corrections(
    status: Optional[str] = Query(None, max_length=32),
    subject_id: Optional[str] = Query(None, max_length=200),
    repo: CorrectionRepository = Depends(get_correction_repository),
    _: None = Depends(require_role("reader")),
) -> list[CorrectionRecord]:
    """Все предложения исправления (по статусу и по сущности)."""
    return repo.list(status=status, subject_id=subject_id)


@router.get(
    "/{correction_id}",
    summary="Получить предложение исправления",
    response_model=CorrectionRecord,
)
async def get_correction(
    correction_id: str,
    repo: CorrectionRepository = Depends(get_correction_repository),
    _: None = Depends(require_role("reader")),
) -> CorrectionRecord:
    """Одно предложение исправления по идентификатору."""
    record = repo.get(correction_id)
    if record is None:
        raise HTTPException(404, f"Correction '{correction_id}' not found")
    return record


@router.post(
    "/{correction_id}/confirm",
    summary="Подтвердить предложение исправления",
    response_model=CorrectionRecord,
)
async def confirm_correction(
    correction_id: str,
    replacement_claim_id: str = Body(..., min_length=1),
    decision_by: str = Body(..., min_length=1),
    decided_at: str = Body(..., min_length=1),
    affected_reasoning_ids: Optional[list[str]] = Body(None),
    repo: CorrectionRepository = Depends(get_correction_repository),
    _: None = Depends(require_role("editor", "admin")),
) -> CorrectionRecord:
    """Подтвердить предложение: обязательна ссылка на заменяющую претензию.

    WorldModel при этом не меняется — это по-прежнему делает только M10.
    """
    try:
        return repo.confirm(
            correction_id,
            replacement_claim_id=replacement_claim_id,
            decision_by=decision_by,
            decided_at=decided_at,
            affected_reasoning_ids=affected_reasoning_ids,
        )
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post(
    "/{correction_id}/reject",
    summary="Отклонить предложение исправления",
    response_model=CorrectionRecord,
)
async def reject_correction(
    correction_id: str,
    reason: str = Body(..., min_length=1),
    decision_by: str = Body(..., min_length=1),
    decided_at: str = Body(..., min_length=1),
    repo: CorrectionRepository = Depends(get_correction_repository),
    _: None = Depends(require_role("editor", "admin")),
) -> CorrectionRecord:
    """Отклонить предложение с указанием причины."""
    try:
        return repo.reject(
            correction_id,
            reason=reason,
            decision_by=decision_by,
            decided_at=decided_at,
        )
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


__all__ = ["router", "get_correction_repository", "CorrectionStatus"]
