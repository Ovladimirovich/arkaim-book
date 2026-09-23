import json
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite


DB_DIR = Path(__file__).resolve().parent / "data"
DB_PATH = DB_DIR / "leads.db"


class LeadStore:
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
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL DEFAULT '',
                user_text TEXT NOT NULL,
                intent TEXT NOT NULL DEFAULT '',
                metadata TEXT NOT NULL DEFAULT '{}',
                contacted INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_leads_session ON leads (session_id);
        """)

    async def store_lead(self, session_id: str, user_id: str, user_text: str, intent: str, metadata: dict | None = None):
        await self._ensure_db()
        now = datetime.now(tz=timezone.utc).isoformat()
        await self._conn.execute(
            "INSERT INTO leads (session_id, user_id, user_text, intent, metadata, contacted, created_at) VALUES (?, ?, ?, ?, ?, 0, ?)",
            (session_id, user_id, user_text, intent, json.dumps(metadata or {}), now),
        )
        await self._conn.commit()

    async def get_leads(self, limit: int = 50) -> list[dict]:
        await self._ensure_db()
        cursor = await self._conn.execute("SELECT * FROM leads ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(r) for r in await cursor.fetchall()]

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None
