"""M5 — Public API for Knowledge conflict records.

Endpoints create, retrieve, list and resolve conflict records through the
existing ConflictRepository. Claims are never rewritten or deleted.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from auth.rbac import require_role
from knowledge.conflict_repository import ConflictRepository
from schemas.conflict import (
    ConflictRecord,
    ConflictStatus,
    ConflictType,
)

router = APIRouter(prefix="/knowledge/conflicts", tags=["Conflicts"])


def _default_data_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "runtime_data" / "knowledge"


def get_conflict_repository() -> ConflictRepository:
    """Factory for the existing ConflictRepository (no new resolution logic)."""
    return ConflictRepository(data_dir=_default_data_dir())


@router.post(
    "",
    summary="Создать запись конфликта претензий",
    response_model=ConflictRecord,
)
async def create_conflict(
    conflict_type: ConflictType = Body(..., embed=False),
    subject_id: str = Body(..., min_length=1),
    claim_ids: list[str] = Body(..., min_length=2),
    evidence_ids: list[str] = Body(default_factory=list),
    world_entity_ids: list[str] = Body(default_factory=list),
    temporal_reference_ids: list[str] = Body(default_factory=list),
    explanation: str = Body(default=""),
    severity: Optional[str] = Body(default=None),
    repo: ConflictRepository = Depends(get_conflict_repository),
    _: None = Depends(require_role("reader")),
) -> ConflictRecord:
    """Создать durable запись конфликта между претензиями.

    Претензии не удаляются и не перезаписываются; запись только фиксирует
    наличие противоречия в статусе UNRESOLVED.
    """
    from uuid import uuid4

    record = ConflictRecord(
        id=f"conflict_{uuid4().hex[:12]}",
        conflict_type=conflict_type,
        subject_id=subject_id,
        claim_ids=claim_ids,
        evidence_ids=evidence_ids,
        world_entity_ids=world_entity_ids,
        temporal_reference_ids=temporal_reference_ids,
        explanation=explanation,
        severity=severity,
        created_at=datetime.now(tz=timezone.utc).isoformat(),
    )
    return repo.add(record)


@router.get(
    "/{conflict_id}",
    summary="Получить запись конфликта",
    response_model=ConflictRecord,
)
async def get_conflict(
    conflict_id: str,
    repo: ConflictRepository = Depends(get_conflict_repository),
    _: None = Depends(require_role("reader")),
) -> ConflictRecord:
    """Получить запись конфликта по идентификатору."""
    record = repo.get(conflict_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"conflict not found: {conflict_id}")
    return record


@router.get(
    "",
    summary="Список конфликтов с фильтрами",
    response_model=list[ConflictRecord],
)
async def list_conflicts(
    subject_id: Optional[str] = Query(default=None),
    status: Optional[ConflictStatus] = Query(default=None),
    repo: ConflictRepository = Depends(get_conflict_repository),
    _: None = Depends(require_role("reader")),
) -> list[ConflictRecord]:
    """Список конфликтов с опциональными фильтрами по субъекту и статусу."""
    return repo.list(subject_id=subject_id, status=status.value if status else None)


@router.post(
    "/{conflict_id}/resolve",
    summary="Разрешить конфликт с доказательством",
    response_model=ConflictRecord,
)
async def resolve_conflict(
    conflict_id: str,
    resolution_claim_id: str = Body(..., min_length=1),
    resolution_reason: str = Body(default=""),
    resolved_at: str = Body(default=""),
    repo: ConflictRepository = Depends(get_conflict_repository),
    _: None = Depends(require_role("reader")),
) -> ConflictRecord:
    """Разрешить конфликт с явным претензией-победителем и причиной.

    Статус переходит в RESOLVED_WITH_EVIDENCE. Исходные претензии остаются
    в claim_ids; они не удаляются.
    """
    if not resolved_at:
        resolved_at = datetime.now(tz=timezone.utc).isoformat()
    try:
        return repo.resolve_with_evidence(
            conflict_id=conflict_id,
            resolution_claim_id=resolution_claim_id,
            resolution_reason=resolution_reason,
            resolved_at=resolved_at,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/{conflict_id}/perspectives",
    summary="Принять конфликт как параллельные перспективы",
    response_model=ConflictRecord,
)
async def accept_as_perspectives(
    conflict_id: str,
    repo: ConflictRepository = Depends(get_conflict_repository),
    _: None = Depends(require_role("reader")),
) -> ConflictRecord:
    """Пометить конфликт как ACCEPTED_AS_PERSPECTIVES без выбора победителя.

    Исходные претензии сохраняются; resolution_claim_id остаётся None.
    """
    try:
        return repo.accept_as_perspectives(conflict_id=conflict_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
