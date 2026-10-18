"""Исходящие DTO — единый формат ответов API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ── Базовые ───────────────────────────────────────────


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Машин-readable код ошибки")
    message: str = Field(..., description="Человеко-понятное сообщение")
    details: dict[str, Any] | None = None


class SuccessResponse(BaseModel):
    ok: bool = True
    data: Any = None
    trace_id: str | None = None


class ErrorResponse(BaseModel):
    ok: bool = False
    error: ErrorDetail


class PaginatedResponse(BaseModel):
    ok: bool = True
    data: list[Any] = []
    total: int = 0
    page: int = 1
    per_page: int = 20


# ── Auth ──────────────────────────────────────────────


class UserResponse(BaseModel):
    id: str
    provider: str
    username: str | None = None
    display_name: str | None = None
    role: str
    is_active: bool = True
    created_at: str = ""


class AuthResponse(BaseModel):
    ok: bool = True
    user: UserResponse


class ApiKeyResponse(BaseModel):
    key_id: str
    key: str
    key_masked: str


class ApiKeyListItem(BaseModel):
    id: str
    name: str | None = None
    key_prefix: str
    last_used_at: str | None = None
    is_active: bool = True
    created_at: str = ""


# ── Book Intelligence ─────────────────────────────────


class BookAskResponse(BaseModel):
    answer: str
    source: str = ""
    layers_used: dict | None = None
    provenance: list[dict] = []
    uncertainty: dict | None = None
    pulse_confidence: float = 1.0
    llm_used: bool = False


class BookGenomeResponse(BaseModel):
    themes: list[dict] = []
    characters: list[dict] = []
    values: list[dict] = []
    world_entities: list[dict] = []
    author_intent: dict = {}
    modules: dict = {}


class BookLayersResponse(BaseModel):
    knowledge_layer: str = ""
    meaning_layer: str = ""
    identity_layer: str = ""
    mission_layer: str = ""
    world_engine_layer: str = ""


# ── Reader ────────────────────────────────────────────


class ReaderTopicItem(BaseModel):
    name: str
    depth: float
    questions: int


class ReaderProfileResponse(BaseModel):
    reader_id: str
    display_name: str = ""
    questions_total: int = 0
    conversation_count: int = 0
    last_topic: str = ""
    topics: list[ReaderTopicItem] = []


class ReaderContextResponse(BaseModel):
    context: str = ""


class ReaderStatsResponse(BaseModel):
    total_readers: int = 0
    total_topics: int = 0
    total_questions: int = 0


# ── Reading Progress ──────────────────────────────────


class ReadingProgressItem(BaseModel):
    chapter_id: str
    chapter_index: int
    first_read_at: str = ""
    last_read_at: str = ""
    read_seconds: int = 0
    completed: bool = False
    scroll_percent: float = 0.0


class ReadingPositionResponse(BaseModel):
    chapter_id: str = ""
    chapter_index: int = 0
    scroll_percent: float = 0.0
    last_read_at: str = ""


class ReadingStatsResponse(BaseModel):
    chapters_started: int = 0
    chapters_completed: int = 0
    total_seconds: int = 0


# ── Visual Genome ─────────────────────────────────────


class VisualizeResponse(BaseModel):
    prompt: str
    image_bytes: str = Field(..., description="Base64-encoded image")
    content_type: str = "image/svg+xml"


# ── Health ────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = ""


class ProviderHealthResponse(BaseModel):
    status: str = "ok"
    providers: dict[str, bool] = {}
