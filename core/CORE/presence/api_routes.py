"""FastAPI router для Presence — наблюдение и предложения автору."""
from fastapi import APIRouter, Depends

from auth.rbac import require_role
from presence.observer import PresenceObserver
from presence.suggester import PresenceSuggester

router = APIRouter(prefix="/presence", tags=["Presence"])

_observer: PresenceObserver | None = None
_suggester: PresenceSuggester | None = None


def set_deps(observer: PresenceObserver, suggester: PresenceSuggester):
    global _observer, _suggester
    _observer = observer
    _suggester = suggester


def get_observer() -> PresenceObserver:
    if _observer is None:
        raise RuntimeError("PresenceObserver not initialized")
    return _observer


def get_suggester() -> PresenceSuggester:
    if _suggester is None:
        raise RuntimeError("PresenceSuggester not initialized")
    return _suggester


# ── Наблюдения ─────────────────────────────────────


@router.get("/trending", dependencies=[Depends(require_role("reader"))])
async def trending(min_hits: int = 3, hours: int = 24):
    """Темы, которые сейчас обсуждают читатели."""
    observer = get_observer()
    topics = await observer.get_trending_topics(min_hits=min_hits, hours=hours)
    return {"trending": [t.to_dict() for t in topics], "total": len(topics)}


@router.post("/observe", dependencies=[Depends(require_role("reader"))])
async def observe_keyword(keyword: str, source: str = "api"):
    """Зарегистрировать упоминание темы (из внешнего источника)."""
    observer = get_observer()
    observer.register_keyword_hit(keyword, source=source)
    return {"ok": True, "keyword": keyword}


# ── Предложения автору ────────────────────────────


@router.get("/suggestions", dependencies=[Depends(require_role("editor"))])
async def list_suggestions(status: str | None = None):
    """Список предложений для автора."""
    suggester = get_suggester()
    if status == "pending":
        return {"suggestions": [s.to_dict() for s in suggester.list_pending()]}
    return {"suggestions": [s.to_dict() for s in suggester.list_all()]}


@router.post("/suggestions/{suggestion_id}/view", dependencies=[Depends(require_role("admin"))])
async def view_suggestion(suggestion_id: str):
    """Автор посмотрел предложение."""
    suggester = get_suggester()
    s = suggester.view(suggestion_id)
    if not s:
        return {"error": "not_found"}
    return {"ok": True, "suggestion": s.to_dict()}


@router.post("/suggestions/{suggestion_id}/approve", dependencies=[Depends(require_role("admin"))])
async def approve_suggestion(suggestion_id: str):
    """Автор одобрил предложение."""
    suggester = get_suggester()
    s = suggester.approve(suggestion_id)
    if not s:
        return {"error": "not_found"}
    return {"ok": True, "suggestion": s.to_dict()}


@router.post("/suggestions/{suggestion_id}/reject", dependencies=[Depends(require_role("admin"))])
async def reject_suggestion(suggestion_id: str, comment: str = ""):
    """Автор отклонил предложение."""
    suggester = get_suggester()
    s = suggester.reject(suggestion_id, comment)
    if not s:
        return {"error": "not_found"}
    return {"ok": True, "suggestion": s.to_dict()}


@router.get("/suggestions/stats", dependencies=[Depends(require_role("admin"))])
async def suggestion_stats():
    """Статистика предложений."""
    suggester = get_suggester()
    return suggester.get_stats()
