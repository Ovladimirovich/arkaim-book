"""Reader Memory — эндпоинты профиля читателя (/book/reader/*)."""
import logging

from fastapi import APIRouter, Depends, Request, Body

from auth.rbac import require_role, get_current_user
from core.dto.responses import (
    ReaderProfileResponse, ReaderContextResponse, ReaderStatsResponse,
    ReadingProgressItem, ReadingPositionResponse, ReadingStatsResponse,
)
from core.adc_deps import get_reader_memory

router = APIRouter(prefix="/reader", tags=["Reader Memory"])


def _get_memory_store():
    from memory.store import get_memory_store
    return get_memory_store()


@router.get("/profile", response_model=ReaderProfileResponse, dependencies=[Depends(require_role("reader"))])
async def reader_profile(request: Request, reader_memory=Depends(get_reader_memory)):
    user = await get_current_user(request)
    profile = await reader_memory.get_or_create(
        reader_id=user["user_id"],
        display_name=user.get("display_name", ""),
        provider=user.get("provider", ""),
    )
    return ReaderProfileResponse(
        reader_id=profile.reader_id,
        display_name=profile.display_name,
        questions_total=profile.questions_total,
        conversation_count=profile.conversation_count,
        last_topic=profile.last_topic,
        topics=[
            {"name": t.name, "depth": t.depth, "questions": t.questions_count}
            for t in sorted(profile.topics.values(), key=lambda x: x.depth, reverse=True)
        ],
    )


@router.get("/context", response_model=ReaderContextResponse, dependencies=[Depends(require_role("reader"))])
async def reader_context(request: Request, reader_memory=Depends(get_reader_memory)):
    user = await get_current_user(request)
    context = await reader_memory.build_reader_context(user["user_id"])
    return ReaderContextResponse(context=context)


@router.get("/stats", response_model=ReaderStatsResponse, dependencies=[Depends(require_role("admin"))])
async def reader_stats(reader_memory=Depends(get_reader_memory)):
    stats = await reader_memory.get_stats()
    return ReaderStatsResponse(**stats)


# ── History endpoints ────────────────────────────────


@router.get("/history", dependencies=[Depends(require_role("reader"))])
async def reader_history(request: Request, limit: int = 50):
    """История вопросов текущего пользователя."""
    log = logging.getLogger("hermes.reader")
    user = await get_current_user(request)
    store = _get_memory_store()
    try:
        history = await store.get_user_history(user["user_id"], limit=limit)
        return {"ok": True, "data": history, "total": len(history)}
    except Exception as e:
        log.exception("reader_history_error %s: %s", type(e).__name__, e)
        raise


@router.get("/history/full", dependencies=[Depends(require_role("reader"))])
async def reader_history_full(request: Request, session_id: str | None = None, limit: int = 100):
    """Полная история (user + assistant) для текущего пользователя."""
    user = await get_current_user(request)
    store = _get_memory_store()
    try:
        history = await store.get_user_history_full(user["user_id"], session_id=session_id, limit=limit)
        return {"ok": True, "data": history, "total": len(history)}
    finally:
        pass


@router.get("/history/sessions", dependencies=[Depends(require_role("reader"))])
async def reader_sessions(request: Request):
    """Список сессий пользователя."""
    user = await get_current_user(request)
    store = _get_memory_store()
    try:
        sessions = await store.get_user_sessions(user["user_id"])
        return {"ok": True, "data": sessions}
    finally:
        pass


@router.get("/history/stats", dependencies=[Depends(require_role("reader"))])
async def reader_history_stats(request: Request):
    """Статистика истории пользователя."""
    user = await get_current_user(request)
    store = _get_memory_store()
    try:
        stats = await store.get_user_stats(user["user_id"])
        return {"ok": True, **stats}
    finally:
        pass


# ── Reading Progress ────────────────────────────────


@router.post("/reading-event", dependencies=[Depends(require_role("reader"))])
async def record_reading_event(
    request: Request,
    chapter_id: str = Body(...),
    chapter_index: int = Body(0),
    read_seconds: int = Body(0),
    scroll_percent: float = Body(0.0),
    completed: bool = Body(False),
    reader_memory=Depends(get_reader_memory),
):
    """Записать событие чтения главы."""
    user = await get_current_user(request)
    await reader_memory.record_reading(
        reader_id=user["user_id"],
        chapter_id=chapter_id,
        chapter_index=chapter_index,
        read_seconds=read_seconds,
        scroll_percent=scroll_percent,
        completed=completed,
    )
    return {"ok": True}


@router.get("/reading-progress", dependencies=[Depends(require_role("reader"))])
async def get_reading_progress(
    request: Request,
    reader_memory=Depends(get_reader_memory),
):
    """Прогресс чтения всех глав."""
    user = await get_current_user(request)
    progress = await reader_memory.get_reading_progress(user["user_id"])
    stats = await reader_memory.get_reading_stats(user["user_id"])
    return {"ok": True, "data": progress, "stats": stats}


@router.get("/reading-position", dependencies=[Depends(require_role("reader"))])
async def get_reading_position(
    request: Request,
    reader_memory=Depends(get_reader_memory),
):
    """Последняя позиция чтения (для «продолжить»)."""
    user = await get_current_user(request)
    position = await reader_memory.get_last_position(user["user_id"])
    return {"ok": True, "data": position}
