"""email_sender — механизм отправки email-рассылок.

Поддерживает три режима (задаётся переменной EMAIL_MODE):
  - mock     : письма логируются, не отправляются (по умолчанию)
  - smtp     : отправка через SMTP-сервер
  - sendgrid : отправка через SendGrid API

Переменные окружения:
  EMAIL_MODE       = mock|smtp|sendgrid (default: mock)
  SMTP_HOST        = smtp.example.com
  SMTP_PORT        = 587
  SMTP_USER        = user@example.com
  SMTP_PASS        = password
  SMTP_USE_TLS     = true|false (default: true)
  SENDGRID_API_KEY = SG.xxx

  EMAIL_FROM         = от кого (default: "Arkaim <noreply@arkaim.local>")
  EMAIL_FROM_NAME    = имя отправителя
"""
import json
import logging
import smtplib
import ssl
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

log = logging.getLogger("hermes.email_sender")


@dataclass
class EmailMessage:
    """Готовое сообщение для отправки."""
    to_email: str
    subject: str
    body_html: str
    body_text: str = ""
    cc: list[str] = field(default_factory=list)

    def build_mime(self, from_email: str, from_name: str = "") -> MIMEMultipart:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{from_name} <{from_email}>" if from_name else from_email
        msg["To"] = self.to_email
        msg["Subject"] = self.subject
        if self.cc:
            msg["Cc"] = ", ".join(self.cc)
        msg.attach(MIMEText(self.body_text or self.body_html, "plain", "utf-8"))
        msg.attach(MIMEText(self.body_html, "html", "utf-8"))
        return msg


# ── Конфиг ────────────────────────────────────────────────

_MODE = "mock"
_SMTP_HOST = ""
_SMTP_PORT = 587
_SMTP_USER = ""
_SMTP_PASS = ""
_SMTP_USE_TLS = True
_SENDGRID_KEY = ""
_EMAIL_FROM = ""
_EMAIL_FROM_NAME = ""


def load_config():
    """Загрузить конфигурацию из переменных окружения."""
    global _MODE, _SMTP_HOST, _SMTP_PORT, _SMTP_USER, _SMTP_PASS
    global _SMTP_USE_TLS, _SENDGRID_KEY, _EMAIL_FROM, _EMAIL_FROM_NAME

    import os

    _MODE = os.getenv("EMAIL_MODE", "mock").strip().lower()
    _SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
    _SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    _SMTP_USER = os.getenv("SMTP_USER", "").strip()
    _SMTP_PASS = os.getenv("SMTP_PASS", "").strip()
    _SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    _SENDGRID_KEY = os.getenv("SENDGRID_API_KEY", "").strip()
    _EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@arkaim.local").strip()
    _EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Arkaim").strip()

    log.info("email_sender_config mode=%s from=%s", _MODE, _EMAIL_FROM)


def get_config() -> dict:
    return {
        "mode": _MODE,
        "smtp_host": _SMTP_HOST,
        "smtp_port": _SMTP_PORT,
        "smtp_user": _SMTP_USER,
        "sendgrid_key_set": bool(_SENDGRID_KEY),
        "email_from": _EMAIL_FROM,
    }


# ── Отправка ──────────────────────────────────────────────

async def send_message(msg: EmailMessage) -> bool:
    """Отправить email-сообщение через настроенный бэкенд."""
    if _MODE == "smtp":
        return await _send_smtp(msg)
    elif _MODE == "sendgrid":
        return await _send_sendgrid(msg)
    else:
        return await _send_mock(msg)


