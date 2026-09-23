from datetime import datetime, timezone
from pathlib import Path
from functools import lru_cache

import aiosqlite

from core.database import get_db_manager


DB_DIR = Path(__file__).resolve().parent / "data"
DB_PATH = DB_DIR / "memory.db"
_RECENT_LIMIT = 20


@lru_cache(maxsize=1)
def get_memory_store() -> "MemoryStore":
    """Кэшированный экземпляр MemoryStore — один на всё приложение."""
    return MemoryStore()


class MemoryStore:
    def __init__(self, db_path: str | None = None):
        self._db_path = db_path or str(DB_PATH)
        self._conn: aiosqlite.Connection | None = None

    async def _ensure_db(self):
        # Проверяем что соединение активно
        if self._conn is not None:
            try:
                await self._conn.execute("SELECT 1")
                return
            except Exception:
                self._conn = None

        db_manager = get_db_manager()
        self._conn = await db_manager.get_connection(db_path=self._db_path)
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_id TEXT DEFAULT '',
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_memory_session ON conversations (session_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_memory_user ON conversations (user_id, created_at);
        """)

    async def retrieve(self, query: str, session_id: str | None = None) -> list[dict]:
        await self._ensure_db()
        if not session_id:
            return []
        cursor = await self._conn.execute(
            "SELECT role, content FROM conversations WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
            (session_id, _RECENT_LIMIT),
        )
        rows = await cursor.fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    async def store(self, messages: list[dict], response: str, session_id: str | None = None, user_id: str = ""):
        await self._ensure_db()
        now = datetime.now(tz=timezone.utc).isoformat()
        sid = session_id or "default"
        rows = [(sid, user_id, m["role"], m["content"], now) for m in messages[-4:]]
        rows.append((sid, user_id, "assistant", response if isinstance(response, str) else str(response), now))
        await self._conn.executemany(
            "INSERT INTO conversations (session_id, user_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)", rows
        )
        await self._conn.commit()

    async def health(self) -> dict:
        await self._ensure_db()
        cursor = await self._conn.execute("SELECT COUNT(*) as cnt FROM conversations")
        row = await cursor.fetchone()
        return {"status": "ok", "type": "sqlite", "conversations": row["cnt"] if row else 0}

    async def archive_old(self, days: int = 30) -> dict:
        """Переносит записи старше days дней в архивную таблицу."""
        await self._ensure_db()
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations_archive (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                archived_at TEXT NOT NULL
            );
        """)
        cursor = await self._conn.execute(
            "SELECT id, session_id, role, content, created_at FROM conversations "
            "WHERE created_at < datetime('now', ?)",
            (f"-{days} days",),
        )
        rows = await cursor.fetchall()
        if not rows:
            return {"archived": 0}

        now = datetime.now(tz=timezone.utc).isoformat()
        await self._conn.executemany(
            "INSERT INTO conversations_archive (session_id, role, content, created_at, archived_at) "
            "VALUES (?, ?, ?, ?, ?)",
            [(r["session_id"], r["role"], r["content"], r["created_at"], now) for r in rows],
        )
        ids = tuple(r["id"] for r in rows)
        placeholders = ",".join("?" * len(ids))
        await self._conn.execute(f"DELETE FROM conversations WHERE id IN ({placeholders})", ids)
        await self._conn.commit()
        return {"archived": len(rows)}

    async def close(self):
        """Сбросить ссылку на соединение (не закрывать — DatabaseManager управляет жизненным циклом)."""
        self._conn = None

    # ── User history ──────────────────────────────────

    async def get_user_history(self, user_id: str, limit: int = 50) -> list[dict]:
        """Получить историю вопросов пользователя."""
        await self._ensure_db()
        if not user_id:
            return []
        cursor = await self._conn.execute(
            "SELECT id, session_id, role, content, created_at "
            "FROM conversations WHERE user_id = ? AND role = 'user' "
            "ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )
        rows = await cursor.fetchall()
        return [{"id": r["id"], "session_id": r["session_id"], "content": r["content"],
                 "created_at": r["created_at"]} for r in rows]

    async def get_user_history_full(self, user_id: str, session_id: str | None = None, limit: int = 100) -> list[dict]:
        """Получить полную историю (user + assistant) для пользователя."""
        await self._ensure_db()
        if not user_id:
            return []
        if session_id:
            cursor = await self._conn.execute(
                "SELECT role, content, created_at FROM conversations "
                "WHERE user_id = ? AND session_id = ? ORDER BY created_at ASC LIMIT ?",
                (user_id, session_id, limit),
            )
        else:
            cursor = await self._conn.execute(
                "SELECT role, content, created_at FROM conversations "
                "WHERE user_id = ? ORDER BY created_at ASC LIMIT ?",
                (user_id, limit),
            )
        rows = await cursor.fetchall()
        return [{"role": r["role"], "content": r["content"], "created_at": r["created_at"]} for r in rows]

    async def get_user_sessions(self, user_id: str) -> list[str]:
        """Получить список session_id для пользователя."""
        await self._ensure_db()
        if not user_id:
            return []
        cursor = await self._conn.execute(
            "SELECT session_id FROM conversations WHERE user_id = ? GROUP BY session_id ORDER BY MAX(created_at) DESC",
            (user_id,),
        )
        return [r["session_id"] for r in await cursor.fetchall()]

    async def get_user_stats(self, user_id: str) -> dict:
        """Статистика пользователя: количество вопросов, сессий, последняя активность."""
        await self._ensure_db()
        if not user_id:
            return {"questions": 0, "sessions": 0, "last_active": None}
        cursor = await self._conn.execute(
            "SELECT COUNT(*) as cnt FROM conversations WHERE user_id = ? AND role = 'user'",
            (user_id,),
        )
        questions = (await cursor.fetchone())["cnt"]
        cursor = await self._conn.execute(
            "SELECT COUNT(DISTINCT session_id) as cnt FROM conversations WHERE user_id = ?",
            (user_id,),
        )
        sessions = (await cursor.fetchone())["cnt"]
        cursor = await self._conn.execute(
            "SELECT MAX(created_at) as last FROM conversations WHERE user_id = ?",
            (user_id,),
        )
        last = (await cursor.fetchone())["last"]
        return {"questions": questions, "sessions": sessions, "last_active": last}
