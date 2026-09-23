"""Репозиторий API-ключей — только доступ к данным."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import aiosqlite

from core.repositories.user_repo import UserRepository


class ApiKeyRepository:
    def __init__(self, user_repo: UserRepository | None = None):
        self._user_repo = user_repo or UserRepository()
        self._conn: aiosqlite.Connection | None = None

    async def _ensure_db(self):
        if self._conn is not None:
            return
        await self._user_repo._ensure_db()
        self._conn = self._user_repo._conn

    async def create(self, user_id: str, key_prefix: str, key_hash: str, name: str | None = None) -> str:
        await self._ensure_db()
        key_id = uuid.uuid4().hex
        now = datetime.now(tz=timezone.utc).isoformat()
        await self._conn.execute(
            "INSERT INTO api_keys (id, user_id, key_prefix, key_hash, name, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (key_id, user_id, key_prefix, key_hash, name, now),
        )
        await self._conn.commit()
        return key_id

    async def list_by_user(self, user_id: str) -> list[dict]:
        await self._ensure_db()
        cursor = await self._conn.execute(
            "SELECT id, user_id, key_prefix, key_hash, name, last_used_at, is_active, created_at "
            "FROM api_keys WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        return [dict(row) for row in await cursor.fetchall()]

    async def get_by_hash(self, key_hash: str) -> dict | None:
        await self._ensure_db()
        cursor = await self._conn.execute(
            "SELECT * FROM api_keys WHERE key_hash = ?", (key_hash,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def revoke(self, key_id: str) -> bool:
        await self._ensure_db()
        cursor = await self._conn.execute(
            "UPDATE api_keys SET is_active = 0 WHERE id = ?", (key_id,),
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    async def touch(self, key_id: str):
        await self._ensure_db()
        now = datetime.now(tz=timezone.utc).isoformat()
        await self._conn.execute(
            "UPDATE api_keys SET last_used_at = ? WHERE id = ?", (now, key_id),
        )
        await self._conn.commit()
