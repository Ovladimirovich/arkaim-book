"""FeedbackStore — хранение обратной связи к ветвям исследований в SQLite."""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiosqlite

from core.database import get_db_manager

log = logging.getLogger("hermes.feedback_store")

DB_DIR = Path(__file__).resolve().parent.parent / "memory" / "data"
DB_PATH = DB_DIR / "explorations.db"
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


class FeedbackStore:
    """Хранит и извлекает обратную связь к ветвям исследований."""

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

    async def add_feedback(
        self,
        user_id: str,
        exploration_id: Optional[int],
        branch_rank: int,
        branch_type: str,
        branch_title: str,
        rating: int,
        comment: str = "",
    ) -> int:
        """Добавить обратную связь. Возвращает ID записи."""
        await self._ensure_db()
        now = datetime.now(tz=timezone.utc).isoformat()
        cursor = await self._conn.execute(
            """INSERT INTO exploration_feedback
               (user_id, exploration_id, branch_rank, branch_type, branch_title,
                rating, comment, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, exploration_id, branch_rank, branch_type, branch_title,
             rating, comment, now),
        )
        await self._conn.commit()
        return cursor.lastrowid

    async def get_feedback_for_exploration(
        self,
        exploration_id: int,
    ) -> list[dict]:
        """Получить всю обратную связь для конкретного исследования."""
        await self._ensure_db()
        cursor = await self._conn.execute(
            """SELECT id, user_id, branch_rank, branch_type, branch_title,
                      rating, comment, created_at
               FROM exploration_feedback
               WHERE exploration_id = ?
               ORDER BY created_at DESC""",
            (exploration_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_feedback_by_user(
        self,
        user_id: str,
        limit: int = 50,
    ) -> list[dict]:
        """Получить обратную связь пользователя."""
        await self._ensure_db()
        cursor = await self._conn.execute(
            """SELECT id, exploration_id, branch_rank, branch_type, branch_title,
                      rating, comment, created_at
               FROM exploration_feedback
               WHERE user_id = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (user_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_average_rating(
        self,
        branch_type: Optional[str] = None,
    ) -> dict:
        """Получить средний рейтинг по типу ветви."""
        await self._ensure_db()
        if branch_type:
            cursor = await self._conn.execute(
                """SELECT AVG(rating) as avg_rating, COUNT(*) as count
                   FROM exploration_feedback
                   WHERE branch_type = ? AND rating > 0""",
                (branch_type,),
            )
        else:
            cursor = await self._conn.execute(
                """SELECT AVG(rating) as avg_rating, COUNT(*) as count
                   FROM exploration_feedback
                   WHERE rating > 0"""
            )
        row = await cursor.fetchone()
        return {
            "average_rating": round(row["avg_rating"], 2) if row and row["avg_rating"] else 0.0,
            "total_ratings": row["count"] if row else 0,
            "branch_type": branch_type,
        }

    async def delete_feedback(self, feedback_id: int, user_id: str) -> bool:
        """Удалить обратную связь (только свою)."""
        await self._ensure_db()
        cursor = await self._conn.execute(
            "DELETE FROM exploration_feedback WHERE id = ? AND user_id = ?",
            (feedback_id, user_id),
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    async def count(self, user_id: Optional[str] = None) -> int:
        """Подсчитать количество отзывов."""
        await self._ensure_db()
        if user_id:
            cursor = await self._conn.execute(
                "SELECT COUNT(*) as cnt FROM exploration_feedback WHERE user_id = ?",
                (user_id,),
            )
        else:
            cursor = await self._conn.execute(
                "SELECT COUNT(*) as cnt FROM exploration_feedback",
            )
        row = await cursor.fetchone()
        return row["cnt"] if row else 0

    async def health(self) -> dict:
        """Статус хранилища."""
        await self._ensure_db()
        cursor = await self._conn.execute(
            "SELECT COUNT(*) as cnt FROM exploration_feedback"
        )
        row = await cursor.fetchone()
        return {
            "status": "ok",
            "type": "sqlite",
            "feedback_count": row["cnt"] if row else 0,
        }


# Синглтон
_store: Optional[FeedbackStore] = None


def get_feedback_store() -> FeedbackStore:
    global _store
    if _store is None:
        _store = FeedbackStore()
    return _store
