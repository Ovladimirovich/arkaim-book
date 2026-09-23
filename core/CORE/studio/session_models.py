"""Studio Session Models — Pydantic schemas for Studio v2 (Phase 1B).

Модели сессии Studio: сессия, сообщения, версии, reference assets, export.

Ключевые принципы:
  - Studio НЕ генератор описаний: три результата приходят из Arkaim Description System
  - Discussion ≠ Description: сообщения ≠ версии
  - Версии immutable: lineage не рвётся
  - MediaPlan v0 не расширяется
  - Reference — пользовательский вход, не execution

ADR compliance: ADR_ARKAIM_MEDIA_BOUNDARY, ADR_MEDIA_PLAN_V0.
"""
from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, ConfigDict, Field

# Reuse existing MediaPlan + VideoScenario (Phase 1A)
from media_plan.schemas import MediaPlan
from studio.scenario_schemas import VideoScenario

_MODEL_CONFIG = ConfigDict(extra="forbid")


# ── Enums ────────────────────────────────────────────────────────


class StudioSessionStatus(str, Enum):
    DRAFT = "draft"
    DISCUSSING = "discussing"
    APPROVED = "approved"
    REJECTED = "rejected"
    SENT = "sent"


class StudioMessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# ── Studio Session ───────────────────────────────────────────────


class StudioSession(BaseModel):
    """Studio-сессия: привязана к сцене, хранит state.

    Сессия — это workspace, где пользователь корректирует
    три исходных описания, полученных от Arkaim Description System.
    """
    model_config = _MODEL_CONFIG

    session_id: str = ""
    user_id: str = ""
    title: str = ""

    # Источник сцены
    chapter: int = 0
    scene_id: str = ""
    context_type: str = "scene"  # scene | epoch | character | location

    # Текущее состояние
    active_version_id: str | None = None
    status: StudioSessionStatus = StudioSessionStatus.DRAFT

    # Связи
    reference_assets: list[str] = Field(default_factory=list)  # asset_ids

    # Метаданные
    created_at: str = ""
    updated_at: str = ""
    finalized_at: str | None = None


# ── Discussion Messages ─────────────────────────────────────────


class StudioMessage(BaseModel):
    """Сообщение в discussion. НЕ описание — история процесса.

    Discussion = история разговора пользователя с Arkaim.
    НЕ смешивать с StudioVersion (состояние описаний).
    """
    model_config = _MODEL_CONFIG

    message_id: str = ""
    session_id: str = ""
    role: StudioMessageRole = StudioMessageRole.USER
    content: str = ""

    # Если сообщение создало новую версию
    created_version_id: str | None = None

    created_at: str = ""


# ── User Modification ───────────────────────────────────────────


class UserModification(BaseModel):
    """Трекинг одного изменения пользователем.

    Каждое изменение фиксируется: target (image/video/scenario),
    field_path, old_value, new_value, reason.
    """
    model_config = _MODEL_CONFIG

    target: str = ""          # "image_description" | "video_description" | "video_scenario"
    field_path: str = ""      # "atmosphere", "camera.shot_type", etc.
    old_value: str = ""
    new_value: str = ""
    reason: str = ""
    timestamp: str = ""


# ── Studio Version ──────────────────────────────────────────────


class StudioVersion(BaseModel):
    """Снимок трёх описаний. НЕ discussion — это конкретное состояние.

    Каждое изменение создаёт новую версию (immutable).
    Версии связаны через parent_version_id (lineage).
    """
    model_config = _MODEL_CONFIG

    version_id: str = ""
    session_id: str = ""
    version_number: int = 0

    # ── Три описания сцены ──
    image_description: MediaPlan | None = None
    video_description: MediaPlan | None = None
    video_scenario: VideoScenario | None = None

    # ── Lineage ──
    parent_version_id: str | None = None
    derivation: str = "initial"  # initial | variation | adaptation

    # ── Пользовательские модификации ──
    user_modifications: list[UserModification] = Field(default_factory=list)

    # ── Статус ──
    is_active: bool = False
    is_final: bool = False

    # ── Метаданные ──
    created_by: str = "system"  # system | user | assistant
    created_at: str = ""
    note: str = ""


# ── Reference Asset ─────────────────────────────────────────────


class ReferenceAsset(BaseModel):
    """Reference-изображение, загруженное пользователем.

    Пользовательский вход. НЕ результат генерации.
    Привязан к сессии (не к версии — reference может быть использован в любой версии).
    """
    model_config = _MODEL_CONFIG

    asset_id: str = ""
    session_id: str = ""
    description: str = ""  # "такой свет", "такая композиция"
    source_type: str = "user_reference"
    created_at: str = ""


# ── Export Contract ──────────────────────────────────────────────


class ExportedReference(BaseModel):
    """Reference в export-контракте. Внешняя ссылка для arkaim-media.

    Не является частью MediaPlan — отдельная external reference.
    """
    model_config = _MODEL_CONFIG

    asset_id: str = ""
    description: str = ""
    file_url: str = ""


class StudioExport(BaseModel):
    """Export-контракт Studio → arkaim-media.

    Содержит три финальных описания + reference asset references.
    MediaPlan v0 не расширяется. VideoScenario — отдельный контракт.
    """
    model_config = _MODEL_CONFIG

    session_id: str = ""
    export_id: str = ""

    # Три финальных описания
    image_description: MediaPlan | None = None
    video_description: MediaPlan | None = None
    video_scenario: VideoScenario | None = None

    # Reference assets (внешние ссылки, НЕ поля описаний)
    references: list[ExportedReference] = Field(default_factory=list)

    # Метаданные
    version_lineage: list[str] = Field(default_factory=list)  # version_ids от initial до final
    exported_at: str = ""
