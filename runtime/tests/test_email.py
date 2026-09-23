"""Тесты для email-модуля: SubscriberStore, EmailTemplates, email_sender."""
import asyncio
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock

# Триггер lazy import для CORE/ (нужен для imports из presence/)
from core.main import app  # noqa: F401


# ── SubscriberStore ──────────────────────────────────────────

class TestSubscriberStore:
    """Тесты хранилища подписчиков."""

    @pytest.fixture
    def store(self):
        from presence.email import SubscriberStore
        fd, tmp = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        s = SubscriberStore(db_path=tmp)
        yield s
        asyncio.run(s.close())
        Path(tmp).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_subscribe(self, store):
        sub = await store.subscribe("test@example.com", "Test User")
        assert sub.email == "test@example.com"
        assert sub.name == "Test User"
        assert sub.is_active is True

    @pytest.mark.asyncio
    async def test_subscribe_no_name(self, store):
        sub = await store.subscribe("test2@example.com")
        assert sub.email == "test2@example.com"
        assert sub.name == ""

    @pytest.mark.asyncio
    async def test_unsubscribe(self, store):
        await store.subscribe("test@example.com")
        ok = await store.unsubscribe("test@example.com")
        assert ok is True

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent(self, store):
        ok = await store.unsubscribe("noone@example.com")
        assert ok is False

    @pytest.mark.asyncio
    async def test_list_active(self, store):
        await store.subscribe("a@example.com", "A")
        await store.subscribe("b@example.com", "B")
        subs = await store.list_active()
        assert len(subs) == 2

    @pytest.mark.asyncio
    async def test_count(self, store):
        await store.subscribe("a@example.com")
        await store.subscribe("b@example.com")
        cnt = await store.count()
        assert cnt == 2

    @pytest.mark.asyncio
    async def test_save_draft(self, store):
        from presence.email import EmailDraft
        draft = EmailDraft(
            subject="Test",
            body_html="<p>Test</p>",
            body_text="Test",
            status="draft",
        )
        draft_id = await store.save_draft(draft)
        assert draft_id > 0

    @pytest.mark.asyncio
    async def test_approve_draft(self, store):
        from presence.email import EmailDraft
        draft = EmailDraft(
            subject="Test",
            body_html="<p>Test</p>",
            body_text="Test",
            status="draft",
        )
        draft_id = await store.save_draft(draft)
        ok = await store.approve_draft(draft_id)
        assert ok is True

    @pytest.mark.asyncio
    async def test_list_drafts(self, store):
        from presence.email import EmailDraft
        d1 = EmailDraft(subject="A", body_html="A", body_text="A")
        d2 = EmailDraft(subject="B", body_html="B", body_text="B")
        await store.save_draft(d1)
        await store.save_draft(d2)
        drafts = await store.list_drafts()
        assert len(drafts) == 2

    @pytest.mark.asyncio
    async def test_get_stats(self, store):
        await store.subscribe("a@example.com")
        stats = await store.get_stats()
        assert "subscribers" in stats
        assert "drafts" in stats


# ── EmailTemplates ───────────────────────────────────────────

