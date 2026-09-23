from datetime import datetime, timezone
from pathlib import Path

import aiosqlite


DB_DIR = Path(__file__).resolve().parent / "data"
DB_PATH = DB_DIR / "memory.db"
_RECENT_LIMIT = 20


class MemoryStore:
    def __init__(self, db_path: str | None = None):
        self._db_path = db_path or str(DB_PATH)
        self._conn: aiosqlite.Connection | None = None

    async def _ensure_db(self):
        if self._conn is not None:
            return
        DB_DIR.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_memory_session ON conversations (session_id, created_at);
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

    async def store(self, messages: list[dict], response: str, session_id: str | None = None):
        await self._ensure_db()
        now = datetime.now(tz=timezone.utc).isoformat()
        sid = session_id or "default"
        rows = [(sid, m["role"], m["content"], now) for m in messages[-4:]]
        rows.append((sid, "assistant", response if isinstance(response, str) else str(response), now))
        await self._conn.executemany(
            "INSERT INTO conversations (session_id, role, content, created_at) VALUES (?, ?, ?, ?)", rows
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
        datetime.now(tz=timezone.utc).isoformat()
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
        if self._conn:
            await self._conn.close()
            self._conn = None
