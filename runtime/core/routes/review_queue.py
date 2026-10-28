"""API очереди проверки кандидатов LLM (Q3).

Обёртка над движком Q1/Q2 (``knowledge_expansion.review``), второго механизма
здесь нет — решения принимает только ``decide``.

Правила (решение владельца):
  * смотреть список/статистику может любой аутентифицированный пользователь;
  * принимать решение — только ``admin`` (роль-«автор» в рантайме представлена
    владельцем-администратором; сам движок по-прежнему допускает и ``author``);
  * комментарий при APPROVE обязателен; массовых операций и перегенерации нет;
  * ``APPROVED`` не превращает запись в канон: ``provenance_category``
    (``SYSTEM_INTERPRETATION``) не меняется.

Ответы — конвенция проекта: ``{"ok": true, "data": ...}``; ошибки —
``{"ok": false, "error": {"code": ..., "message": ...}}``.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from auth.rbac import require_role

from knowledge_expansion.review import (
    STATUS_APPROVED,
    CandidateNotFound,
    InvalidTransition,
    PermissionDenied,
    StaleCandidate,
    ValidationError,
    candidate_stats,
    decide,
    filter_candidates,
    scan_candidates,
)

router = APIRouter(prefix="/api/candidates", tags=["Candidate Review Queue"])


def _candidate_payload(record: Any) -> dict[str, Any]:
    """Публичное представление кандидата (то, что видит экран)."""
    return {
        "candidate_id": record.candidate_id,
        "topic": record.topic,
        "status": record.status,
        "file": record.file,
        "locator": record.locator,
        "preview": record.preview,
        "source": record.source,
        "model": record.model,
        "generated_at": record.generated_at,
        "reviewed_by": record.reviewed_by,
        "reviewed_at": record.reviewed_at,
        "review_comment": record.review_comment,
        "file_blocked": record.file_blocked,
        "requires_author_review": record.status != STATUS_APPROVED,
        # provisional_category в зеркале очереди — константа: кандидат — это
        # системная интерпретация; APPROVED не делает его каноном.
        "provenance_category": "SYSTEM_INTERPRETATION",
    }


@router.get("", dependencies=[Depends(require_role("reader"))])
async def list_candidates(
    status: str | None = Query(None, description="Фильтр по статусу"),
    file: str | None = Query(None, description="Фильтр по файлу-источнику"),
    source: str | None = Query(None, description="Фильтр по источнику"),
    q: str | None = Query(None, description="Поиск по теме/фрагменту"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """Список кандидатов (фильтры и постраничность)."""
    records = scan_candidates()
    selected = filter_candidates(
        records,
        status=status,
        file=file,
        source=source,
        query=q,
        limit=None,
        offset=0,
    )
    total = len(selected)
    page = selected[offset : offset + limit] if limit else selected[offset:]
    payloads = [_candidate_payload(r) for r in page]

    return {"ok": True, "data": payloads, "total": total, "limit": limit, "offset": offset}


@router.get("/stats", dependencies=[Depends(require_role("reader"))])
async def candidates_stats() -> dict[str, Any]:
    """Сводная статистика очереди (для бейджа)."""
    records = scan_candidates()
    return {"ok": True, "data": candidate_stats(records)}


def _decision(action: str, candidate_id: str, user: dict, body: dict[str, Any] | None):
    """Единственная точка решений — движок Q2 (никакого второго механизма)."""
    payload = body if isinstance(body, dict) else {}
    comment = str(payload.get("comment", ""))
    expected_status = payload.get("expected_status")
    actor = str(user.get("display_name") or user.get("username") or user.get("user_id") or "")
    role = str(user.get("role") or "")
    try:
        updated = decide(
            candidate_id,
            action,
            actor=actor,
            role=role,
            comment=comment,
            expected_status=expected_status,
        )
    except PermissionDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (CandidateNotFound, InvalidTransition, StaleCandidate, ValidationError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"ok": True, "data": _candidate_payload(updated)}


@router.post(
    "/{candidate_id}/approve",
    summary="Одобрить кандидата (только admin; комментарий обязателен)",
    dependencies=[Depends(require_role("admin"))],
)
async def approve_candidate(
    candidate_id: str,
    body: dict[str, Any] | None = None,
    user: dict = Depends(require_role("admin")),
) -> dict[str, Any]:
    return _decision("approve", candidate_id, user, body)


@router.post(
    "/{candidate_id}/reject",
    summary="Отклонить кандидата (REJECTED остаётся в файле)",
    dependencies=[Depends(require_role("admin"))],
)
async def reject_candidate(
    candidate_id: str,
    body: dict[str, Any] | None = None,
    user: dict = Depends(require_role("admin")),
) -> dict[str, Any]:
    return _decision("reject", candidate_id, user, body)


@router.post(
    "/{candidate_id}/reopen",
    summary="Вернуть отклонённого кандидата в проверку",
    dependencies=[Depends(require_role("admin"))],
)
async def reopen_candidate(
    candidate_id: str,
    body: dict[str, Any] | None = None,
    user: dict = Depends(require_role("admin")),
) -> dict[str, Any]:
    return _decision("reopen", candidate_id, user, body)