class TestEmailTemplates:
    """Тесты генерации email-шаблонов."""

    def test_weekly_digest(self):
        from presence.email import EmailTemplates
        draft = EmailTemplates.weekly_digest("context", "Reader")
        assert "Reader" in draft.body_text
        assert "context" in draft.body_html
        assert draft.status == "pending_approval"

    def test_topic_deep_dive(self):
        from presence.email import EmailTemplates
        draft = EmailTemplates.topic_deep_dive("Архитектура", "context", "Reader")
        assert "Архитектура" in draft.subject
        assert draft.target_topics == ["Архитектура"]

    def test_build_from_pulse_none(self):
        """Если pulse=None — fallback на пустой шаблон."""
        from presence.email import EmailTemplates
        draft = EmailTemplates.build_from_pulse(
            pulse=None,
            template="weekly",
        )
        assert draft.subject == "Новое из мира «Наследие Аркаима»"
        assert draft.status == "pending_approval"

    def test_build_from_pulse_with_mock(self):
        """pulse.build_context() вызывается корректно."""
        from presence.email import EmailTemplates

        mock_pulse = MagicMock()
        mock_pulse.build_context.return_value = (
            "<ЗНАНИЕ>\nТестовые знания\n</ЗНАНИЕ>\n"
            "<ЛИЧНОСТЬ>\nТестовая личность\n</ЛИЧНОСТЬ>"
        )

        draft = EmailTemplates.build_from_pulse(
            pulse=mock_pulse,
            template="weekly",
            subscriber_name="Test",
        )

        mock_pulse.build_context.assert_called_once()
        assert "Тестовые знания" in draft.body_html
        assert "Тестовая личность" in draft.body_html

    def test_build_from_pulse_deep_dive(self):
        """Deep dive с темой."""
        from presence.email import EmailTemplates

        mock_pulse = MagicMock()
        mock_pulse.build_context.return_value = "<ЗНАНИЕ>\nDeep dive content\n</ЗНАНИЕ>"

        draft = EmailTemplates.build_from_pulse(
            pulse=mock_pulse,
            topic="Архитектура",
            template="deep_dive",
        )

        assert "Архитектура" in draft.subject
        assert draft.target_topics == ["Архитектура"]

    def test_format_pulse_for_email(self):
        """Форматирование pulse-контекста в HTML."""
        from presence.email import EmailTemplates

        raw = (
            "<ЗНАНИЕ>\nКнига о наследии Аркаима\n</ЗНАНИЕ>\n"
            "<СМЫСЛ>\nПоиск истины\n</СМЫСЛ>\n"
            "<ЛИЧНОСТЬ>\nМудрый наставник\n</ЛИЧНОСТЬ>"
        )
        formatted = EmailTemplates._format_pulse_for_email(raw)

        assert "Знание" in formatted
        assert "Смысл" in formatted
        assert "Личность" in formatted
        assert "Книга о наследии Аркаима" in formatted

    def test_format_pulse_empty(self):
        """Пустой контекст — fallback."""
        from presence.email import EmailTemplates
        formatted = EmailTemplates._format_pulse_for_email("")
        assert formatted == ""

    def test_fallback_template_deep_dive(self):
        """Fallback для deep_dive."""
        from presence.email import EmailTemplates
        draft = EmailTemplates._fallback_template(
            topic="Test", subscriber_name="Name", template="deep_dive"
        )
        assert "Test" in draft.subject
        assert draft.target_topics == ["Test"]

    def test_fallback_template_weekly(self):
        """Fallback для weekly."""
        from presence.email import EmailTemplates
        draft = EmailTemplates._fallback_template(
            topic=None, subscriber_name="Name", template="weekly"
        )
        assert "Новое из мира" in draft.subject


# ── EmailSender (mock mode) ─────────────────────────────────

class TestEmailSender:
    """Тесты механизма отправки email."""

    @pytest.fixture(autouse=True)
    def _setup_mock_mode(self):
        """Убедимся что EMAIL_MODE=mock для тестов."""
        old_mode = os.environ.get("EMAIL_MODE")
        os.environ["EMAIL_MODE"] = "mock"
        from presence.email_sender import load_config
        load_config()
        yield
        if old_mode:
            os.environ["EMAIL_MODE"] = old_mode
        else:
            os.environ.pop("EMAIL_MODE", None)
        from presence.email_sender import load_config
        load_config()

    def test_send_message_mock(self):
        """Mock-режим всегда возвращает True."""
        from presence.email_sender import EmailMessage, send_message
        msg = EmailMessage(
            to_email="test@example.com",
            subject="Test",
            body_html="<p>Test</p>",
            body_text="Test",
        )
        result = asyncio.run(send_message(msg))
        assert result is True

    def test_email_message_build_mime(self):
        """Проверка сборки MIME-сообщения."""
        from presence.email_sender import EmailMessage
        msg = EmailMessage(
            to_email="to@example.com",
            subject="Subject",
            body_html="<p>HTML</p>",
            body_text="Text",
            cc=["cc@example.com"],
        )
        mime = msg.build_mime("from@example.com", "Sender")
        assert "to@example.com" in mime["To"]
        assert "cc@example.com" in mime["Cc"]
        assert "Subject" in mime["Subject"]

    @pytest.mark.asyncio
    async def test_send_draft_to_subscribers_no_subscribers(self):
        """Отправка без подписчиков."""
        from presence.email_sender import send_draft_to_subscribers
        from presence.email import SubscriberStore, EmailDraft

        fd, tmp = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        store = SubscriberStore(db_path=tmp)
        await store._ensure_db()

        draft = EmailDraft(
            subject="Test",
            body_html="<p>Test</p>",
            body_text="Test",
            status="draft",
        )
        did = await store.save_draft(draft)
        await store.approve_draft(did)

        stats = await send_draft_to_subscribers(did, store)
        assert stats["sent"] == 0
        assert stats.get("note") == "Нет активных подписчиков"

        await store.close()
        Path(tmp).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_send_draft_to_subscribers_with_subscribers(self):
        """Отправка подписчикам (mock)."""
        from presence.email_sender import send_draft_to_subscribers
        from presence.email import SubscriberStore, EmailDraft

        fd, tmp = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        store = SubscriberStore(db_path=tmp)
        await store._ensure_db()

        await store.subscribe("a@example.com", "A")
        await store.subscribe("b@example.com", "B")

        draft = EmailDraft(
            subject="Hello",
            body_html="<p>Hello</p>",
            body_text="Hello",
            status="draft",
        )
        did = await store.save_draft(draft)
        await store.approve_draft(did)

        stats = await send_draft_to_subscribers(did, store)
        assert stats["sent"] == 2
        assert stats["errors"] == 0

        await store.close()
        Path(tmp).unlink(missing_ok=True)

    def test_get_config(self):
        """Проверка получения конфигурации."""
        from presence.email_sender import get_config
        cfg = get_config()
        assert cfg["mode"] == "mock"
        assert "email_from" in cfg


