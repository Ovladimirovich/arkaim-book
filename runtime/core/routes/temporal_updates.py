"""Temporal Updates API — M10.2: pending-updates endpoints.

Тонкая HTTP-обёртка над существующим M10 TemporalUpdateManager.
НИКАКИХ изменений логики подтверждения: endpoint'ы только вызывают
методы менеджера (suggest-only инвариант M10 сохраняется).

RBAC (утверждено владельцем 2026-09-08):
  - reader  — только просмотр предложений;
  - editor  — просмотр + confirm + reject + scan;
  - admin   — просмотр + confirm + reject + scan.

Persistence: очередь in-memory (утверждено владельцем; после рестарта
процесса pending исчезают, подтверждённые — уже в WorldModel).

Endpoints (все под /book/temporal/pending-updates):
  POST /scan                       — editor+: детектор → извлечение → submit
  GET  /                           — reader+: список pending
  GET  /stats                      — reader+: счётчики
  GET  /history                    — reader+: подтверждённые + отклонённые
  GET  /{finding_id}               — reader+: детали находки
  POST /{finding_id}/confirm       — editor+: confirmation gate менеджера
  POST /{finding_id}/reject        — editor+: отклонение
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from auth.rbac import require_role

log = logging.getLogger("routes.temporal_updates")

router = APIRouter(prefix="/temporal/pending-updates", tags=["Temporal Updates (M10.2)"])

# Может менять WorldModel только через менеджер M10; держим singleton
_manager = None
_detector = None


# ── Singleton-доступ к M10-компонентам (паттерн get_world_engine) ──


def _get_manager():
    """Lazy singleton TemporalUpdateManager (создаётся при первом вызове)."""
    global _manager
    if _manager is None:
        from narrative_engine.world_model import WorldModel
        from narrative_engine.research.temporal_update_manager import TemporalUpdateManager
        from narrative_engine.world_engine import get_world_engine

        _manager = TemporalUpdateManager(
            world_model=WorldModel.load(),
            world_engine=get_world_engine(),
        )
        log.info("temporal_updates_manager_initialized")
    return _manager


def _get_detector():
    """Lazy singleton BookChangeDetector."""
    global _detector
    if _detector is None:
        from narrative_engine.research.book_change_detector import BookChangeDetector

        _detector = BookChangeDetector()
        _detector.initialize()
        log.info("temporal_updates_detector_initialized")
    return _detector


def reset_manager_singleton():
    """Сброс singleton'ов (используется тестами для изоляции)."""
    global _manager, _detector
    _manager = None
    _detector = None


# ── Модели ответов ────────────────────────────────────────────


class FindingView(BaseModel):
    id: str
    kind: str
    raw_text: str
    value: str
    line_number: int
    context: str = ""
    category: str
    confidence: float

    model_config = {"from_attributes": True}


class RejectRequest(BaseModel):
    """Причина отклонения (опциональна)."""

    reason: str = Field("", max_length=500)


# ── Helpers ──────────────────────────────────────────────────


def _finding_view(f) -> dict:
    return {
        "id": f.id,
        "kind": f.kind,
        "raw_text": f.raw_text,
        "value": f.value,
        "line_number": f.line_number,
        "context": f.context[:300],
        "category": f.category.value,
        "confidence": f.confidence,
    }


def _manager_view() -> dict:
    mgr = _get_manager()
    return {
        "id": "temporal_updates_manager",
        "pending": len(mgr.pending),
        "confirmed": len(mgr.confirmed),
        "rejected": len(mgr.rejected),
    }


# ── POST /scan — триггер цепочки M10 (только явный вызов) ─────


@router.post(
    "/scan",
    summary="Сканировать книгу на temporal-изменения",
    dependencies=[Depends(require_role("editor", "admin"))],
)
async def scan_book():
    """Явный запуск цепочки M10: детектор → извлечение → submit в pending.

    Idempotent: без изменения книги → 0 новых предложений.
    Не автоскан: никаких фоновых процессов.
    """
    detector = _get_detector()
    snapshot = detector.watch()

    if snapshot is None:
        return {
            "ok": True,
            "data": {
                "book_changed": False,
                "new_findings": 0,
                "duplicate_findings": 0,
                "total_pending": len(_get_manager().pending),
            },
        }

    from narrative_engine.research.temporal_extractor import TemporalExtractor

    findings = TemporalExtractor().extract(snapshot.content)
    if findings:
        result = _get_manager().submit_findings(findings)
    else:
        result = {"new": 0, "duplicates": 0, "total_pending": len(_get_manager().pending)}

    return {
        "ok": True,
        "data": {
            "book_changed": True,
            "snapshot": {
                "mtime": snapshot.mtime,
                "sha256": snapshot.sha256[:12] + "...",
                "size_bytes": snapshot.size_bytes,
            },
            "extracted": len(findings),
            **result,
        },
    }


