# OpenAI-compatible DTOs for Gateway

from pydantic import BaseModel, Field
from typing import Optional


class OpenAIMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str


class OpenAIChatCompletionRequest(BaseModel):
    model: str = Field(..., description="Provider/model identifier")
    messages: list[OpenAIMessage] = Field(..., min_length=1)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1)
    stream: bool = False
    # Ignored parameters (for compatibility)
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop: Optional[list[str]] = None


class OpenAIChoice(BaseModel):
    index: int
    message: dict
    finish_reason: str = "stop"


class OpenAIUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class OpenAIChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[OpenAIChoice]
    usage: Optional[OpenAIUsage] = None


class OpenAIError(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None


class OpenAIErrorResponse(BaseModel):
    ok: bool = False
    error: OpenAIError


class OpenAIModel(BaseModel):
    id: str
    object: str = "model"
    owned_by: str = ""
    context_window: Optional[int] = None
    modalities: Optional[list[str]] = None
    status: Optional[str] = None  # "available", "unknown", "unavailable"


class OpenAIHealthProvider(BaseModel):
    name: str
    health: str = "ok"
    models: list[dict] = []
    last_error: Optional[str] = None
