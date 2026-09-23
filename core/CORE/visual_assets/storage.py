"""Visual Assets — хранение метаданных (SQLite) и файлов (filesystem)."""
from __future__ import annotations

import json
import os
import time
import uuid
import logging
from pathlib import Path

from .schemas import VisualAsset, AssetType, AssetStatus, GenerationParams

log = logging.getLogger("visual_assets.storage")

# Корневая директория для файлов
_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "visual_assets"
_DB_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
_DB_PATH = _DB_DIR / "visual_assets.db"
_MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


class AssetStorage:
    """Хранение ассетов: метаданные в SQLite, файлы на диске."""

    def __init__(self, db_path: str | Path | None = None):
        self._db_path = Path(db_path) if db_path else _DB_PATH
        self._conn = None
        self._ensure_dirs()

    def _ensure_dirs(self):
        for subdir in ("images", "thumbnails", "videos"):
            (_DATA_DIR / subdir).mkdir(parents=True, exist_ok=True)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    async def _get_conn(self):
        """Получить соединение с SQLite (ленивая инициализация)."""
        if self._conn is None:
            import aiosqlite
            self._conn = await aiosqlite.connect(str(self._db_path))
            self._conn.row_factory = aiosqlite.Row
            await self._conn.execute("PRAGMA journal_mode = WAL")
            await self._init_table()
        return self._conn

    async def _init_table(self):
        """Создать таблицу если не существует."""
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS visual_assets (
                asset_id TEXT PRIMARY KEY,
                asset_type TEXT NOT NULL,
                book_id TEXT DEFAULT 'arkaim',
                chapter INTEGER NOT NULL,
                scene_id TEXT NOT NULL,
                title TEXT DEFAULT '',
                mood TEXT DEFAULT 'neutral',
                style TEXT DEFAULT 'cinematic_fantasy',
                status TEXT DEFAULT 'pending',
                file_path TEXT,
                thumbnail_path TEXT,
                prompt_used TEXT DEFAULT '',
                generation_params TEXT DEFAULT '{}',
                reader_id TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_assets_chapter ON visual_assets(chapter)
        """)
        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_assets_scene ON visual_assets(scene_id)
        """)
        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_assets_type ON visual_assets(asset_type)
        """)
        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_assets_status ON visual_assets(status)
        """)
        await self._conn.commit()

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None

    # ── CRUD ──────────────────────────────────────────────

    async def save(self, asset: VisualAsset) -> VisualAsset:
        """Сохранить ассет."""
        if not asset.created_at:
            asset.created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        asset.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ")

        conn = await self._get_conn()
        await conn.execute(
            """INSERT OR REPLACE INTO visual_assets
               (asset_id, asset_type, book_id, chapter, scene_id, title, mood, style,
                status, file_path, thumbnail_path, prompt_used, generation_params,
                reader_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                asset.asset_id, asset.asset_type.value, asset.book_id,
                asset.chapter, asset.scene_id, asset.title, asset.mood, asset.style,
                asset.status.value, asset.file_path, asset.thumbnail_path,
                asset.prompt_used, json.dumps(asset.generation.model_dump()),
                asset.reader_id, asset.created_at, asset.updated_at,
            ),
        )
        await conn.commit()
        return asset

    async def get(self, asset_id: str) -> VisualAsset | None:
        conn = await self._get_conn()
        cursor = await conn.execute(
            "SELECT * FROM visual_assets WHERE asset_id = ?", (asset_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return self._row_to_asset(row)

    async def list_assets(
        self,
        chapter: int | None = None,
        asset_type: AssetType | None = None,
        status: AssetStatus | None = None,
        scene_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[VisualAsset]:
        conn = await self._get_conn()
        query = "SELECT * FROM visual_assets WHERE 1=1"
        params = []
        if chapter is not None:
            query += " AND chapter = ?"
            params.append(chapter)
        if asset_type is not None:
            query += " AND asset_type = ?"
            params.append(asset_type.value)
        if status is not None:
            query += " AND status = ?"
            params.append(status.value)
        if scene_id is not None:
            query += " AND scene_id = ?"
            params.append(scene_id)
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()
        return [self._row_to_asset(r) for r in rows]

    async def delete(self, asset_id: str) -> bool:
        asset = await self.get(asset_id)
        if not asset:
            return False
        # Удалить файлы
        if asset.file_path:
            fpath = _DATA_DIR / asset.file_path
            if fpath.exists():
                fpath.unlink()
        if asset.thumbnail_path:
            tpath = _DATA_DIR / asset.thumbnail_path
            if tpath.exists():
                tpath.unlink()
        # Удалить метаданные
        conn = await self._get_conn()
        await conn.execute("DELETE FROM visual_assets WHERE asset_id = ?", (asset_id,))
        await conn.commit()
        return True

    def get_file_path(self, asset: VisualAsset) -> Path | None:
        if asset.file_path:
            fpath = _DATA_DIR / asset.file_path
            return fpath if fpath.exists() else None
        return None

    def get_thumbnail_path(self, asset: VisualAsset) -> Path | None:
        if asset.thumbnail_path:
            tpath = _DATA_DIR / asset.thumbnail_path
            return tpath if tpath.exists() else None
        return None

    def save_file(self, asset_id: str, asset_type: AssetType, data: bytes) -> str:
        """Сохранить файл ассета, вернуть относительный путь."""
        if asset_type == AssetType.IMAGE:
            if data[:3] == b'\xff\xd8\xff':
                ext = "jpg"
            elif data[:4] == b'\x89PNG':
                ext = "png"
            elif data[:4] == b'RIFF':
                ext = "webp"
            else:
                ext = "png"
            subdir = "images"
        else:
            ext = "mp4"
            subdir = "videos"
        filename = f"{asset_id}.{ext}"
        rel_path = f"{subdir}/{filename}"
        full_path = _DATA_DIR / rel_path
        full_path.write_bytes(data)
        return rel_path

    def save_thumbnail(self, asset_id: str, data: bytes) -> str:
        """Сохранить thumbnail, вернуть относительный путь."""
        filename = f"{asset_id}_thumb.png"
        rel_path = f"thumbnails/{filename}"
        full_path = _DATA_DIR / rel_path
        full_path.write_bytes(data)
        return rel_path

    def _row_to_asset(self, row) -> VisualAsset:
        d = dict(row)
        gen_params = json.loads(d.get("generation_params") or "{}")
        return VisualAsset(
            asset_id=d["asset_id"],
            asset_type=AssetType(d["asset_type"]),
            book_id=d.get("book_id", "arkaim"),
            chapter=d["chapter"],
            scene_id=d["scene_id"],
            title=d.get("title", ""),
            mood=d.get("mood", "neutral"),
            style=d.get("style", "cinematic_fantasy"),
            status=AssetStatus(d.get("status", "pending")),
            file_path=d.get("file_path"),
            thumbnail_path=d.get("thumbnail_path"),
            prompt_used=d.get("prompt_used", ""),
            generation=GenerationParams(**gen_params) if gen_params else GenerationParams(),
            reader_id=d.get("reader_id"),
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
        )


def generate_asset_id() -> str:
    ts = time.strftime("%Y%m%d_%H%M%S")
    short = uuid.uuid4().hex[:6]
    return f"asset_{ts}_{short}"
