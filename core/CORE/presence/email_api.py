"""FastAPI router для Email — подписка и рассылки."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.rbac import require_role
from presence.email import SubscriberStore, EmailTemplates
from presence.email_sender import (
    send_draft_to_subscribers,
    send_weekly_digest,
    get_config as get_email_sender_config,
)

router = APIRouter(prefix="/email", tags=["Email"])

_store: SubscriberStore | None = None


def init_store():
    global _store
    if _store is None:
        _store = SubscriberStore()
    return _store


def get_store():
    if _store is None:
        init_store()
    return _store


class SubscribeRequest(BaseModel):
    email: str
    name: str = ""


class AutoDraftRequest(BaseModel):
    """Запрос на автогенерацию черновика из Pulse."""
    topic: str | None = None  # для deep_dive
    template: str = "weekly"  # weekly | deep_dive


class SendDraftRequest(BaseModel):
    """Запрос на отправку черновика."""
    # В теле не нужен, draft_id в path


@router.post("/subscribe")
async def subscribe(req: SubscribeRequest):
    """Подписаться на рассылку."""
    store = get_store()
    sub = await store.subscribe(req.email, req.name)
    return {"ok": True, "email": sub.email}


@router.post("/unsubscribe")
async def unsubscribe(email: str):
    """Отписаться от рассылки."""
    store = get_store()
    ok = await store.unsubscribe(email)
    return {"ok": ok}


@router.get("/stats", dependencies=[Depends(require_role("admin"))])
async def email_stats():
    """Статистика подписок."""
    store = get_store()
    result = await store.get_stats()
    result["sender_config"] = get_email_sender_config()
    return result


@router.get("/subscribers", dependencies=[Depends(require_role("admin"))])
async def list_subscribers():
    """Список подписчиков."""
    store = get_store()
    subs = await store.list_active()
    return [{"email": s.email, "name": s.name, "subscribed_at": s.subscribed_at} for s in subs]


# ── Автогенерация из Pulse ─────────────────────────────────

@router.post("/draft/auto", dependencies=[Depends(require_role("editor"))])
async def draft_auto(req: AutoDraftRequest):
    """
    Создать черновик автоматически из Pulse.

    Использует pulse.build_context() для генерации содержимого.
    Если Pulse не загружен — fallback на пустой шаблон.
    """
    store = get_store()

    # Пытаемся получить Pulse
    pulse = None
    try:
        from core.presence_manager import get_pulse
        pulse = get_pulse()
    except Exception:
        # Pulse может быть не инициализирован
        pass

    draft = EmailTemplates.build_from_pulse(
        pulse=pulse,
        topic=req.topic,
        template=req.template,
    )

    draft_id = await store.save_draft(draft)
    return {
        "ok": True,
        "draft_id": draft_id,
        "subject": draft.subject,
        "status": draft.status,
        "pulse_used": pulse is not None,
    }


# ── Ручная генерация (legacy) ─────────────────────────────

@router.post("/draft/topic/{topic}", dependencies=[Depends(require_role("editor"))])
async def draft_topic_email(topic: str, pulse_context: str = ""):
    """Создать черновик письма по теме (на утверждение автору)."""
    store = get_store()
    draft = EmailTemplates.topic_deep_dive(topic, pulse_context)
    draft_id = await store.save_draft(draft)
    return {"ok": True, "draft_id": draft_id, "subject": draft.subject}


@router.post("/draft/weekly", dependencies=[Depends(require_role("editor"))])
async def draft_weekly(pulse_context: str = ""):
    """Создать еженедельный дайджест (на утверждение автору)."""
    store = get_store()
    draft = EmailTemplates.weekly_digest(pulse_context)
    draft_id = await store.save_draft(draft)
    return {"ok": True, "draft_id": draft_id, "subject": draft.subject}


# ── Черновики ─────────────────────────────────────────────

@router.get("/drafts", dependencies=[Depends(require_role("editor"))])
async def list_drafts(status: str | None = None):
    """Список черновиков писем."""
    store = get_store()
    drafts = await store.list_drafts(status)
    return [
        {
            "id": d.id,
            "subject": d.subject,
            "status": d.status,
            "created_at": d.created_at,
            "approved_at": getattr(d, "approved_at", ""),
            "sent_at": getattr(d, "sent_at", ""),
        }
        for d in drafts
    ]


@router.post("/drafts/{draft_id}/approve", dependencies=[Depends(require_role("admin"))])
async def approve_draft(draft_id: int):
    """Автор одобрил черновик."""
    store = get_store()
    ok = await store.approve_draft(draft_id)
    if not ok:
        raise HTTPException(404, "Черновик не найден или уже одобрен")
    return {"ok": True}


# ── Отправка ──────────────────────────────────────────────

@router.post("/drafts/{draft_id}/send", dependencies=[Depends(require_role("admin"))])
async def send_draft(draft_id: int):
    """
    Отправить одобренный черновик всем подходящим подписчикам.

    Возвращает статистику: sent / errors / failed_emails.
    """
    store = get_store()

    # Проверяем что черновик одобрен
    drafts = await store.list_drafts(status="approved")
    draft = None
    for d in drafts:
        if d.id == draft_id:
            draft = d
            break

    if not draft:
        raise HTTPException(404, "Черновик не найден или не одобрен")

    # Пытаемся получить Pulse для логирования
    pulse = None
    try:
        from core.presence_manager import get_pulse
        pulse = get_pulse()
    except Exception:
        pass

    stats = await send_draft_to_subscribers(draft_id, store, pulse=pulse)
    return stats


@router.post("/send/weekly-digest", dependencies=[Depends(require_role("admin"))])
async def send_weekly_digest_endpoint():
    """
    Отправить еженедельный дайджест автоматически из Pulse.

    Создаёт черновик, одобряет и отправляет всем подписчикам.
    """
    store = get_store()

    pulse = None
    try:
        from core.presence_manager import get_pulse
        pulse = get_pulse()
        if not pulse:
            raise HTTPException(503, "Pulse не загружен")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, "Pulse недоступен")

    stats = await send_weekly_digest(store, pulse)
    return stats


@router.post("/send/topic/{topic}", dependencies=[Depends(require_role("admin"))])
async def send_topic_deep_dive_endpoint(topic: str):
    """
    Отправить глубокое письмо по теме подписчикам этой темы.

    Использует Pulse для генерации содержимого.
    """
    store = get_store()

    pulse = None
    try:
        from core.presence_manager import get_pulse
        pulse = get_pulse()
        if not pulse:
            raise HTTPException(503, "Pulse не загружен")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, "Pulse недоступен")

    from presence.email_sender import send_topic_deep_dive
    stats = await send_topic_deep_dive(store, pulse, topic)
    return stats