# ── EmailAPI Integration ─────────────────────────────────────

class TestEmailAPI:
    """Интеграционные тесты email API endpoints."""

    def test_subscribe_endpoint(self):
        """POST /book/email/subscribe."""
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.post("/book/email/subscribe", json={
            "email": "test@example.com",
            "name": "Test User",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["email"] == "test@example.com"

    def test_subscribe_duplicate(self):
        """Дубликат подписки."""
        from fastapi.testclient import TestClient
        client = TestClient(app)
        client.post("/book/email/subscribe", json={
            "email": "dup@example.com",
            "name": "Dup",
        })
        resp = client.post("/book/email/subscribe", json={
            "email": "dup@example.com",
            "name": "Dup 2",
        })
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_unsubscribe(self):
        """POST /book/email/unsubscribe."""
        from fastapi.testclient import TestClient
        client = TestClient(app)
        client.post("/book/email/subscribe", json={
            "email": "unsub@example.com",
        })
        resp = client.post("/book/email/unsubscribe?email=unsub@example.com")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_list_subscribers(self):
        """GET /book/email/subscribers."""
        from fastapi.testclient import TestClient
        client = TestClient(app)
        client.post("/book/email/subscribe", json={
            "email": "list@example.com",
            "name": "List",
        })
        resp = client.get("/book/email/subscribers")
        assert resp.status_code == 200
        subs = resp.json()
        assert isinstance(subs, list)

    def test_draft_auto(self):
        """POST /book/email/draft/auto — автогенерация из Pulse."""
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.post("/book/email/draft/auto", json={
            "template": "weekly",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "draft_id" in data
        assert "pulse_used" in data

    def test_draft_auto_deep_dive(self):
        """POST /book/email/draft/auto с темой."""
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.post("/book/email/draft/auto", json={
            "template": "deep_dive",
            "topic": "Архитектура",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True

    def test_list_drafts(self):
        """GET /book/email/drafts."""
        from fastapi.testclient import TestClient
        client = TestClient(app)
        client.post("/book/email/draft/auto", json={"template": "weekly"})
        resp = client.get("/book/email/drafts")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_email_stats(self):
        """GET /book/email/stats."""
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/book/email/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "subscribers" in data
        assert "drafts" in data
        assert "sender_config" in data


# ── Config ──────────────────────────────────────────────────

class TestEmailConfig:
    """Проверка конфигурации email."""

    def test_config_defaults(self):
        """Проверка дефолтных значений в config."""
        from config import config
        assert config.EMAIL_MODE == "mock"
        assert config.EMAIL_FROM == "noreply@arkaim.local"
        assert config.EMAIL_FROM_NAME == "Arkaim"
        assert config.EMAIL_DIGEST_INTERVAL == 604800

    def test_config_env_override(self):
        """Проверка что env-переменные читаются."""
        os.environ["EMAIL_MODE"] = "smtp"
        os.environ["SMTP_HOST"] = "smtp.test.com"
        os.environ["SENDGRID_API_KEY"] = "SG.test"

        import importlib
        import config as cfg_module
        importlib.reload(cfg_module)

        assert cfg_module.config.EMAIL_MODE == "smtp"
        assert cfg_module.config.SMTP_HOST == "smtp.test.com"
        assert cfg_module.config.SENDGRID_API_KEY == "SG.test"

        os.environ.pop("EMAIL_MODE", None)
        os.environ.pop("SMTP_HOST", None)
        os.environ.pop("SENDGRID_API_KEY", None)
        importlib.reload(cfg_module)
