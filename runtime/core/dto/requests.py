"""Входящие DTO — валидация всех входящих запросов."""
from __future__ import annotations

from pydantic import BaseModel, Field


# ── Chat ──────────────────────────────────────────────

class Message(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1, max_length=10000)


class ChatRequest(BaseModel):
    messages: list[Message] = Field(..., min_length=1)
    session_id: str | None = None
    provider: str | None = None
    model: str | None = None
    stream: bool = False


# ── Book Intelligence ─────────────────────────────────

class BookAskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000, json_schema_extra={"example": "Кто такой Велик?"})
    context: str | None = Field(None, max_length=1000)
    messages: list[Message] | None = None  # история диалога
    session_id: str | None = Field(
        None,
        min_length=8,
        max_length=128,
        pattern=r"^[A-Za-z0-9_-]+$",
    )


class BookGenerateRequest(BaseModel):
    type: str = Field(..., min_length=1, max_length=100, json_schema_extra={"example": "chapter"})
    topic: str = Field(..., min_length=1, max_length=500, json_schema_extra={"example": "История Аркаима"})
    auto_publish: bool = False


# ── Visual Genome ─────────────────────────────────────

class VisualSceneRequest(BaseModel):
    chapter: int = Field(..., ge=1)
    title: str = Field(..., min_length=1, max_length=200)
    characters: list[str] = []
    location: str = ""
    emotion: str = "neutral"
    color_palette: list[str] = []
    meaning_tags: list[str] = []


class VisualCharacterRequest(BaseModel):
    character_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    archetype: str = ""
    color_palette: list[str] = []
    visual_description: str = ""


class VisualLocationRequest(BaseModel):
    location_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    atmosphere: str = ""
    architecture: str = ""
    lighting: str = ""


class VisualFromSpeechRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    reader_id: str | None = None


class VisualizeRequest(BaseModel):
    chapter: int = Field(..., ge=1)
    scene_id: str = Field(..., min_length=1)
    reader_id: str | None = None


class EpochVisualRequest(BaseModel):
    """Request for epoch visualization."""
    reader_id: str | None = None


# ── Telegram ──────────────────────────────────────────

class TelegramMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    user_id: str = "unknown"


# ── Auth (внутренние, для вызова из сервисов) ─────────

class LoginData(BaseModel):
    provider: str
    provider_user_id: str
    username: str | None = None
    display_name: str | None = None
    role: str = "reader"
