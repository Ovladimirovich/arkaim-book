"""Visual Assets — хранение метаданных (SQLite) и файлов (filesystem)."""

from __future__ import annotations

import json
import time
import uuid
import logging
from pathlib import Path

from .schemas import VisualAsset, AssetType, AssetStatus, GenerationParams

log = logging.getLogger("visual_assets.storage")

# Корневая директория для файлов
_DATA_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent / "data" / "visual_assets"
)
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
        # Миграция (Этап 2): текст ошибки задания должен переживать хранение,
        # иначе статус failed читается без причины. ADD COLUMN идемпотентен.
        try:
            await self._conn.execute("ALTER TABLE visual_assets ADD COLUMN error TEXT")
        except Exception as exc:  # duplicate column — уже добавлена
            if "duplicate column" not in str(exc).lower():
                raise
        # Миграция: статус эксперимента (управляемая история экспериментов Studio).
        try:
            await self._conn.execute(
                "ALTER TABLE visual_assets ADD COLUMN experiment_status TEXT"
            )
        except Exception as exc:  # duplicate column — уже добавлена
            if "duplicate column" not in str(exc).lower():
                raise
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
        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_assets_experiment ON visual_assets(experiment_status)
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
                reader_id, created_at, updated_at, error, experiment_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                asset.asset_id,
                asset.asset_type.value,
                asset.book_id,
                asset.chapter,
                asset.scene_id,
                asset.title,
                asset.mood,
                asset.style,
                asset.status.value,
                asset.file_path,
                asset.thumbnail_path,
                asset.prompt_used,
                json.dumps(asset.generation.model_dump()),
                asset.reader_id,
                asset.created_at,
                asset.updated_at,
                asset.error,
                asset.experiment_status,
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

    async def set_experiment_status(self, asset_id: str, status: str) -> bool:
        """Установить статус эксперимента (experimental/candidate/approved/used/archived)."""
        conn = await self._get_conn()
        cursor = await conn.execute(
            "UPDATE visual_assets SET experiment_status = ?, updated_at = ? WHERE asset_id = ?",
            (status, time.strftime("%Y-%m-%dT%H:%M:%SZ"), asset_id),
        )
        await conn.commit()
        return cursor.rowcount > 0

    async def list_experiments(
        self,
        chapter: int,
        scene_id: str,
        status: str | None = None,
        shot_id: str | None = None,
        backend: str | None = None,
        older_than_days: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[VisualAsset]:
        """Список экспериментов сцены с фильтрами и пагинацией."""
        conn = await self._get_conn()
        query = "SELECT * FROM visual_assets WHERE chapter = ? AND scene_id = ? AND experiment_status IS NOT NULL"
        params: list = [chapter, scene_id]
        if status:
            query += " AND experiment_status = ?"
            params.append(status)
        if shot_id:
            query += " AND json_extract(generation_params, '$.shot_id') = ?"
            params.append(shot_id)
        if backend:
            query += " AND json_extract(generation_params, '$.backend') = ?"
            params.append(backend)
        if older_than_days is not None:
            cutoff = time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - older_than_days * 86400)
            )
            query += " AND created_at < ?"
            params.append(cutoff)
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()
        return [self._row_to_asset(r) for r in rows]

    async def count_experiments(
        self,
        chapter: int,
        scene_id: str,
        status: str | None = None,
        shot_id: str | None = None,
        backend: str | None = None,
        older_than_days: int | None = None,
    ) -> int:
        """Количество экспериментов сцены (для пагинации)."""
        conn = await self._get_conn()
        query = "SELECT COUNT(*) FROM visual_assets WHERE chapter = ? AND scene_id = ? AND experiment_status IS NOT NULL"
        params: list = [chapter, scene_id]
        if status:
            query += " AND experiment_status = ?"
            params.append(status)
        if shot_id:
            query += " AND json_extract(generation_params, '$.shot_id') = ?"
            params.append(shot_id)
        if backend:
            query += " AND json_extract(generation_params, '$.backend') = ?"
            params.append(backend)
        if older_than_days is not None:
            cutoff = time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - older_than_days * 86400)
            )
            query += " AND created_at < ?"
            params.append(cutoff)
        cursor = await conn.execute(query, params)
        row = await cursor.fetchone()
        return row[0] if row else 0

    async def list_experiment_groups(self, chapter: int, scene_id: str) -> list[dict]:
        """Группировка экспериментов по шотам (для отображения Shot #N → M вариантов)."""
        conn = await self._get_conn()
        cursor = await conn.execute(
            """
            SELECT
                COALESCE(json_extract(generation_params, '$.shot_id'), '') as shot_id,
                experiment_status,
                COUNT(*) as cnt
            FROM visual_assets
            WHERE chapter = ? AND scene_id = ? AND experiment_status IS NOT NULL
            GROUP BY shot_id, experiment_status
        """,
            (chapter, scene_id),
        )
        rows = await cursor.fetchall()
        groups: dict[str, dict] = {}
        for r in rows:
            sid = r[0] or ""
            if sid not in groups:
                groups[sid] = {"shot_id": sid or None, "total": 0, "by_status": {}}
            groups[sid]["total"] += r[2]
            groups[sid]["by_status"][r[1]] = r[2]
        return list(groups.values())

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
            if data[:3] == b"\xff\xd8\xff":
                ext = "jpg"
            elif data[:4] == b"\x89PNG":
                ext = "png"
            elif data[:4] == b"RIFF":
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
            generation=GenerationParams(**gen_params)
            if gen_params
            else GenerationParams(),
            reader_id=d.get("reader_id"),
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
            error=d.get("error"),
            experiment_status=d.get("experiment_status"),
        )


def generate_asset_id() -> str:
    ts = time.strftime("%Y%m%d_%H%M%S")
    short = uuid.uuid4().hex[:6]
    return f"asset_{ts}_{short}"
