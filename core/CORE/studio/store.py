"""StudioStore — SQLite persistence for Studio sessions (Phase 1B).

Следует паттерну FilmProjectStore:
  - aiosqlite async
  - WAL mode
  - CREATE TABLE IF NOT EXISTS
  - Использует существующую SQLite (НЕ отдельную БД)

Таблицы: studio_sessions, studio_messages, studio_versions, studio_references.
"""

from __future__ import annotations

import json
import time
import uuid
import logging
from pathlib import Path

from .session_models import (
    StudioSession,
    StudioSessionStatus,
    StudioMessage,
    StudioMessageRole,
    StudioVersion,
    UserModification,
    ReferenceAsset,
)
from .scenario_schemas import VideoScenario
from .art_direction import FilmArtDirection
from media_plan.schemas import MediaPlan

log = logging.getLogger("studio.store")

_DB_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
_DB_PATH = _DB_DIR / "studio.db"


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _row_get(r, key: str, default=None):
    """Безопасное чтение колонки: старые строки/БД без миграции не падают."""
    try:
        return r[key]
    except (IndexError, KeyError):
        return default


class StudioStore:
    """Хранение Studio-сессий в SQLite (existing persistence pattern)."""

    def __init__(self, db_path: str | Path | None = None):
        self._db_path = Path(db_path) if db_path else _DB_PATH
        self._conn = None

    async def _get_conn(self):
        if self._conn is None:
            import aiosqlite

            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = await aiosqlite.connect(str(self._db_path))
            self._conn.row_factory = aiosqlite.Row
            await self._conn.execute("PRAGMA journal_mode = WAL")
            await self._init_tables()
        return self._conn

    async def _init_tables(self):
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS studio_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                chapter INTEGER DEFAULT 0,
                scene_id TEXT DEFAULT '',
                context_type TEXT DEFAULT 'scene',
                active_version_id TEXT,
                status TEXT DEFAULT 'draft',
                reference_assets TEXT DEFAULT '[]',
                created_at TEXT,
                updated_at TEXT,
                finalized_at TEXT
            );

            CREATE TABLE IF NOT EXISTS studio_messages (
                message_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL DEFAULT '',
                created_version_id TEXT,
                created_at TEXT,
                FOREIGN KEY (session_id) REFERENCES studio_sessions(session_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS studio_versions (
                version_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                version_number INTEGER NOT NULL DEFAULT 0,
                image_description_json TEXT,
                video_description_json TEXT,
                video_scenario_json TEXT,
                parent_version_id TEXT,
                derivation TEXT DEFAULT 'initial',
                user_modifications_json TEXT DEFAULT '[]',
                is_active INTEGER DEFAULT 0,
                is_final INTEGER DEFAULT 0,
                created_by TEXT DEFAULT 'system',
                created_at TEXT,
                note TEXT DEFAULT '',
                FOREIGN KEY (session_id) REFERENCES studio_sessions(session_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS studio_references (
                asset_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                description TEXT DEFAULT '',
                source_type TEXT DEFAULT 'user_reference',
                created_at TEXT,
                FOREIGN KEY (session_id) REFERENCES studio_sessions(session_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS studio_art_direction (
                ad_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS studio_prepared_updates (
                prepared_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                shot_id TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (session_id) REFERENCES studio_sessions(session_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS studio_continuity_decisions (
                decision_id TEXT PRIMARY KEY,
                session_id TEXT DEFAULT '',
                link_key TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT,
                updated_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_studio_sessions_user ON studio_sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_studio_sessions_status ON studio_sessions(status);
            CREATE INDEX IF NOT EXISTS idx_studio_messages_session ON studio_messages(session_id);
            CREATE INDEX IF NOT EXISTS idx_studio_versions_session ON studio_versions(session_id);
            CREATE INDEX IF NOT EXISTS idx_studio_references_session ON studio_references(session_id);
            CREATE INDEX IF NOT EXISTS idx_studio_prepared_session ON studio_prepared_updates(session_id);
            CREATE INDEX IF NOT EXISTS idx_studio_prepared_shot ON studio_prepared_updates(session_id, shot_id);
            CREATE INDEX IF NOT EXISTS idx_studio_continuity_link ON studio_continuity_decisions(link_key);
        """)
        # Миграция: утверждённый кадр сцены (Studio: промпт → изображение → видео).
        try:
            await self._conn.execute(
                "ALTER TABLE studio_sessions ADD COLUMN approved_image_asset_id TEXT"
            )
        except Exception:
            pass  # колонка уже существует (повторный вызов _init_tables)
        await self._conn.commit()

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None

    # ── Sessions ─────────────────────────────────────────────────

    async def create_session(
        self,
        user_id: str,
        title: str,
        chapter: int = 0,
        scene_id: str = "",
        context_type: str = "scene",
    ) -> StudioSession:
        session_id = _new_id("session")
        now = _now()
        conn = await self._get_conn()
        await conn.execute(
            """INSERT INTO studio_sessions
               (session_id, user_id, title, chapter, scene_id, context_type, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                user_id,
                title,
                chapter,
                scene_id,
                context_type,
                "draft",
                now,
                now,
            ),
        )
        await conn.commit()
        return StudioSession(
            session_id=session_id,
            user_id=user_id,
            title=title,
            chapter=chapter,
            scene_id=scene_id,
            context_type=context_type,
            status=StudioSessionStatus.DRAFT,
            created_at=now,
            updated_at=now,
        )

    async def get_session(self, session_id: str) -> StudioSession | None:
        conn = await self._get_conn()
        row = await conn.execute_fetchall(
            "SELECT * FROM studio_sessions WHERE session_id = ?", (session_id,)
        )
        if not row:
            return None
        r = row[0]
        return StudioSession(
            session_id=r["session_id"],
            user_id=r["user_id"],
            title=r["title"],
            chapter=r["chapter"],
            scene_id=r["scene_id"],
            context_type=r["context_type"],
            active_version_id=r["active_version_id"],
            status=StudioSessionStatus(r["status"]),
            reference_assets=json.loads(r["reference_assets"] or "[]"),
            approved_image_asset_id=_row_get(r, "approved_image_asset_id"),
            created_at=r["created_at"],
            updated_at=r["updated_at"],
            finalized_at=r["finalized_at"],
        )

    async def list_sessions(
        self, user_id: str, status: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[StudioSession]:
        conn = await self._get_conn()
        if status:
            rows = await conn.execute_fetchall(
                "SELECT * FROM studio_sessions WHERE user_id = ? AND status = ? ORDER BY updated_at DESC LIMIT ? OFFSET ?",
                (user_id, status, limit, offset),
            )
        else:
            rows = await conn.execute_fetchall(
                "SELECT * FROM studio_sessions WHERE user_id = ? ORDER BY updated_at DESC LIMIT ? OFFSET ?",
                (user_id, limit, offset),
            )
        return [
            StudioSession(
                session_id=r["session_id"],
                user_id=r["user_id"],
                title=r["title"],
                chapter=r["chapter"],
                scene_id=r["scene_id"],
                context_type=r["context_type"],
                active_version_id=r["active_version_id"],
                status=StudioSessionStatus(r["status"]),
                reference_assets=json.loads(r["reference_assets"] or "[]"),
                approved_image_asset_id=_row_get(r, "approved_image_asset_id"),
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                finalized_at=r["finalized_at"],
            )
            for r in rows
        ]

    async def update_session_status(self, session_id: str, status: str) -> bool:
        conn = await self._get_conn()
        now = _now()
        finalized = now if status in ("approved", "rejected") else None
        await conn.execute(
            "UPDATE studio_sessions SET status = ?, updated_at = ?, finalized_at = ? WHERE session_id = ?",
            (status, now, finalized, session_id),
        )
        await conn.commit()
        return True

    async def set_active_version(self, session_id: str, version_id: str) -> bool:
        conn = await self._get_conn()
        now = _now()
        await conn.execute(
            "UPDATE studio_sessions SET active_version_id = ?, updated_at = ? WHERE session_id = ?",
            (version_id, now, session_id),
        )
        await conn.commit()
        return True

    async def add_reference_to_session(self, session_id: str, asset_id: str) -> bool:
        conn = await self._get_conn()
        rows = await conn.execute_fetchall(
            "SELECT reference_assets FROM studio_sessions WHERE session_id = ?",
            (session_id,),
        )
        if not rows:
            return False
        refs = json.loads(rows[0]["reference_assets"] or "[]")
        if asset_id not in refs:
            refs.append(asset_id)
        now = _now()
        await conn.execute(
            "UPDATE studio_sessions SET reference_assets = ?, updated_at = ? WHERE session_id = ?",
            (json.dumps(refs), now, session_id),
        )
        await conn.commit()
        return True

    async def set_approved_image(self, session_id: str, asset_id: str | None) -> bool:
        """Утвердить (или снять) IMAGE-ассет как кадр-основу сцены.

        Шаг «создать и утвердить изображение» производственной модели Studio:
        approved_image_asset_id — asset_id в AssetStorage (status=completed).
        """
        conn = await self._get_conn()
        now = _now()
        await conn.execute(
            "UPDATE studio_sessions SET approved_image_asset_id = ?, updated_at = ? WHERE session_id = ?",
            (asset_id, now, session_id),
        )
        await conn.commit()
        return True

    # ── Messages ─────────────────────────────────────────────────

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        created_version_id: str | None = None,
    ) -> StudioMessage:
        message_id = _new_id("msg")
        now = _now()
        conn = await self._get_conn()
        await conn.execute(
            """INSERT INTO studio_messages
               (message_id, session_id, role, content, created_version_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (message_id, session_id, role, content, created_version_id, now),
        )
        await conn.commit()
        return StudioMessage(
            message_id=message_id,
            session_id=session_id,
            role=StudioMessageRole(role),
            content=content,
            created_version_id=created_version_id,
            created_at=now,
        )

    async def get_messages(
        self, session_id: str, limit: int = 50, offset: int = 0
    ) -> list[StudioMessage]:
        conn = await self._get_conn()
        rows = await conn.execute_fetchall(
            "SELECT * FROM studio_messages WHERE session_id = ? ORDER BY created_at ASC LIMIT ? OFFSET ?",
            (session_id, limit, offset),
        )
        return [
            StudioMessage(
                message_id=r["message_id"],
                session_id=r["session_id"],
                role=StudioMessageRole(r["role"]),
                content=r["content"],
                created_version_id=r["created_version_id"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    # ── Versions ─────────────────────────────────────────────────

    async def create_version(
        self,
        session_id: str,
        version_number: int,
        image_description: MediaPlan | None = None,
        video_description: MediaPlan | None = None,
        video_scenario: VideoScenario | None = None,
        parent_version_id: str | None = None,
        derivation: str = "initial",
        user_modifications: list[UserModification] | None = None,
        created_by: str = "system",
        note: str = "",
    ) -> StudioVersion:
        version_id = _new_id("ver")
        now = _now()
        conn = await self._get_conn()

        # Deactivate previous active version
        await conn.execute(
            "UPDATE studio_versions SET is_active = 0 WHERE session_id = ? AND is_active = 1",
            (session_id,),
        )

        await conn.execute(
            """INSERT INTO studio_versions
               (version_id, session_id, version_number,
                image_description_json, video_description_json, video_scenario_json,
                parent_version_id, derivation, user_modifications_json,
                is_active, is_final, created_by, created_at, note)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, ?, ?, ?)""",
            (
                version_id,
                session_id,
                version_number,
                image_description.model_dump_json() if image_description else None,
                video_description.model_dump_json() if video_description else None,
                video_scenario.model_dump_json() if video_scenario else None,
                parent_version_id,
                derivation,
                json.dumps(
                    [m.model_dump() for m in (user_modifications or [])],
                    ensure_ascii=False,
                ),
                created_by,
                now,
                note,
            ),
        )
        await conn.commit()

        # Update session active version
        await self.set_active_version(session_id, version_id)

        return StudioVersion(
            version_id=version_id,
            session_id=session_id,
            version_number=version_number,
            image_description=image_description,
            video_description=video_description,
            video_scenario=video_scenario,
            parent_version_id=parent_version_id,
            derivation=derivation,
            user_modifications=user_modifications or [],
            is_active=True,
            is_final=False,
            created_by=created_by,
            created_at=now,
            note=note,
        )

    async def get_version(self, version_id: str) -> StudioVersion | None:
        conn = await self._get_conn()
        rows = await conn.execute_fetchall(
            "SELECT * FROM studio_versions WHERE version_id = ?", (version_id,)
        )
        if not rows:
            return None
        return self._row_to_version(rows[0])

    async def get_versions(self, session_id: str) -> list[StudioVersion]:
        conn = await self._get_conn()
        rows = await conn.execute_fetchall(
            "SELECT * FROM studio_versions WHERE session_id = ? ORDER BY version_number ASC",
            (session_id,),
        )
        return [self._row_to_version(r) for r in rows]

    async def get_active_version(self, session_id: str) -> StudioVersion | None:
        conn = await self._get_conn()
        rows = await conn.execute_fetchall(
            "SELECT * FROM studio_versions WHERE session_id = ? AND is_active = 1",
            (session_id,),
        )
        if not rows:
            return None
        return self._row_to_version(rows[0])

    async def finalize_version(self, version_id: str) -> bool:
        conn = await self._get_conn()
        await conn.execute(
            "UPDATE studio_versions SET is_final = 1 WHERE version_id = ?",
            (version_id,),
        )
        await conn.commit()
        return True

    def _row_to_version(self, r) -> StudioVersion:
        mods_raw = json.loads(r["user_modifications_json"] or "[]")
        mods = [UserModification(**m) for m in mods_raw]

        img = None
        if r["image_description_json"]:
            img = MediaPlan.model_validate_json(r["image_description_json"])
        vid = None
        if r["video_description_json"]:
            vid = MediaPlan.model_validate_json(r["video_description_json"])
        scenario = None
        if r["video_scenario_json"]:
            scenario = VideoScenario.model_validate_json(r["video_scenario_json"])

        return StudioVersion(
            version_id=r["version_id"],
            session_id=r["session_id"],
            version_number=r["version_number"],
            image_description=img,
            video_description=vid,
            video_scenario=scenario,
            parent_version_id=r["parent_version_id"],
            derivation=r["derivation"],
            user_modifications=mods,
            is_active=bool(r["is_active"]),
            is_final=bool(r["is_final"]),
            created_by=r["created_by"],
            created_at=r["created_at"],
            note=r["note"] or "",
        )

    # ── References ───────────────────────────────────────────────

    async def add_reference(
        self, session_id: str, asset_id: str, description: str = ""
    ) -> ReferenceAsset:
        now = _now()
        conn = await self._get_conn()
        await conn.execute(
            """INSERT OR REPLACE INTO studio_references
               (asset_id, session_id, description, source_type, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (asset_id, session_id, description, "user_reference", now),
        )
        await conn.commit()
        # Also link to session
        await self.add_reference_to_session(session_id, asset_id)
        return ReferenceAsset(
            asset_id=asset_id,
            session_id=session_id,
            description=description,
            source_type="user_reference",
            created_at=now,
        )

    async def get_references(self, session_id: str) -> list[ReferenceAsset]:
        conn = await self._get_conn()
        rows = await conn.execute_fetchall(
            "SELECT * FROM studio_references WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        )
        return [
            ReferenceAsset(
                asset_id=r["asset_id"],
                session_id=r["session_id"],
                description=r["description"],
                source_type=r["source_type"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    async def get_reference(self, asset_id: str) -> ReferenceAsset | None:
        conn = await self._get_conn()
        rows = await conn.execute_fetchall(
            "SELECT * FROM studio_references WHERE asset_id = ?", (asset_id,)
        )
        if not rows:
            return None
        r = rows[0]
        return ReferenceAsset(
            asset_id=r["asset_id"],
            session_id=r["session_id"],
            description=r["description"],
            source_type=r["source_type"],
            created_at=r["created_at"],
        )

    # ── Film Art Direction (общие визуальные правила фильма) ─────

    async def get_art_direction(self, ad_id: str = "film") -> FilmArtDirection | None:
        """Прочитать сохранённые общие правила (None — ещё не сохранялись)."""
        conn = await self._get_conn()
        rows = await conn.execute_fetchall(
            "SELECT data FROM studio_art_direction WHERE ad_id = ?", (ad_id,)
        )
        if not rows:
            return None
        try:
            return FilmArtDirection.model_validate_json(rows[0]["data"])
        except Exception as e:
            log.error("art_direction_parse_failed ad_id=%s error=%s", ad_id, e)
            return None

    async def save_art_direction(self, ad) -> None:
        """Сохранить общие правила целиком (revision считает вызывающая сторона)."""
        conn = await self._get_conn()
        now = _now()
        await conn.execute(
            """INSERT INTO studio_art_direction (ad_id, data, updated_at)
               VALUES (?, ?, ?)
               ON CONFLICT(ad_id) DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at""",
            (ad.ad_id, ad.model_dump_json(), now),
        )
        await conn.commit()

    # ── Prepared updates (подготовленные обновления кадров) ──────

    async def save_prepared_update(self, prepared) -> None:
        """Upsert подготовленного задания (модель из studio.prepared_updates)."""
        from .prepared_updates import (
            PreparedUpdate,
        )  # локальный импорт — избежать цикла

        assert isinstance(prepared, PreparedUpdate)
        now = _now()
        prepared.updated_at = now
        if not prepared.created_at:
            prepared.created_at = now
        conn = await self._get_conn()
        await conn.execute(
            """INSERT INTO studio_prepared_updates
               (prepared_id, session_id, shot_id, data, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(prepared_id) DO UPDATE SET
                 shot_id = excluded.shot_id,
                 data = excluded.data,
                 updated_at = excluded.updated_at""",
            (
                prepared.prepared_id,
                prepared.session_id,
                prepared.shot_id,
                prepared.model_dump_json(),
                prepared.created_at,
                prepared.updated_at,
            ),
        )
        await conn.commit()

    async def get_prepared_update(self, prepared_id: str):
        from .prepared_updates import PreparedUpdate

        conn = await self._get_conn()
        rows = await conn.execute_fetchall(
            "SELECT data FROM studio_prepared_updates WHERE prepared_id = ?",
            (prepared_id,),
        )
        if not rows:
            return None
        try:
            return PreparedUpdate.model_validate_json(rows[0]["data"])
        except Exception as e:
            log.error("prepared_update_parse_failed id=%s error=%s", prepared_id, e)
            return None

    async def list_prepared_updates(self, session_id: str, shot_id: str | None = None):
        from .prepared_updates import PreparedUpdate

        conn = await self._get_conn()
        if shot_id:
            rows = await conn.execute_fetchall(
                "SELECT data FROM studio_prepared_updates WHERE session_id = ? AND shot_id = ? ORDER BY created_at ASC",
                (session_id, shot_id),
            )
        else:
            rows = await conn.execute_fetchall(
                "SELECT data FROM studio_prepared_updates WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,),
            )
        result = []
        for r in rows:
            try:
                result.append(PreparedUpdate.model_validate_json(r["data"]))
            except Exception as e:
                log.error(
                    "prepared_update_parse_failed session=%s error=%s", session_id, e
                )
        return result

    # ── Continuity decisions (решения режиссёра по связанности) ──

    async def save_continuity_decision(self, decision) -> None:
        """Upsert решения по связи (модель из studio.continuity)."""
        from .continuity import ContinuityDecision

        assert isinstance(decision, ContinuityDecision)
        now = _now()
        decision.updated_at = now
        if not decision.created_at:
            decision.created_at = now
        conn = await self._get_conn()
        await conn.execute(
            """INSERT INTO studio_continuity_decisions
               (decision_id, session_id, link_key, data, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(decision_id) DO UPDATE SET
                 link_key = excluded.link_key,
                 data = excluded.data,
                 updated_at = excluded.updated_at""",
            (
                decision.decision_id,
                decision.session_id,
                decision.link_key,
                decision.model_dump_json(),
                decision.created_at,
                decision.updated_at,
            ),
        )
        await conn.commit()

    async def get_continuity_decision(self, decision_id: str):
        from .continuity import ContinuityDecision

        conn = await self._get_conn()
        rows = await conn.execute_fetchall(
            "SELECT data FROM studio_continuity_decisions WHERE decision_id = ?",
            (decision_id,),
        )
        if not rows:
            return None
        try:
            return ContinuityDecision.model_validate_json(rows[0]["data"])
        except Exception as e:
            log.error("continuity_decision_parse_failed id=%s error=%s", decision_id, e)
            return None

    async def list_continuity_decisions(self, session_id: str | None = None):
        from .continuity import ContinuityDecision

        conn = await self._get_conn()
        if session_id:
            rows = await conn.execute_fetchall(
                "SELECT data FROM studio_continuity_decisions WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,),
            )
        else:
            rows = await conn.execute_fetchall(
                "SELECT data FROM studio_continuity_decisions ORDER BY created_at ASC",
            )
        result = []
        for r in rows:
            try:
                result.append(ContinuityDecision.model_validate_json(r["data"]))
            except Exception as e:
                log.error("continuity_decision_parse_failed error=%s", e)
        return result

    async def delete_continuity_decision(self, decision_id: str) -> bool:
        conn = await self._get_conn()
        cursor = await conn.execute(
            "DELETE FROM studio_continuity_decisions WHERE decision_id = ?",
            (decision_id,),
        )
        await conn.commit()
        return cursor.rowcount > 0

    async def delete_session(self, session_id: str) -> bool:
        """Delete session and all related data (versions, messages, references)."""
        conn = await self._get_conn()
        cursor = await conn.execute(
            "DELETE FROM studio_sessions WHERE session_id = ?", (session_id,)
        )
        await conn.commit()
        # Cascade: versions, messages, references are deleted by FK or separately
        await conn.execute(
            "DELETE FROM studio_versions WHERE session_id = ?", (session_id,)
        )
        await conn.execute(
            "DELETE FROM studio_messages WHERE session_id = ?", (session_id,)
        )
        await conn.execute(
            "DELETE FROM studio_references WHERE session_id = ?", (session_id,)
        )
        await conn.commit()
        return cursor.rowcount > 0
