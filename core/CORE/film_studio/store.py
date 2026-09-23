"""Film Project Store — SQLite хранилище для проектов фильмов."""
from __future__ import annotations

import json
import time
import uuid
import logging
from pathlib import Path

from .schemas import (
    FilmProject, FilmProjectSummary, SceneShot, ShotVersion,
    ProjectStatus, ShotStatus, CameraSpec,
)

log = logging.getLogger("film_studio.store")

_DB_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
_DB_PATH = _DB_DIR / "film_studio.db"


class FilmProjectStore:
    """Хранение проектов фильмов в SQLite."""

    def __init__(self, db_path: str | Path | None = None):
        self._db_path = Path(db_path) if db_path else _DB_PATH
        self._conn = None

    async def _get_conn(self):
        if self._conn is None:
            import aiosqlite
            self._conn = await aiosqlite.connect(str(self._db_path))
            self._conn.row_factory = aiosqlite.Row
            await self._conn.execute("PRAGMA journal_mode = WAL")
            await self._init_tables()
            await self._migrate_schema()
        return self._conn

    async def _migrate_schema(self):
        """F-12: ensure film_shots has quality column (idempotent)."""
        cur = await self._conn.execute(
            "SELECT COUNT(*) FROM pragma_table_info('film_shots') WHERE name='quality'"
        )
        (count,) = await cur.fetchone()
        if count == 0:
            await self._conn.execute(
                "ALTER TABLE film_shots ADD COLUMN quality TEXT DEFAULT 'standard'"
            )
            await self._conn.commit()
            log.info("F-12 migration: added quality column to film_shots")

    async def _init_tables(self):
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS film_projects (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                status TEXT DEFAULT 'draft',
                style TEXT DEFAULT 'cinematic_fantasy',
                mood TEXT DEFAULT 'neutral',
                aspect_ratio TEXT DEFAULT '16:9',
                fps INTEGER DEFAULT 24,
                output_path TEXT,
                output_duration_sec REAL DEFAULT 0,
                reader_id TEXT,
                created_at TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS film_scenes (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                scene_id TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0,
                prompt_override TEXT DEFAULT '',
                camera JSON DEFAULT '{}',
                duration_sec REAL DEFAULT 3.0,
                active_version_id TEXT,
                FOREIGN KEY (project_id) REFERENCES film_projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS film_shots (
                id TEXT PRIMARY KEY,
                scene_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                asset_id TEXT,
                prompt TEXT DEFAULT '',
                camera JSON DEFAULT '{}',
                duration_sec REAL DEFAULT 3.0,
                negative_prompt JSON DEFAULT '[]',
                status TEXT DEFAULT 'pending',
                error TEXT,
                is_active INTEGER DEFAULT 1,
                quality TEXT DEFAULT 'standard',
                created_at TEXT,
                FOREIGN KEY (scene_id) REFERENCES film_scenes(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_scenes_project ON film_scenes(project_id);
            CREATE INDEX IF NOT EXISTS idx_shots_scene ON film_shots(scene_id);
            CREATE INDEX IF NOT EXISTS idx_shots_project ON film_shots(project_id);
        """)
        await self._conn.commit()

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None

    # ── Projects ──────────────────────────────────────────

    async def create_project(
        self,
        title: str,
        description: str = "",
        style: str = "cinematic_fantasy",
        mood: str = "neutral",
        aspect_ratio: str = "16:9",
        fps: int = 24,
        reader_id: str | None = None,
    ) -> FilmProject:
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        project_id = f"film_{uuid.uuid4().hex[:12]}"
        conn = await self._get_conn()
        await conn.execute(
            """INSERT INTO film_projects
               (id, title, description, status, style, mood, aspect_ratio, fps, reader_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (project_id, title, description, ProjectStatus.DRAFT.value,
             style, mood, aspect_ratio, fps, reader_id, now, now),
        )
        await conn.commit()
        return FilmProject(
            id=project_id, title=title, description=description,
            status=ProjectStatus.DRAFT, style=style, mood=mood,
            aspect_ratio=aspect_ratio, fps=fps, reader_id=reader_id,
            created_at=now, updated_at=now,
        )

    async def get_project(self, project_id: str) -> FilmProject | None:
        conn = await self._get_conn()
        row = await (await conn.execute(
            "SELECT * FROM film_projects WHERE id = ?", (project_id,)
        )).fetchone()
        if not row:
            return None
        project = self._row_to_project(row)
        # Load scenes and shots
        project.scenes = await self._load_scenes(project_id)
        return project

    async def list_projects(self, limit: int = 50, offset: int = 0) -> list[FilmProjectSummary]:
        conn = await self._get_conn()
        rows = await (await conn.execute(
            "SELECT * FROM film_projects ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )).fetchall()

        if not rows:
            return []

        project_ids = [row["id"] for row in rows]

        # Batch load all scenes for these projects (single query)
        placeholders = ",".join("?" for _ in project_ids)
        scene_rows = await (await conn.execute(
            f"SELECT * FROM film_scenes WHERE project_id IN ({placeholders}) ORDER BY sort_order",
            project_ids,
        )).fetchall()

        # Batch load all shots for these scenes (single query)
        scene_ids = [sr["id"] for sr in scene_rows]
        shot_map: dict[str, list] = {}
        if scene_ids:
            scene_placeholders = ",".join("?" for _ in scene_ids)
            shot_rows = await (await conn.execute(
                f"SELECT * FROM film_shots WHERE scene_id IN ({scene_placeholders}) ORDER BY created_at",
                scene_ids,
            )).fetchall()
            for sr in shot_rows:
                shot_map.setdefault(sr["scene_id"], []).append(sr)

        # Build scene lists per project
        scenes_by_project: dict[str, list] = {}
        for sr in scene_rows:
            pid = sr["project_id"]
            scene = self._row_to_scene(sr)
            scene.versions = [self._row_to_shot(r) for r in shot_map.get(sr["id"], [])]
            scenes_by_project.setdefault(pid, []).append(scene)

        results = []
        for row in rows:
            project_id = row["id"]
            scenes = scenes_by_project.get(project_id, [])
            shot_count = sum(len(s.versions) for s in scenes)
            completed = sum(
                1 for s in scenes
                for v in s.versions
                if v.status == ShotStatus.COMPLETED
            )
            total_dur = sum(
                v.duration_sec for s in scenes
                for v in s.versions if v.is_active and v.status == ShotStatus.COMPLETED
            )
            results.append(FilmProjectSummary(
                id=project_id,
                title=row["title"],
                status=ProjectStatus(row["status"]),
                scene_count=len(scenes),
                shot_count=shot_count,
                completed_shots=completed,
                total_duration_sec=total_dur,
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            ))
        return results

    async def update_project(self, project_id: str, **kwargs) -> bool:
        conn = await self._get_conn()
        allowed = {"title", "description", "status", "style", "mood", "aspect_ratio", "fps", "output_path", "output_duration_sec"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False
        # Validate status enum
        if "status" in updates:
            updates["status"] = ProjectStatus(updates["status"]).value
        updates["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [project_id]
        await conn.execute(f"UPDATE film_projects SET {set_clause} WHERE id = ?", values)
        await conn.commit()
        return True

    async def delete_project(self, project_id: str) -> bool:
        conn = await self._get_conn()
        await conn.execute("DELETE FROM film_shots WHERE project_id = ?", (project_id,))
        await conn.execute("DELETE FROM film_scenes WHERE project_id = ?", (project_id,))
        cursor = await conn.execute("DELETE FROM film_projects WHERE id = ?", (project_id,))
        await conn.commit()
        return cursor.rowcount > 0

    # ── Scenes ────────────────────────────────────────────

    async def add_scene(
        self,
        project_id: str,
        scene_id: str,
        order: int = 0,
        prompt_override: str = "",
        duration_sec: float = 3.0,
    ) -> SceneShot | None:
        conn = await self._get_conn()
        fs_id = f"fsc_{uuid.uuid4().hex[:10]}"
        camera = CameraSpec().model_dump()
        await conn.execute(
            """INSERT INTO film_scenes
               (id, project_id, scene_id, sort_order, prompt_override, camera, duration_sec)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (fs_id, project_id, scene_id, order, prompt_override, json.dumps(camera), duration_sec),
        )
        await conn.execute(
            "UPDATE film_projects SET updated_at = ? WHERE id = ?",
            (time.strftime("%Y-%m-%dT%H:%M:%SZ"), project_id),
        )
        await conn.commit()
        return SceneShot(
            id=fs_id, scene_id=scene_id, order=order,
            prompt_override=prompt_override, duration_sec=duration_sec,
        )

    async def get_scene(self, scene_id: str) -> SceneShot | None:
        conn = await self._get_conn()
        row = await (await conn.execute(
            "SELECT * FROM film_scenes WHERE id = ?", (scene_id,)
        )).fetchone()
        if not row:
            return None
        scene = self._row_to_scene(row)
        scene.versions = await self._load_shots(scene_id)
        return scene

    async def delete_scene(self, scene_id: str) -> bool:
        conn = await self._get_conn()
        # Get project_id before deletion
        row = await conn.execute("SELECT project_id FROM film_scenes WHERE id = ?", (scene_id,))
        scene_row = await row.fetchone()
        project_id = scene_row["project_id"] if scene_row else None
        await conn.execute("DELETE FROM film_shots WHERE scene_id = ?", (scene_id,))
        cursor = await conn.execute("DELETE FROM film_scenes WHERE id = ?", (scene_id,))
        # Update project's updated_at
        if project_id:
            now = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            await conn.execute("UPDATE film_projects SET updated_at = ? WHERE id = ?", (now, project_id))
        await conn.commit()
        return cursor.rowcount > 0

    async def update_scene(self, scene_id: str, **kwargs) -> bool:
        conn = await self._get_conn()
        allowed = {"sort_order", "prompt_override", "camera", "duration_sec", "active_version_id"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False
        if "camera" in updates and isinstance(updates["camera"], CameraSpec):
            updates["camera"] = json.dumps(updates["camera"].model_dump())
        elif "camera" in updates and isinstance(updates["camera"], dict):
            updates["camera"] = json.dumps(updates["camera"])
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [scene_id]
        await conn.execute(f"UPDATE film_scenes SET {set_clause} WHERE id = ?", values)
        # Update project's updated_at
        row = await conn.execute("SELECT project_id FROM film_scenes WHERE id = ?", (scene_id,))
        scene_row = await row.fetchone()
        if scene_row:
            now = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            await conn.execute("UPDATE film_projects SET updated_at = ? WHERE id = ?", (now, scene_row["project_id"]))
        await conn.commit()
        return True

    # ── Shots (versions) ──────────────────────────────────

    async def add_shot(
        self,
        scene_id: str,
        project_id: str,
        prompt: str = "",
        camera: CameraSpec | None = None,
        duration_sec: float = 3.0,
    ) -> ShotVersion | None:
        conn = await self._get_conn()
        shot_id = f"sho_{uuid.uuid4().hex[:10]}"
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        cam = (camera or CameraSpec()).model_dump()
        await conn.execute(
            """INSERT INTO film_shots
               (id, scene_id, project_id, prompt, camera, duration_sec, status, is_active, quality, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)""",
            (shot_id, scene_id, project_id, prompt, json.dumps(cam), duration_sec,
             ShotStatus.PENDING.value, "standard", now),
        )
        # Update scene's active_version_id to this new shot
        await conn.execute(
            "UPDATE film_scenes SET active_version_id = ? WHERE id = ?",
            (shot_id, scene_id),
        )
        await conn.execute(
            "UPDATE film_projects SET updated_at = ? WHERE id = ?",
            (now, project_id),
        )
        await conn.commit()
        return ShotVersion(
            id=shot_id, prompt=prompt, camera=camera or CameraSpec(),
            duration_sec=duration_sec, status=ShotStatus.PENDING,
            is_active=True, created_at=now,
        )

    async def update_shot(self, shot_id: str, **kwargs) -> bool:
        conn = await self._get_conn()
        allowed = {"prompt", "camera", "duration_sec", "asset_id", "status", "error", "is_active", "quality", "negative_prompt"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False
        # Validate status enum
        if "status" in updates:
            updates["status"] = ShotStatus(updates["status"]).value
        # Serialize camera if needed
        if "camera" in updates and isinstance(updates["camera"], CameraSpec):
            updates["camera"] = json.dumps(updates["camera"].model_dump())
        elif "camera" in updates and isinstance(updates["camera"], dict):
            updates["camera"] = json.dumps(updates["camera"])
        if "is_active" in updates:
            updates["is_active"] = 1 if updates["is_active"] else 0
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [shot_id]
        await conn.execute(f"UPDATE film_shots SET {set_clause} WHERE id = ?", values)
        await conn.commit()
        return True

    async def delete_shot(self, shot_id: str) -> bool:
        conn = await self._get_conn()
        cursor = await conn.execute("DELETE FROM film_shots WHERE id = ?", (shot_id,))
        await conn.commit()
        return cursor.rowcount > 0

    async def create_shot_version(
        self,
        scene_id: str,
        project_id: str,
        prompt: str = "",
        camera: CameraSpec | None = None,
        duration_sec: float = 3.0,
    ) -> ShotVersion:
        """Создать новую версию шота (деактивировать предыдущую активную)."""
        conn = await self._get_conn()
        # Deactivate current active shot in this scene
        await conn.execute(
            "UPDATE film_shots SET is_active = 0 WHERE scene_id = ? AND is_active = 1",
            (scene_id,),
        )
        shot = await self.add_shot(scene_id, project_id, prompt, camera, duration_sec)
        # add_shot already sets active_version_id, but ensure it's correct
        if shot:
            await conn.execute(
                "UPDATE film_scenes SET active_version_id = ? WHERE id = ?",
                (shot.id, scene_id),
            )
            await conn.commit()
        return shot

    async def activate_shot(self, shot_id: str) -> bool:
        """Активировать версию шота."""
        conn = await self._get_conn()
        # Get scene_id for this shot
        row = await (await conn.execute(
            "SELECT scene_id FROM film_shots WHERE id = ?", (shot_id,)
        )).fetchone()
        if not row:
            return False
        scene_id = row["scene_id"]
        # Deactivate all in this scene
        await conn.execute(
            "UPDATE film_shots SET is_active = 0 WHERE scene_id = ?",
            (scene_id,),
        )
        # Activate this one
        await conn.execute(
            "UPDATE film_shots SET is_active = 1 WHERE id = ?",
            (shot_id,),
        )
        # Update scene's active_version_id
        await conn.execute(
            "UPDATE film_scenes SET active_version_id = ? WHERE id = ?",
            (shot_id, scene_id),
        )
        await conn.commit()
        return True

    async def get_project_stats(self, project_id: str) -> dict:
        scenes = await self._load_scenes(project_id)
        total_shots = sum(len(s.versions) for s in scenes)
        completed = sum(
            1 for s in scenes for v in s.versions
            if v.status == ShotStatus.COMPLETED
        )
        active_duration = sum(
            v.duration_sec for s in scenes
            for v in s.versions
            if v.is_active and v.status == ShotStatus.COMPLETED
        )
        return {
            "project_id": project_id,
            "scene_count": len(scenes),
            "total_shots": total_shots,
            "completed_shots": completed,
            "pending_shots": total_shots - completed,
            "active_duration_sec": active_duration,
        }

    # ── Internal ──────────────────────────────────────────

    async def _load_scenes(self, project_id: str) -> list[SceneShot]:
        conn = await self._get_conn()
        rows = await (await conn.execute(
            "SELECT * FROM film_scenes WHERE project_id = ? ORDER BY sort_order",
            (project_id,),
        )).fetchall()
        scenes = []
        for row in rows:
            scene = self._row_to_scene(row)
            scene.versions = await self._load_shots(scene.id)
            scenes.append(scene)
        return scenes

    async def _load_shots(self, scene_id: str) -> list[ShotVersion]:
        conn = await self._get_conn()
        rows = await (await conn.execute(
            "SELECT * FROM film_shots WHERE scene_id = ? ORDER BY created_at",
            (scene_id,),
        )).fetchall()
        return [self._row_to_shot(r) for r in rows]

    def _row_to_project(self, row) -> FilmProject:
        d = dict(row)
        return FilmProject(
            id=d["id"],
            title=d["title"],
            description=d.get("description", ""),
            status=ProjectStatus(d.get("status", "draft")),
            style=d.get("style", "cinematic_fantasy"),
            mood=d.get("mood", "neutral"),
            aspect_ratio=d.get("aspect_ratio", "16:9"),
            fps=d.get("fps", 24),
            output_path=d.get("output_path"),
            output_duration_sec=d.get("output_duration_sec", 0),
            reader_id=d.get("reader_id"),
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
        )

    def _row_to_scene(self, row) -> SceneShot:
        d = dict(row)
        cam = json.loads(d.get("camera") or "{}")
        return SceneShot(
            id=d["id"],
            scene_id=d["scene_id"],
            order=d.get("sort_order", 0),
            prompt_override=d.get("prompt_override", ""),
            camera=CameraSpec(**cam) if cam else CameraSpec(),
            duration_sec=d.get("duration_sec", 3.0),
            active_version_id=d.get("active_version_id"),
        )

    def _row_to_shot(self, row) -> ShotVersion:
        d = dict(row)
        cam = json.loads(d.get("camera") or "{}")
        neg = json.loads(d.get("negative_prompt") or "[]")
        return ShotVersion(
            id=d["id"],
            asset_id=d.get("asset_id"),
            prompt=d.get("prompt", ""),
            camera=CameraSpec(**cam) if cam else CameraSpec(),
            duration_sec=d.get("duration_sec", 3.0),
            negative_prompt=neg,
            status=ShotStatus(d.get("status", "pending")),
            error=d.get("error"),
            is_active=bool(d.get("is_active", 1)),
            quality=d.get("quality", "standard"),
            created_at=d.get("created_at", ""),
        )
