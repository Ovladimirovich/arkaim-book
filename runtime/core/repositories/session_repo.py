"""Репозиторий сессий — только доступ к данным."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import aiosqlite

from core.repositories.user_repo import UserRepository


class SessionRepository:
    def __init__(self, user_repo: UserRepository | None = None):
        self._user_repo = user_repo or UserRepository()
        self._conn: aiosqlite.Connection | None = None

    async def _ensure_db(self):
        if self._conn is not None:
            return
        # Используем то же соединение что и UserRepo (auth.db)
        await self._user_repo._ensure_db()
        self._conn = self._user_repo._conn

    async def save(self, session_id: str, user_id: str, token_hash: str, expires_at: datetime):
        await self._ensure_db()
        now = datetime.now(tz=timezone.utc).isoformat()
        await self._conn.execute(
            "INSERT OR REPLACE INTO sessions (id, user_id, token_hash, expires_at, created_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, user_id, token_hash, expires_at.isoformat(), now),
        )
        await self._conn.commit()

    async def get(self, session_id: str) -> dict | None:
        await self._ensure_db()
        cursor = await self._conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def delete(self, session_id: str) -> bool:
        await self._ensure_db()
        cursor = await self._conn.execute(
            "DELETE FROM sessions WHERE id = ?", (session_id,),
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    async def delete_expired(self) -> int:
        """Удалить все истёкшие сессии."""
        await self._ensure_db()
        now = datetime.now(tz=timezone.utc).isoformat()
        cursor = await self._conn.execute(
            "DELETE FROM sessions WHERE expires_at < ?", (now,),
        )
        await self._conn.commit()
        return cursor.rowcount
