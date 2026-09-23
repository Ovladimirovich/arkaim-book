"""Репозиторий пользователей — только доступ к данным."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from core.config import settings
from core.database import get_db_manager


DB_PATH = Path(settings.AUTH_DB_PATH)
MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "auth" / "migrations"


class UserRepository:
    def __init__(self):
        self._conn: aiosqlite.Connection | None = None

    async def _ensure_db(self):
        if self._conn is not None:
            return
        self._conn = await get_db_manager().get_connection(
            db_path=DB_PATH,
            migrations_dir=MIGRATIONS_DIR,
        )

    async def get_by_provider(self, provider: str, provider_user_id: str) -> dict | None:
        await self._ensure_db()
        cursor = await self._conn.execute(
            "SELECT * FROM users WHERE provider = ? AND provider_user_id = ?",
            (provider, provider_user_id),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_by_id(self, user_id: str) -> dict | None:
        await self._ensure_db()
        cursor = await self._conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def upsert(
        self,
        provider: str,
        provider_user_id: str,
        username: str | None = None,
        display_name: str | None = None,
        role: str = "reader",
    ) -> dict:
        await self._ensure_db()
        now = datetime.now(tz=timezone.utc).isoformat()
        existing = await self.get_by_provider(provider, provider_user_id)
        if existing:
            await self._conn.execute(
                "UPDATE users SET username = COALESCE(?, username), display_name = COALESCE(?, display_name), "
                "role = ?, updated_at = ? WHERE id = ?",
                (username, display_name, role, now, existing["id"]),
            )
            await self._conn.commit()
            return await self.get_by_id(existing["id"])
        user_id = uuid.uuid4().hex
        await self._conn.execute(
            "INSERT INTO users (id, provider, provider_user_id, username, display_name, role, is_active, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)",
            (user_id, provider, provider_user_id, username, display_name, role, now, now),
        )
        await self._conn.commit()
        return await self.get_by_id(user_id)

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[dict]:
        await self._ensure_db()
        cursor = await self._conn.execute(
            "SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return [dict(row) for row in await cursor.fetchall()]

    async def count_by_role(self) -> dict[str, int]:
        await self._ensure_db()
        cursor = await self._conn.execute(
            "SELECT role, COUNT(*) as cnt FROM users GROUP BY role"
        )
        return {row["role"]: row["cnt"] for row in await cursor.fetchall()}

    async def set_role(self, user_id: str, role: str) -> bool:
        await self._ensure_db()
        now = datetime.now(tz=timezone.utc).isoformat()
        cursor = await self._conn.execute(
            "UPDATE users SET role = ?, updated_at = ? WHERE id = ?",
            (role, now, user_id),
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    async def set_active(self, user_id: str, is_active: bool) -> bool:
        await self._ensure_db()
        now = datetime.now(tz=timezone.utc).isoformat()
        cursor = await self._conn.execute(
            "UPDATE users SET is_active = ?, updated_at = ? WHERE id = ?",
            (1 if is_active else 0, now, user_id),
        )
        await self._conn.commit()
        return cursor.rowcount > 0
