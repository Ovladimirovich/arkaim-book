"""ExplorationStore — хранение истории исследований World Explorer в SQLite."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiosqlite

from core.database import get_db_manager

log = logging.getLogger("hermes.exploration_store")

DB_DIR = Path(__file__).resolve().parent.parent / "memory" / "data"
DB_PATH = DB_DIR / "explorations.db"
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


class ExplorationStore:
    """Хранит и извлекает историю исследований World Explorer."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = db_path or str(DB_PATH)
        self._conn: Optional[aiosqlite.Connection] = None

    async def _ensure_db(self) -> None:
        if self._conn is not None:
            try:
                await self._conn.execute("SELECT 1")
                return
            except Exception:
                self._conn = None

        db_manager = get_db_manager()
        self._conn = await db_manager.get_connection(
            db_path=self._db_path,
            migrations_dir=MIGRATIONS_DIR,
        )

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
        self._conn = None

    async def save(
        self,
        user_id: str,
        prompt: str,
        epoch: Optional[str],
        branch_count: int,
        hypothesis_id: Optional[str],
        hypothesis_title: Optional[str],
        result_json: str,
        summary: str,
        overall_score: float,
        branch_count_actual: int,
        duration_ms: float,
    ) -> int:
        """Сохранить результат исследования. Возвращает ID записи."""
        await self._ensure_db()
        now = datetime.now(tz=timezone.utc).isoformat()
        cursor = await self._conn.execute(
            """INSERT INTO exploration_history
               (user_id, prompt, epoch, branch_count, hypothesis_id, hypothesis_title,
                result_json, summary, overall_score, branch_count_actual, duration_ms, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, prompt, epoch, branch_count, hypothesis_id, hypothesis_title,
             result_json, summary, overall_score, branch_count_actual, duration_ms, now),
        )
        await self._conn.commit()
        return cursor.lastrowid

    async def list_by_user(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """Получить список исследований пользователя."""
        await self._ensure_db()
        cursor = await self._conn.execute(
            """SELECT id, prompt, epoch, hypothesis_title, summary,
                      overall_score, branch_count_actual, duration_ms, created_at
               FROM exploration_history
               WHERE user_id = ?
               ORDER BY created_at DESC
               LIMIT ? OFFSET ?""",
            (user_id, limit, offset),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get(self, exploration_id: int) -> Optional[dict]:
        """Получить конкретное исследование с полным result_json."""
        await self._ensure_db()
        cursor = await self._conn.execute(
            "SELECT * FROM exploration_history WHERE id = ?",
            (exploration_id,),
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None

    async def delete(self, exploration_id: int, user_id: str) -> bool:
        """Удалить исследование (только своё)."""
        await self._ensure_db()
        cursor = await self._conn.execute(
            "DELETE FROM exploration_history WHERE id = ? AND user_id = ?",
            (exploration_id, user_id),
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    async def count(self, user_id: Optional[str] = None) -> int:
        """Подсчитать количество исследований."""
        await self._ensure_db()
        if user_id:
            cursor = await self._conn.execute(
                "SELECT COUNT(*) as cnt FROM exploration_history WHERE user_id = ?",
                (user_id,),
            )
        else:
            cursor = await self._conn.execute(
                "SELECT COUNT(*) as cnt FROM exploration_history",
            )
        row = await cursor.fetchone()
        return row["cnt"] if row else 0

    async def health(self) -> dict:
        """Статус хранилища."""
        await self._ensure_db()
        cursor = await self._conn.execute(
            "SELECT COUNT(*) as cnt FROM exploration_history"
        )
        row = await cursor.fetchone()
        return {
            "status": "ok",
            "type": "sqlite",
            "explorations": row["cnt"] if row else 0,
        }


# Синглтон
_store: Optional[ExplorationStore] = None


def get_exploration_store() -> ExplorationStore:
    global _store
    if _store is None:
        _store = ExplorationStore()
    return _store
