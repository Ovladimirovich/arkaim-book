"""
Модуль для работы с Telegram.
Включает обработку сообщений, управление черновиками (SQLite) и отправку уведомлений.
Интеграция с Telegram Bot API для российского рынка.
"""
import logging
import sqlite3
import uuid
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

import httpx
from config import config as current_config
from core_memory.logger import EventLogger




# Настройка логирования
logger = logging.getLogger(__name__)

# Путь к SQLite БД черновиков
_DRAFTS_DB_PATH = current_config.RUNTIME_DIR / "memory" / "data" / "drafts.db"


class DraftManager:
    """
    Управление черновиками с SQLite-персистентностью.
    Черновики сохраняются между перезапусками сервиса.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or _DRAFTS_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.event_logger = EventLogger()
        self._init_db()

    def _init_db(self):
        """Создаёт таблицу drafts, если её ещё нет."""
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS drafts (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    target TEXT NOT NULL DEFAULT 'telegram',
                    source TEXT NOT NULL DEFAULT 'user',
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_drafts_status ON drafts(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_drafts_source ON drafts(source)
            """)
            conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        """Возвращает новое соединение с SQLite (thread-safe)."""
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _draft_from_row(self, row: sqlite3.Row) -> dict:
        """Конвертирует строку SQLite в dict."""
        return {
            "id": row["id"],
            "content": row["content"],
            "target": row["target"],
            "source": row["source"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def save_draft(self, content: str, target: str = "telegram", source: str = "user") -> str:
        """Сохранить черновик. Возвращает draft_id."""
        draft_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO drafts (id, content, target, source, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, 'pending', ?, ?)",
                (draft_id, content, target, source, now, now),
            )
            conn.commit()

        logger.info(f"Draft saved: {draft_id} (source={source}, target={target})")
        self.event_logger.log_event({
            "event_type": "draft_created",
            "draft_id": draft_id,
            "source": source,
            "target": target,
            "content_length": len(content),
        })

        return draft_id

    def save_draft_obj(self, draft) -> str:
        """Сохранить черновик из объекта Draft (обратная совместимость)."""
        return self.save_draft(
            content=draft.content,
            target=getattr(draft, 'target', 'telegram'),
            source=getattr(draft, 'source', 'user'),
        )

    def get_draft(self, draft_id: str) -> Optional[dict]:
        """Получить черновик по ID."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM drafts WHERE id = ?", (draft_id,)
            ).fetchone()
            if row:
                return self._draft_from_row(row)
        return None

    def get_pending_drafts(self) -> List[dict]:
        """Получить все черновики со статусом 'pending'."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM drafts WHERE status = 'pending' ORDER BY created_at DESC"
            ).fetchall()
            return [self._draft_from_row(r) for r in rows]

    def get_all_drafts(self, limit: int = 100) -> List[dict]:
        """Получить все черновики (с лимитом)."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM drafts ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [self._draft_from_row(r) for r in rows]

    def approve_draft(self, draft_id: str) -> bool:
        """Одобрить черновик."""
        now = datetime.now().isoformat()
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE drafts SET status = 'approved', updated_at = ? WHERE id = ? AND status = 'pending'",
                (now, draft_id),
            )
            conn.commit()
            if cursor.rowcount == 0:
                logger.warning(f"Draft {draft_id} not found or already processed")
                return False

        self.event_logger.log_event({
            "event_type": "draft_approved",
            "draft_id": draft_id,
        })
        logger.info(f"Draft approved: {draft_id}")
        return True

    def reject_draft(self, draft_id: str) -> bool:
        """Отклонить черновик."""
        now = datetime.now().isoformat()
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE drafts SET status = 'rejected', updated_at = ? WHERE id = ? AND status = 'pending'",
                (now, draft_id),
            )
            conn.commit()
            if cursor.rowcount == 0:
                logger.warning(f"Draft {draft_id} not found or already processed")
                return False

        self.event_logger.log_event({
            "event_type": "draft_rejected",
            "draft_id": draft_id,
        })
        logger.info(f"Draft rejected: {draft_id}")
        return True

    def get_stats(self) -> dict:
        """Получить статистику по черновикам."""
        with self._get_conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM drafts").fetchone()[0]
            pending = conn.execute("SELECT COUNT(*) FROM drafts WHERE status='pending'").fetchone()[0]
            approved = conn.execute("SELECT COUNT(*) FROM drafts WHERE status='approved'").fetchone()[0]
            rejected = conn.execute("SELECT COUNT(*) FROM drafts WHERE status='rejected'").fetchone()[0]

        return {
            "total": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
        }

    def close(self):
        """Закрыть все соединения (заглушка для совместимости)."""
        pass


# ── Telegram Bot ─────────────────────────────────────────────────

class TelegramBotStub:
    """
    Telegram Bot интеграция для российского рынка.
    Поддерживает отправку сообщений, inline режим и вебхуки.
    Черновики сохраняются в SQLite (персистентно).
    """

    def __init__(self):
        self.config = current_config
        self.event_logger = EventLogger()
        self.draft_manager = DraftManager()
        self.bot_token = getattr(self.config, 'TELEGRAM_BOT_TOKEN', None)
        self.api_url = "https://api.telegram.org/bot"
        self._client = httpx.AsyncClient(timeout=30.0)

    async def _call_api(self, method: str, data: dict = None) -> dict:
        """Вызов Telegram Bot API."""
        if not self.bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN не настроен, использую stub режим")
            return {"ok": True, "result": {}}

        try:
            url = f"{self.api_url}{self.bot_token}/{method}"
            response = await self._client.post(url, json=data) if data else await self._client.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Telegram API error: {e}")
            return {"ok": False, "error": str(e)}

    async def handle_message(self, message: str, user_id: str = "unknown") -> Dict:
        """
        Обработка сообщения от telegram.
        Возвращает ответ и создаёт черновик для публикации.
        Если настроен TelegramPresence — анализирует ключевые слова книги.
        """
        logger.info(f"Получено сообщение от {user_id}: {message}")

        # Сохраняем черновик в SQLite
        draft_id = self.draft_manager.save_draft(
            content=message,
            target="telegram",
            source="user",
        )

        self.event_logger.log_event({
            "event_type": "telegram_message_received",
            "user_id": user_id,
            "message_length": len(message),
            "draft_id": draft_id,
        })

        # Telegram Presence: анализ ключевых слов книги
        found_keywords = []
        try:
            from core.presence_manager import get_telegram_presence
            tp = get_telegram_presence()
            if tp:
                found_keywords = tp.process_message(message, chat_id="telegram", user_id=user_id)
                if found_keywords:
                    logger.info(f"telegram_presence_keywords_found count={len(found_keywords)} keywords={found_keywords[:5]}")
        except Exception as e:
            logger.warning(f"telegram_presence_error {e}")

        return {
            "status": "ok",
            "message": f"Ваше сообщение получено и сохранено как черновик (ID: {draft_id})",
            "draft_id": draft_id,
            "keywords_found": found_keywords,
        }

    async def send_notification(self, message: str, chat_id: Optional[str] = None) -> bool:
        """
        Отправка уведомления в Telegram через Bot API.
        """
        chat_id = chat_id or getattr(self.config, 'TELEGRAM_ADMIN_CHAT_ID', None)
        if not chat_id:
            logger.warning("TELEGRAM_ADMIN_CHAT_ID не настроен")
            return False

        logger.info(f"Отправка уведомления в чат {chat_id}: {message}")

        result = await self._call_api("sendMessage", {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
        })

        success = result.get("ok", False)

        self.event_logger.log_event({
            "event_type": "telegram_notification_sent",
            "chat_id": chat_id,
            "message_length": len(message),
            "success": success,
        })

        return success

    async def send_draft(self, draft_id: str, chat_id: Optional[str] = None) -> bool:
        """
        Отправка одобренного черновика в Telegram через Bot API (из SQLite).
        """
        draft = self.draft_manager.get_draft(draft_id)
        if not draft:
            logger.error(f"Draft {draft_id} not found")
            return False
        if draft["status"] != "approved":
            logger.error(f"Draft {draft_id} not approved (status={draft['status']})")
            return False

        chat_id = chat_id or getattr(self.config, 'TELEGRAM_ADMIN_CHAT_ID', None)
        if not chat_id:
            logger.warning("TELEGRAM_ADMIN_CHAT_ID не настроен")
            return False

        logger.info(f"Отправка черновика {draft_id} в Telegram")

        result = await self._call_api("sendMessage", {
            "chat_id": chat_id,
            "text": draft["content"],
            "parse_mode": "HTML",
        })

        success = result.get("ok", False)

        self.event_logger.log_event({
            "event_type": "telegram_draft_sent",
            "draft_id": draft_id,
            "content_length": len(draft["content"]),
            "success": success,
        })

        return success

    async def send_inline_query(self, query_id: str, results: List[dict]) -> bool:
        """
        Отправка ответа на inline запрос (для inline режима).
        """
        result = await self._call_api("answerInlineQuery", {
            "inline_query_id": query_id,
            "results": results,
            "cache_time": 300,
        })

        success = result.get("ok", False)
        logger.info(f"Inline query ответ: {success}")
        return success

    async def set_webhook(self, webhook_url: str) -> bool:
        """
        Установка вебхука для Telegram бота.
        """
        result = await self._call_api("setWebhook", {
            "url": webhook_url,
        })

        success = result.get("ok", False)
        logger.info(f"Webhook установлен: {success}")
        return success

    async def get_webhook_info(self) -> dict:
        """
        Получение информации о текущем вебхуке.
        """
        result = await self._call_api("getWebhookInfo")
        return result

    async def poll_visuals(self, character_id: str, hours: int = 24) -> dict:
        """Опрос читателей о визуальном образе персонажа.

        Отправляет сообщение читателям, собирает ответы в течение hours часов,
        агрегирует частотный анализ.
        Возвращает character_visual черновик.
        """
        logger.info(f"telegram_poll_visuals character={character_id} hours={hours}")

        question = f"📚 Как вы представляете персонажа «{character_id}»? Опишите его внешность в нескольких словах: одежду, цвет волос, глаз, телосложение."
        chat_id = getattr(self.config, 'TELEGRAM_ADMIN_CHAT_ID', None)

        if chat_id:
            await self.send_notification(f"📊 ЗАПУСК ОПРОСА: {character_id}\n\n{question}")

        poll_dir = Path(__file__).resolve().parent.parent / "OS_DATA" / "telegram_polls"
        poll_dir.mkdir(parents=True, exist_ok=True)
        poll_file = poll_dir / f"poll_{character_id}.json"

        return {
            "status": "poll_started",
            "character_id": character_id,
            "question": question,
            "hours": hours,
            "poll_file": str(poll_file),
        }

    async def aggregate_poll_results(self, character_id: str) -> dict | None:
        """Агрегировать результаты опроса читателей.

        Собирает ответы из черновиков (drafts), связанных с опросом.
        Выполняет частотный анализ слов.
        """
        from collections import Counter

        drafts = self.draft_manager.get_all_drafts(limit=200)
        poll_drafts = [d for d in drafts if character_id.lower() in d.get("content", "").lower()]

        if not poll_drafts:
            logger.info(f"telegram_poll_no_results character={character_id}")
            return None

        words: list[str] = []
        for d in poll_drafts:
            words.extend(d["content"].lower().split())

        stop_words = {"как", "вы", "его", "её", "он", "она", "и", "в", "на", "с", "по", "из", "у", "к", "о", "а", "но", "то", "что", "это", "для", "или", "не", "да", "от", "до", "за", "над", "под", "перед", "между", "когда", "где", "кто", "что", "такой", "ваш"}
        filtered = [w.strip(".,!?;:„“«»()") for w in words if w.strip(".,!?;:„“«»()") not in stop_words and len(w) > 2]
        freq = Counter(filtered)
        top_words = freq.most_common(15)

        return {
            "character_id": character_id,
            "total_responses": len(poll_drafts),
            "top_words": top_words,
            "suggested_visual": {
                "character_id": character_id,
                "clothing": "не определено",
                "color_palette": ["#808080"],
                "note": f"агрегировано из {len(poll_drafts)} ответов читателей",
            },
        }

    async def close(self):
        """Закрытие HTTP клиента и соединений с БД."""
        await self._client.aclose()
        self.draft_manager.close()
