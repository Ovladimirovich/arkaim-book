"""Story Store — SQLite persistence for generated stories."""

import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

log = logging.getLogger("hermes.narrative.story_store")

DB_PATH = Path("runtime/arkaim.db")


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create story_history table if not exists."""
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS story_history (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                word_count INTEGER DEFAULT 0,
                prompt TEXT DEFAULT '',
                constraints TEXT DEFAULT '{}',
                validation TEXT DEFAULT '{}',
                score REAL DEFAULT 0.0,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def save_story(story: dict):
    """Save a generated story to the database."""
    conn = _get_conn()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO story_history
               (id, text, word_count, prompt, constraints, validation, score, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                story["id"],
                story["text"],
                story.get("word_count", 0),
                story.get("prompt", ""),
                json.dumps(story.get("constraints", {}), ensure_ascii=False, default=str),
                json.dumps(story.get("validation", {}), ensure_ascii=False, default=str),
                story.get("validation", {}).get("score", 0.0),
                story.get("created_at", datetime.now(tz=timezone.utc).isoformat()),
            ),
        )
        conn.commit()
        log.info("story_saved id=%s", story["id"])
    finally:
        conn.close()


def get_story(story_id: str) -> Optional[dict]:
    """Get a single story by ID."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM story_history WHERE id = ?", (story_id,)).fetchone()
        if row:
            return _row_to_dict(row)
        return None
    finally:
        conn.close()


def get_stories(limit: int = 20, offset: int = 0) -> list[dict]:
    """Get recent stories."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM story_history ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def delete_story(story_id: str) -> bool:
    """Delete a story."""
    conn = _get_conn()
    try:
        cursor = conn.execute("DELETE FROM story_history WHERE id = ?", (story_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def count_stories() -> int:
    """Count total stories."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT COUNT(*) as cnt FROM story_history").fetchone()
        return row["cnt"] if row else 0
    finally:
        conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a database row to a dictionary."""
    d = dict(row)
    # Parse JSON fields
    for field in ("constraints", "validation"):
        if d.get(field) and isinstance(d[field], str):
            try:
                d[field] = json.loads(d[field])
            except json.JSONDecodeError:
                d[field] = {}
    return d


# Initialize on import
init_db()