async def send_draft_to_subscribers(draft_id: int, store, pulse=None) -> dict:
    """
    Отправить одобренный черновик всем подписчикам (или по темам).

    Args:
        draft_id: ID одобренного черновика
        store: SubscriberStore для получения подписчиков
        pulse: BookPulse для авто-генерации контекста (опционально)

    Returns:
        dict: stats отправленных/ошибок
    """
    from presence.email import EmailTemplates

    # Получаем черновик из одобренных
    drafts = await store.list_drafts(status="approved")
    draft = None
    for d in drafts:
        if d.id == draft_id:
            draft = d
            break

    if not draft:
        log.error("email_draft_not_found_or_not_approved id=%d", draft_id)
        return {"ok": False, "error": "Черновик не найден или не одобрен"}

    if not draft:
        log.error("email_draft_not_found_or_not_approved id=%d", draft_id)
        return {"ok": False, "error": "Черновик не найден или не одобрен"}

    # Получаем подписчиков
    subscribers = await store.list_active()
    if not subscribers:
        log.warning("email_no_active_subscribers")
        return {"ok": True, "sent": 0, "errors": 0, "note": "Нет активных подписчиков"}

    # Фильтруем по темам (если черновик тематический)
    target_topics = draft.target_topics or []
    if target_topics:
        subscribers = [
            s for s in subscribers
            if s.topics and any(t in s.topics for t in target_topics)
        ]
        log.info("email_topic_filter topics=%s matched=%d", target_topics, len(subscribers))

    if not subscribers:
        log.warning("email_no_subscribers_for_topics topics=%s", target_topics)
        return {"ok": True, "sent": 0, "errors": 0, "note": "Нет подписчиков для выбранных тем"}

    # Генерируем контекст из Pulse (если pulse передан)
    pulse_context = ""
    if pulse:
        try:
            pulse_context = pulse.build_context()
        except Exception as e:
            log.error("pulse_build_context_error error=%s", e)

    stats = {"sent": 0, "errors": 0, "failed_emails": []}

    for sub in subscribers:
        # Формируем письмо: используем тело черновика
        msg = EmailMessage(
            to_email=sub.email,
            subject=draft.subject,
            body_html=draft.body_html,
            body_text=draft.body_text,
        )
        ok = await send_message(msg)
        if ok:
            stats["sent"] += 1
            log.info("email_sent_to email=%s subject=%s", sub.email, draft.subject)
        else:
            stats["errors"] += 1
            stats["failed_emails"].append(sub.email)
            log.warning("email_failed_to email=%s", sub.email)

    # Обновляем статус черновика
    await _mark_as_sent(store, draft_id)

    return stats


async def send_weekly_digest(store, pulse) -> dict:
    """
    Создать и отправить еженедельный дайджест из Pulse.

    Используется периодической задачей в main.py lifespan.
    """
    from presence.email import EmailTemplates

    subscribers = await store.list_active()
    if not subscribers:
        log.info("email_weekly_digest_skipped_no_subscribers")
        return {"skipped": True, "reason": "no_subscribers"}

    # Генерируем контекст из Pulse
    try:
        pulse_context = pulse.build_context()
    except Exception as e:
        log.error("email_weekly_digest_pulse_error error=%s", e)
        return {"skipped": True, "reason": "pulse_error", "error": str(e)}

    # Генерируем черновик
    draft = EmailTemplates.weekly_digest(pulse_context)

    # Сохраняем черновик
    draft_id = await store.save_draft(draft)
    # Одобрим автоматически (еженедельный дайджест — системное письмо)
    await store.approve_draft(draft_id)

    stats = await send_draft_to_subscribers(draft_id, store, pulse=pulse)
    stats["draft_id"] = draft_id
    stats["type"] = "weekly_digest"

    log.info("email_weekly_digest_sent sent=%d errors=%d", stats["sent"], stats["errors"])
    return stats