# ── GET: список / счётчики / история / детали ─────────────────


@router.get(
    "",
    summary="Список pending temporal-предложений",
    dependencies=[Depends(require_role("reader", "editor", "admin"))],
)
async def list_pending():
    """Pending предложения (не применены, WorldModel не тронута)."""
    mgr = _get_manager()
    return {
        "ok": True,
        "data": [_finding_view(f) for f in mgr.pending],
        "total": len(mgr.pending),
    }


@router.get(
    "/stats",
    summary="Счётчики очереди",
    dependencies=[Depends(require_role("reader", "editor", "admin"))],
)
async def get_stats():
    mgr = _get_manager()
    return {"ok": True, "data": mgr.stats()}


@router.get(
    "/history",
    summary="История подтверждённых и отклонённых",
    dependencies=[Depends(require_role("reader", "editor", "admin"))],
)
async def get_history():
    """Аудит-след: подтверждённые и отклонённые находки (in-memory)."""
    mgr = _get_manager()
    confirmed = [{**_finding_view(f), "status": "confirmed"} for f in mgr.confirmed]
    rejected = [{**_finding_view(f), "status": "rejected", "reason": reason} for f, reason in mgr.rejected]
    return {
        "ok": True,
        "data": {
            "confirmed": confirmed,
            "rejected": rejected,
        },
    }


@router.get(
    "/{finding_id}",
    summary="Детали temporal-предложения",
    dependencies=[Depends(require_role("reader", "editor", "admin"))],
)
async def get_finding(finding_id: str):
    """Найти находку по id среди pending / confirmed / rejected."""
    mgr = _get_manager()

    for f in mgr.pending:
        if f.id == finding_id:
            return {"ok": True, "data": {**_finding_view(f), "status": "pending"}}

    for f in mgr.confirmed:
        if f.id == finding_id:
            return {"ok": True, "data": {**_finding_view(f), "status": "confirmed"}}

    for f, reason in mgr.rejected:
        if f.id == finding_id:
            return {"ok": True, "data": {**_finding_view(f), "status": "rejected", "reason": reason}}

    raise HTTPException(404, detail=f"Finding '{finding_id}' not found")


# ── Confirmation gate (прокси к менеджеру M10, БЕЗ изменений его логики) ──


@router.post(
    "/{finding_id}/confirm",
    summary="Подтвердить temporal-предложение (human confirmation)",
    dependencies=[Depends(require_role("editor", "admin"))],
)
async def confirm_finding(finding_id: str):
    """Граница подтверждения: manager.confirm() → validation → apply → save → refresh.

    RBAC: только editor/admin (утверждено владельцем). Читатель никогда
    не может изменить WorldModel.
    """
    mgr = _get_manager()
    result = mgr.confirm(finding_id)

    if not result.ok:
        # Разделяем причины: не найдено vs validation/conflict
        if "not_found" in result.reason:
            raise HTTPException(404, detail=result.reason)
        raise HTTPException(409, detail=f"Confirmation rejected: {result.reason}")

    return {
        "ok": True,
        "data": {
            "finding_id": finding_id,
            "applied": result.applied,
            "world_model_saved": result.world_model_saved,
            "temporal_refreshed": result.temporal_refreshed,
            "manager": _manager_view(),
        },
    }


@router.post(
    "/{finding_id}/reject",
    summary="Отклонить temporal-предложение",
    dependencies=[Depends(require_role("editor", "admin"))],
)
async def reject_finding(finding_id: str, req: Optional[RejectRequest] = None):
    """Отклонение: WorldModel не трогается. RBAC: editor/admin."""
    mgr = _get_manager()
    reason = req.reason if req else ""
    result = mgr.reject(finding_id, reason=reason)

    if not result.ok:
        if "not_found" in result.reason:
            raise HTTPException(404, detail=result.reason)
        raise HTTPException(409, detail=f"Reject rejected: {result.reason}")

    return {
        "ok": True,
        "data": {
            "finding_id": finding_id,
            "applied": False,
            "manager": _manager_view(),
        },
    }
