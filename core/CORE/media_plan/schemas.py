"""MediaPlan v0 — доменный контракт «задание на генерацию» (MD-3).

MD-3 (MediaPlan Contract v0). ADR_MEDIA_PLAN_V0:
  - MediaPlan — отдельный доменный контракт, НЕ новый SceneContext;
  - строится ТОЛЬКО из canonical Scene Context (VisualContext + MD-2
    scene_extras: temporal/source_refs/integrity);
  - provenance наследуется от сцены/эпохи, lineage связывает
    regenerate/derived планы с родителем;
  - в контракте НЕТ execution-семантики: model/checkpoint/steps/cfg/
    sampler/seed/workflow/node-graph/provider/backend/ComfyUI —
    запрещены (ADR_ARKAIM_MEDIA_BOUNDARY Decision 3, тест-инвариант);
  - audio — extension point: media_kind="audio" зарезервирован,
    схема НЕ определяется (прямой запрет ADR_MEDIA_PLAN_V0 D2).


"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from visual.visual_context import VisualContext  # canonical Scene Context
from visual.scene_context import (
    ProvenanceRef,
    SourceRefs,
    TemporalSceneRef,
)

PLAN_VERSION = "0.1.0"

# Строгий контракт: посторонние поля запрещены на уровне pydantic —
# execution-поля (model/steps/seed/…) нельзя даже протолкнуть через
# конструктор (ADR_MEDIA_PLAN_V0 Decision 2; тест-инвариант).
_MODEL_CONFIG = ConfigDict(extra="forbid")


class MediaKind:
    """Виды носителей плана (значения media_kind).

    audio — ЗАРЕЗЕРВИРОВАН как extension point: схема AudioPlan
    не определяется и не реализуется (ADR_MEDIA_PLAN_V0 Decision 2).
    """

    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"  # extension point — только зарезервированное значение


class PlanLineage(BaseModel):
    """Родословная плана (ADR_MEDIA_PLAN_V0 Decision 3).

    Lineage — это родословная ЗАДАНИЯ, а не storage/execution
    metadata: здесь нет статусов исполнения, файлов, очередей,
    attempt-счётчиков. Regenerate/derived план обязан ссылаться
    на родителя; independent-план создаётся только когда родителя
    действительно нет (первый план сцены).
    """

    parent_plan_id: str | None = None
    derivation: str = "initial"  # initial | regenerate | variation | adaptation | …
    created_from: str = "scene_context"  # класс источника: scene_context | film_shot | epoch | …

    @property
    def is_derived(self) -> bool:
        """True, если план — производный (есть родитель или не-initial derivation)."""
        return self.parent_plan_id is not None or self.derivation != "initial"


class CharacterPlan(BaseModel):
    """Персонаж в плане — проекция CharacterVisualContext (без копирования данных genome).

    Идентификатор + краткое визуальное описание для исполнителя;
    полные описания остаются в genome (единственный источник).
    """

    character_id: str = ""
    name: str = ""
    appearance_summary: str = ""
    expression: str = ""
    pose: str = ""


class LocationRef(BaseModel):
    """Ссылка на локацию — идентификаторы и АТМОСФЕРНАЯ проекция, не копия LocationContext."""

    location_id: str = ""
    name: str = ""
    type: str = ""
    architecture_style: str = ""
    landscape_terrain: str = ""


class CameraPlan(BaseModel):
    """Камера плана — проекция CameraContext (shot/angle/movement — смысл, не механика)."""

    shot_type: str = "wide"
    angle: str = "eye_level"
    movement: str = "static"
    composition: str = ""


class ShotPlan(BaseModel):
    """Кадр video-последовательности — проекция ShotSpec/ShotVersion (без дублей классов)."""

    shot_id: str = ""
    prompt: str = ""
    duration_sec: float = 2.0
    camera: CameraPlan = Field(default_factory=CameraPlan)
    lighting: str = ""
    palette: list[str] = Field(default_factory=list)


class ContinuityRef(BaseModel):
    """Ссылка на требование непрерывности — проекция ContinuityEngine.apply(ctx, project_id, shot_index).

    Хранит только ИДЕНТИФИКАТОРЫ проекта/шота; сам ContinuityState
    живёт в visual-слое (media-сторона читает ссылку, не состояние).
    """

    project_id: str = ""
    shot_index: int = 0


class MotionPlan(BaseModel):
    """Движение в video-плане — проекция VideoContext-типов (CameraMovement/CharacterMotion)."""

    camera_motion: str = "static"  # CameraMovement.type
    character_actions: list[dict] = Field(default_factory=list)  # CharacterMotion-проекции
    transitions: list[dict] = Field(default_factory=list)  # TransitionSpec-проекции


class MediaPlan(BaseModel):
    """MediaPlan v0 — единственный канонический доменный контракт задания.

    Спроцирован из canonical Scene Context (VisualContext + scene_extras).
    Поле — всегда смысл; НИКОГДА execution (см. BANNED_FIELDS ниже
    и тест-инвариант test_md3_media_plan). extra="forbid": любые
    посторонние поля (включая execution) отвергаются при создании.
    """

    model_config = _MODEL_CONFIG

    # ── идентификация ──
    plan_id: str = ""
    plan_version: str = PLAN_VERSION
    media_kind: str = MediaKind.IMAGE  # image | video | audio(extension)

    # ── смысловая проекция SceneContext ──
    intent: str = "key_frame"
    structured_prompt: str = ""
    prompt: str = ""
    negative_constraints: list[str] = Field(default_factory=list)
    characters: list[CharacterPlan] = Field(default_factory=list)
    location: LocationRef = Field(default_factory=LocationRef)
    visual_style: str = "cinematic_fantasy"
    atmosphere: str = "neutral"
    camera: CameraPlan = Field(default_factory=CameraPlan)
    constraints: list[str] = Field(default_factory=list)

    # ── ссылки и происхождение (наследование MD-2) ──
    source_refs: SourceRefs = Field(default_factory=SourceRefs)
    temporal_context: TemporalSceneRef | None = None
    provenance: list[ProvenanceRef] = Field(default_factory=list)

    # ── родословная ──
    lineage: PlanLineage = Field(default_factory=PlanLineage)

    # ── video-only (заполняется при media_kind=video) ──
    duration_sec: float = 8.0
    fps: int = 24
    sequence: list[ShotPlan] = Field(default_factory=list)
    motion: MotionPlan = Field(default_factory=MotionPlan)
    temporal_consistency: ContinuityRef | None = None

    def to_dict(self) -> dict:
        """JSON-представление плана (для asset-записи/логов/экспорта)."""
        data = self.model_dump(mode="json")
        # SourceRefs/TemporalSceneRef — dataclass'ы: сериализуем отдельно.
        data["source_refs"] = self.source_refs.to_dict()
        if self.temporal_context is not None:
            data["temporal_context"] = _temporal_to_dict(self.temporal_context)
        if self.provenance:
            data["provenance"] = [
                {"category": p.category, "source": p.source, "confidence": p.confidence}
                for p in self.provenance
            ]
        return data


# ── запрет execution-семантики (ADR Decision 3 + ADR_MEDIA_PLAN_V0 D2) ──

BANNED_FIELDS = frozenset({
    "model", "checkpoint", "ckpt", "steps", "cfg", "sampler", "seed",
    "workflow", "node_graph", "nodegraph", "provider", "backend",
    "comfyui", "comfy_url", "lora", "loras", "denoise", "scheduler",
    "execution", "execution_settings", "quality",  # quality — мёртвый gap MP-F1
})


def _temporal_to_dict(ref: TemporalSceneRef) -> dict:
    """None-safe сериализация TemporalSceneRef (паттерн MD-2)."""
    return {
        "epoch_id": ref.epoch_id,
        "name_ru": ref.name_ru,
        "confidence": ref.confidence,
        "bounds_start": ref.bounds_start,
        "bounds_end": ref.bounds_end,
        "bounds_uncertainty": ref.bounds_uncertainty,
        "provenance": [
            {"category": p.category, "source": p.source, "confidence": p.confidence}
            for p in ref.provenance
        ],
        "event_count": ref.event_count,
        "character_count": ref.character_count,
        "technology_count": ref.technology_count,
    }


def verify_no_execution_fields(plan_class: type = MediaPlan) -> list[str]:
    """Проверить запрет-инвариант: BANNED ∩ поля MediaPlan = ∅.

    Возвращает список нарушений (пустой = инвариант соблюдён).
    Тест-хук: unit-тесты MD-3 вызывают эту функцию напрямую.
    """

    violations: list[str] = []
    seen: set[str] = set()

    def _walk(model: type, prefix: str = "") -> None:
        if model in ({}, ):  # unreachable guard
            return
        key = f"{model.__module__}.{model.__name__}"
        if key in seen:
            return
        seen.add(key)
        for name, f in getattr(model, "model_fields", {}).items():
            full = f"{prefix}{name}"
            leaf = name.rsplit("_", 1)[-1]  # provider_name → provider
            for candidate in (name, leaf):
                if candidate in BANNED_FIELDS:
                    violations.append(full)
            ann = getattr(f, "annotation", None)
            _walk_annotation(ann, full)

    def _walk_annotation(ann, prefix: str) -> None:
        if ann is None:
            return
        origin = getattr(ann, "__origin__", None)
        if origin is not None:
            for arg in getattr(ann, "__args__", ()):
                _walk_annotation(arg, prefix)
            return
        if isinstance(ann, type) and issubclass(ann, BaseModel):
            _walk(ann, f"{prefix}.")

    _walk(plan_class)
    return violations


def scene_ref_from_context(ctx: VisualContext) -> tuple[SourceRefs, TemporalSceneRef | None, list[ProvenanceRef]]:
    """Извлечь MD-2-ссылки из canonical Scene Context (без мутации ctx)."""
    extras = getattr(ctx, "scene_extras", None)
    if extras is None:
        return SourceRefs(), None, []
    temporal = extras.temporal if extras.temporal.is_temporal else None
    provenance = list(temporal.provenance) if temporal is not None else []
    return extras.source_refs, temporal, provenance
