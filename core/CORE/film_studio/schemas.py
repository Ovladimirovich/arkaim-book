"""Film Studio — Pydantic schemas для проектов фильмов."""
from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    GENERATING = "generating"
    ASSEMBLING = "assembling"
    COMPLETE = "complete"
    FAILED = "failed"


class ShotStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class CameraMotion(str, Enum):
    STATIC = "static"
    SLOW_DOLLY_IN = "slow_dolly_in"
    SLOW_DOLLY_OUT = "slow_dolly_out"
    SLOW_PAN = "slow_pan"
    SLOW_ZOOM_IN = "slow_zoom_in"
    SLOW_ZOOM_OUT = "slow_zoom_out"
    TRACKING = "tracking"
    CRANE_UP = "crane_up"
    ORBIT = "orbit"
    FOLLOW = "follow"


class CameraSpec(BaseModel):
    shot_type: str = "medium_shot"
    angle: str = "eye_level"
    motion: CameraMotion = CameraMotion.STATIC


class ShotVersion(BaseModel):
    """Версия генерации шота."""
    id: str
    asset_id: str | None = None
    prompt: str = ""
    camera: CameraSpec = CameraSpec()
    duration_sec: float = Field(3.0, gt=0)
    negative_prompt: list[str] = Field(default_factory=list)
    status: ShotStatus = ShotStatus.PENDING
    error: str | None = None
    is_active: bool = True
    quality: str = Field("standard", pattern="^(draft|standard|high|ultra)$")
    created_at: str = ""


class SceneShot(BaseModel):
    """Шот в сцене фильма."""
    id: str
    scene_id: str
    order: int = 0
    prompt_override: str = ""
    camera: CameraSpec = CameraSpec()
    duration_sec: float = Field(3.0, gt=0)
    versions: list[ShotVersion] = Field(default_factory=list)
    active_version_id: str | None = None


class FilmProject(BaseModel):
    """Проект фильма."""
    id: str
    title: str
    description: str = ""
    status: ProjectStatus = ProjectStatus.DRAFT
    style: str = "cinematic_fantasy"
    mood: str = "neutral"
    aspect_ratio: str = "16:9"
    fps: int = Field(24, ge=12, le=60)
    # Scenes with shots
    scenes: list[SceneShot] = Field(default_factory=list)
    # Output
    output_path: str | None = None
    output_duration_sec: float = 0
    # Metadata
    created_at: str = ""
    updated_at: str = ""
    reader_id: str | None = None


class FilmProjectSummary(BaseModel):
    """Краткая информация о проекте для списка."""
    id: str
    title: str
    status: ProjectStatus
    scene_count: int = 0
    shot_count: int = 0
    completed_shots: int = 0
    total_duration_sec: float = 0
    created_at: str = ""
    updated_at: str = ""
