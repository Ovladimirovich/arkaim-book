"""
Email — интеграция для подписки читателей и рассылок.

Никаких автономных рассылок. Только:
- Форма подписки на дашборде
- Шаблоны писем на основе Pulse.build_context()
- Рассылка только после подтверждения автора (Принцип 11)
"""
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

log = logging.getLogger("hermes.email")

DB_PATH = Path(__file__).resolve().parent.parent.parent / "runtime" / "memory" / "subscribers.db"
TEMPLATES_DIR = Path(__file__).resolve().parent / "email_templates"


@dataclass
class Subscriber:
    email: str
    name: str = ""
    subscribed_at: str = ""
    is_active: bool = True
    topics: list[str] | None = None


@dataclass
class EmailDraft:
    id: int = 0
    subject: str = ""
    body_html: str = ""
    body_text: str = ""
    target_topics: list[str] | None = None
    created_at: str = ""
    status: str = "draft"  # draft | pending_approval | approved | sent
    approved_at: str = ""
    sent_at: str = ""


class SubscriberStore:
    """Хранилище подписчиков (SQLite)."""

    def __init__(self, db_path: str | None = None):
        self._db_path = str(db_path or DB_PATH)
        self._conn: aiosqlite.Connection | None = None

    async def _ensure_db(self):
        if self._conn is not None:
            return
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS subscribers (
                email TEXT PRIMARY KEY,
                name TEXT DEFAULT '',
                subscribed_at TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                topics TEXT DEFAULT '[]'
            );
            CREATE TABLE IF NOT EXISTS email_drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                body_html TEXT NOT NULL,
                body_text TEXT NOT NULL,
                target_topics TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                status TEXT DEFAULT 'draft',
                approved_at TEXT DEFAULT '',
                sent_at TEXT DEFAULT ''
            );
        """)

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None

    # ── Подписчики ──

    async def subscribe(self, email: str, name: str = "") -> Subscriber:
        await self._ensure_db()
        now = datetime.now(tz=timezone.utc).isoformat()
        await self._conn.execute(
            "INSERT OR REPLACE INTO subscribers (email, name, subscribed_at, is_active) VALUES (?, ?, ?, 1)",
            (email, name, now),
        )
        await self._conn.commit()
        log.info("subscriber_added email=%s", email)
        return Subscriber(email=email, name=name, subscribed_at=now)

    async def unsubscribe(self, email: str) -> bool:
        await self._ensure_db()
        cursor = await self._conn.execute(
            "UPDATE subscribers SET is_active = 0 WHERE email = ?", (email,)
        )
        await self._conn.commit()
        log.info("subscriber_removed email=%s", email)
        return cursor.rowcount > 0

    async def list_active(self) -> list[Subscriber]:
        await self._ensure_db()
        cursor = await self._conn.execute(
            "SELECT email, name, subscribed_at, topics FROM subscribers WHERE is_active = 1 ORDER BY subscribed_at DESC"
        )
        rows = await cursor.fetchall()
        return [Subscriber(email=r["email"], name=r["name"] or "", subscribed_at=r["subscribed_at"], topics=json.loads(r["topics"] or "[]")) for r in rows]

    async def count(self) -> int:
        await self._ensure_db()
        row = await (await self._conn.execute("SELECT COUNT(*) as cnt FROM subscribers WHERE is_active = 1")).fetchone()
        return row["cnt"] if row else 0

    # ── Черновики писем ──

    async def save_draft(self, draft: EmailDraft) -> int:
        await self._ensure_db()
        now = datetime.now(tz=timezone.utc).isoformat()
        draft.created_at = now
        cursor = await self._conn.execute(
            "INSERT INTO email_drafts (subject, body_html, body_text, target_topics, created_at, status) VALUES (?, ?, ?, ?, ?, ?)",
            (draft.subject, draft.body_html, draft.body_text, json.dumps(draft.target_topics or []), now, draft.status),
        )
        await self._conn.commit()
        return cursor.lastrowid

    async def approve_draft(self, draft_id: int) -> bool:
        await self._ensure_db()
        now = datetime.now(tz=timezone.utc).isoformat()
        cursor = await self._conn.execute(
            "UPDATE email_drafts SET status = 'approved', approved_at = ? WHERE id = ? AND status = 'draft'",
            (now, draft_id),
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    async def list_drafts(self, status: str | None = None) -> list[EmailDraft]:
        await self._ensure_db()
        if status:
            cursor = await self._conn.execute(
                "SELECT id, subject, body_html, body_text, target_topics, created_at, status, approved_at, sent_at FROM email_drafts WHERE status = ? ORDER BY created_at DESC",
                (status,),
            )
        else:
            cursor = await self._conn.execute(
                "SELECT id, subject, body_html, body_text, target_topics, created_at, status, approved_at, sent_at FROM email_drafts ORDER BY created_at DESC"
            )
        rows = await cursor.fetchall()
        result = []
        for r in rows:
            result.append(EmailDraft(
                id=r["id"],
                subject=r["subject"],
                body_html=r["body_html"],
                body_text=r["body_text"],
                target_topics=json.loads(r["target_topics"] or "[]"),
                created_at=r["created_at"],
                status=r["status"],
            ))
        return result

    async def get_stats(self) -> dict:
        await self._ensure_db()
        subs = await self.count()
        drafts = await (await self._conn.execute("SELECT COUNT(*) as cnt FROM email_drafts")).fetchone()
        return {"subscribers": subs, "drafts": drafts["cnt"] if drafts else 0}


class EmailTemplates:
    """Генерация писем на основе Pulse.build_context()."""

    @staticmethod
    def build_from_pulse(
        pulse,
        topic: str | None = None,
        subscriber_name: str = "",
        template: str = "weekly",
    ) -> EmailDraft:
        """
        Создать черновик письма, автоматически сгенерировав контекст из Pulse.

        Args:
            pulse: BookPulse instance (должен быть загружен)
            topic: опциональная тема для deep_dive
            subscriber_name: имя подписчика
            template: "weekly" или "deep_dive"

        Returns:
            EmailDraft с заполненным body из pulse.build_context()
        """
        if pulse is None:
            log.warning("email_templates_pulse_none using_fallback")
            return EmailTemplates._fallback_template(topic, subscriber_name, template)

        # Генерируем контекст из живых слоёв Pulse
        try:
            pulse_context = pulse.build_context()
        except Exception as e:
            log.error("email_templates_pulse_build_error error=%s", e)
            return EmailTemplates._fallback_template(topic, subscriber_name, template)

        if not pulse_context:
            log.warning("email_templates_pulse_context_empty")
            return EmailTemplates._fallback_template(topic, subscriber_name, template)

        # Форматируем контекст для чтения человеком
        formatted = EmailTemplates._format_pulse_for_email(pulse_context)

        if template == "deep_dive" and topic:
            return EmailTemplates.topic_deep_dive(topic, formatted, subscriber_name)
        else:
            return EmailTemplates.weekly_digest(formatted, subscriber_name)

    @staticmethod
    def _format_pulse_for_email(context: str) -> str:
        """
        Преобразовать сырой pulse.build_context() в читаемый HTML.

        Убирает XML-теги, добавляет форматирование.
        """
        import re

        # Разбиваем по секциям
        sections = re.findall(r"<(\w+)>\n(.*?)\n</\w+>", context, re.DOTALL)

        html_parts = []
        for tag, content in sections:
            # Очистка от лишних пробелов
            clean = re.sub(r"\s+", " ", content).strip()
            if not clean:
                continue

            # Преобразуем в читаемый текст
            title_map = {
                "ЗНАНИЕ": "📚 Знание",
                "СМЫСЛ": "💡 Смысл",
                "ЛИЧНОСТЬ": "🎭 Личность",
                "МИССИЯ": "🎯 Миссия",
                "VISUAL_STYLE": "🎨 Визуальный стиль",
                "SCENE": "🎬 Сцены",
            }
            title = title_map.get(tag, tag)
            html_parts.append(f"<h4>{title}</h4><p>{clean}</p>")

        if html_parts:
            return "<hr>".join(html_parts)

        # Fallback: просто убираем теги
        clean = re.sub(r"<[^>]+>", "", context)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    @staticmethod
    def _fallback_template(topic, subscriber_name, template):
        """Fallback когда Pulse недоступен."""
        name = subscriber_name or "Читатель"
        if template == "deep_dive" and topic:
            body_text = f"Здравствуйте, {name}!\n\nПо вашим вопросам мы подготовили подробный материал о «{topic}».\n\nС уважением,\nЦифровое представительство книги"
            body_html = f"<h2>Здравствуйте, {name}!</h2><p>По вашим вопросам мы подготовили подробный материал.</p><h3>{topic}</h3><p><em>Цифровое представительство книги</em></p>"
            return EmailDraft(
                subject=f"Подробнее о «{topic}»",
                body_html=body_html,
                body_text=body_text,
                target_topics=[topic],
                status="pending_approval",
            )
        else:
            body_text = f"Здравствуйте, {name}!\n\nКнига «Наследие Аркаима» подготовила для вас новую подборку.\n\nС уважением,\nЦифровое представительство книги"
            body_html = f"<h2>Здравствуйте, {name}!</h2><p>Книга «Наследие Аркаима» подготовила для вас новую подборку.</p><p><em>Цифровое представительство книги</em></p>"
            return EmailDraft(
                subject="Новое из мира «Наследие Аркаима»",
                body_html=body_html,
                body_text=body_text,
                status="pending_approval",
            )

    @staticmethod
    def weekly_digest(pulse_context: str, subscriber_name: str = "") -> EmailDraft:
        name = subscriber_name or "Читатель"
        body_text = f"Здравствуйте, {name}!\n\nКнига «Наследие Аркаима» подготовила для вас новую подборку.\n\n{pulse_context}\n\nС уважением,\nЦифровое представительство книги"
        body_html = f"<h2>Здравствуйте, {name}!</h2><p>Книга «Наследие Аркаима» подготовила для вас новую подборку.</p><hr>{pulse_context}<hr><p><em>Цифровое представительство книги</em></p>"
        return EmailDraft(
            subject="Новое из мира «Наследие Аркаима»",
            body_html=body_html,
            body_text=body_text,
            status="pending_approval",
        )

    @staticmethod
    def topic_deep_dive(topic: str, pulse_context: str, subscriber_name: str = "") -> EmailDraft:
        name = subscriber_name or "Читатель"
        body_text = f"Здравствуйте, {name}!\n\nПо вашим вопросам мы подготовили подробный материал о «{topic}».\n\n{pulse_context}\n\nС уважением,\nЦифровое представительство книги"
        body_html = f"<h2>Здравствуйте, {name}!</h2><p>По вашим вопросам мы подготовили подробный материал.</p><h3>{topic}</h3><hr>{pulse_context}<hr><p><em>Цифровое представительство книги</em></p>"
        return EmailDraft(
            subject=f"Подробнее о «{topic}»",
            body_html=body_html,
            body_text=body_text,
            target_topics=[topic],
            status="pending_approval",
        )
