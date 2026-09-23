"""Pydantic-схемы для Visual Assets — генерация изображений и видео."""
from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class AssetType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"


class AssetStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class CameraSpec(BaseModel):
    shot_type: str = "medium_shot"
    angle: str = "eye_level"
    movement: str = "static"


class CharacterInAsset(BaseModel):
    character_id: str
    name: str
    role: str = "supporting"
    appearance: str = ""
    expression: str = ""
    pose: str = ""


class ShotSpec(BaseModel):
    id: str
    prompt: str = ""
    duration_sec: float = 2.0
    camera: CameraSpec = CameraSpec()
    lighting: str = ""
    palette: list[str] = []


class GenerationParams(BaseModel):
    provider: str = "auto"
    model: str = "sdxl"
    size: str = "1024x1024"
    seed: int | None = None
    steps: int = 30
    quality: str = "standard"
    negative_prompt: list[str] = Field(default_factory=list)


class VisualAsset(BaseModel):
    """Доменная запись-результат генерации (image/video).

    MD-2 DEPRECATED как ВХОД генерации: смысловой вход консолидирован
    в SceneContext (VisualContext+scene_extras). Схема сохранена как
    результат пайплайна (статус/файлы/prompt_used) и для legacy-маршрутов
    /assets/generate*; execution-поля (GenerationParams) остаются до
    MD-3 (MediaPlan-контракт) — чистка вне MD-2 (MB-3). НЕ УДАЛЕНА.
    """
    asset_id: str
    asset_type: AssetType
    book_id: str = "arkaim"
    chapter: int
    scene_id: str
    title: str = ""
    intent: str = "key_frame"
    mood: str = "neutral"
    style: str = "cinematic_fantasy"
    palette: list[str] = Field(default_factory=list)
    camera: CameraSpec = CameraSpec()
    characters: list[CharacterInAsset] = Field(default_factory=list)
    objects: list[str] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)
    composition: dict = Field(default_factory=dict)
    generation: GenerationParams = GenerationParams()
    # Video-specific
    duration_sec: float = 0
    fps: int = 24
    shots: list[ShotSpec] = Field(default_factory=list)
    transition: dict = Field(default_factory=dict)
    audio: dict = Field(default_factory=dict)
    # Output
    status: AssetStatus = AssetStatus.PENDING
    file_path: str | None = None
    thumbnail_path: str | None = None
    prompt_used: str = ""
    error: str | None = None
    reader_id: str | None = None
    created_at: str = ""
    updated_at: str = ""