async def send_topic_deep_dive(store, pulse, topic: str) -> dict:
    """
    Создать и отправить глубокое письмо по теме из Pulse.

    Используется при обнаружении новых инсайтов по теме.
    """
    from presence.email import EmailTemplates

    subscribers = await store.list_active()
    if not subscribers:
        return {"skipped": True, "reason": "no_subscribers"}

    # Фильтруем по теме
    topic_subs = [
        s for s in subscribers
        if s.topics and topic in s.topics
    ]
    if not topic_subs:
        log.info("email_deep_dive_no_topic_subs topic=%s", topic)
        return {"skipped": True, "reason": "no_topic_subscribers", "topic": topic}

    try:
        pulse_context = pulse.build_context()
    except Exception as e:
        log.error("email_deep_dive_pulse_error error=%s", e)
        return {"skipped": True, "reason": "pulse_error"}

    draft = EmailTemplates.topic_deep_dive(topic, pulse_context)
    draft_id = await store.save_draft(draft)
    await store.approve_draft(draft_id)

    stats = await send_draft_to_subscribers(draft_id, store, pulse=pulse)
    stats["draft_id"] = draft_id
    stats["type"] = "topic_deep_dive"
    stats["topic"] = topic

    log.info("email_deep_dive_sent topic=%s sent=%d errors=%d", topic, stats["sent"], stats["errors"])
    return stats


# ── Бэкенды ───────────────────────────────────────────────

async def _send_mock(msg: EmailMessage) -> bool:
    """Mock-отправка: логируем, не отправляем."""
    log.info(
        "email_mock_send to=%s subject=%s",
        msg.to_email, msg.subject,
    )
    # В debug-режиме можно выводить тело
    if log.isEnabledFor(logging.DEBUG):
        log.debug("email_mock_body_html=%s", msg.body_html[:500])
    return True


async def _send_smtp(msg: EmailMessage) -> bool:
    """Отправка через SMTP."""
    import asyncio

    loop = asyncio.get_event_loop()

    def _do_send():
        mime = msg.build_mime(_EMAIL_FROM, _EMAIL_FROM_NAME)
        context = ssl.create_default_context()

        try:
            if _SMTP_USE_TLS:
                server = smtplib.SMTP(_SMTP_HOST, _SMTP_PORT, timeout=15)
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
            else:
                server = smtplib.SMTP(_SMTP_HOST, _SMTP_PORT, timeout=15)

            if _SMTP_USER and _SMTP_PASS:
                server.login(_SMTP_USER, _SMTP_PASS)

            recipients = [msg.to_email] + msg.cc
            server.sendmail(_EMAIL_FROM, recipients, mime.as_string())
            server.quit()
            return True
        except Exception as e:
            log.error("smtp_send_error error=%s", e)
            try:
                server.quit()
            except Exception:
                pass
            return False

    return await loop.run_in_executor(None, _do_send)


async def _send_sendgrid(msg: EmailMessage) -> bool:
    """Отправка через SendGrid API."""
    import httpx

    try:
        url = "https://api.sendgrid.com/v3/mail/send"
        payload = {
            "personalizations": [{"to": [{"email": msg.to_email}]}],
            "from": {"email": _EMAIL_FROM, "name": _EMAIL_FROM_NAME or None},
            "subject": msg.subject,
            "content": [
                {"type": "text/plain", "value": msg.body_text or msg.body_html},
                {"type": "text/html", "value": msg.body_html},
            ],
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {_SENDGRID_KEY}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
        log.info("sendgrid_sent to=%s subject=%s", msg.to_email, msg.subject)
        return True
    except Exception as e:
        log.error("sendgrid_error error=%s", e)
        return False


async def _mark_as_sent(store, draft_id: int):
    """Отметить черновик как отправленный."""
    try:
        from datetime import datetime, timezone
        now = datetime.now(tz=timezone.utc).isoformat()
        await store._ensure_db()
        await store._conn.execute(
            "UPDATE email_drafts SET status = 'sent', sent_at = ? WHERE id = ?",
            (now, draft_id),
        )
        await store._conn.commit()
    except Exception as e:
        log.error("mark_draft_sent_error error=%s", e)


# ── Init ──────────────────────────────────────────────────

load_config()

__all__ = [
    "EmailMessage",
    "send_message",
    "send_draft_to_subscribers",
    "send_weekly_digest",
    "send_topic_deep_dive",
    "get_config",
    "load_config",
]
