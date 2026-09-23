"""VideoScenario — semantic contract для Full Video Scenario (Phase 1A).

Полное сценарное описание сцены для arkaim-media.

VideoScenario — это НЕ execution-контракт: нет model/steps/seed/workflow/provider.
Это режиссёрское описание, построенное из Arkaim Description System:
  VisualContext + VideoIntelligence + World Model → VideoScenario.

Каждое существенное поле несёт provenance-ссылку на источник данных.
VideoScenario НЕ подменяет World Model / World Engine / систему описаний Arkaim:
он формулирует сценарный текст из уже существующих данных.

ADR compliance:
  - ADR_ARKAIM_MEDIA_BOUNDARY: VideoScenario не содержит execution-семантики.
  - ADR_MEDIA_PLAN_V0: MediaPlan v0 не расширяется; VideoScenario — отдельный контракт.
  - extra="forbid": посторонние поля (включая execution) отвергаются.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# Reuse existing provenance types from SceneContext
from visual.scene_context import ProvenanceRef, SourceRefs, TemporalSceneRef

SCENARIO_VERSION = "0.1.0"

_MODEL_CONFIG = ConfigDict(extra="forbid")


class ScenarioProvenance(BaseModel):
    """Provenance одного элемента сценария.

    Указывает, откуда пришла информация: из genome, из VISUAL_KNOWLEDGE,
    из VideoIntelligence (derived), или из directorial logic (inferred).
    """
    model_config = _MODEL_CONFIG

    source: str = ""        # "genome" | "visual_knowledge" | "video_intelligence" | "world_model" | "inferred"
    source_id: str = ""     # ID конкретного источника (scene_id, character_id, location_id)
    confidence: float = 1.0  # 0.0-1.0


class ScenarioCharacterAction(BaseModel):
    """Действие персонажа в определённый момент сценария.

    Источник: VideoIntelligence._determine_character_motion() (derived)
    + VisualContext.characters (existing).
    """
    model_config = _MODEL_CONFIG

    character_id: str = ""
    character_name: str = ""
    action: str = ""           # "alert stance, hand on weapon" / "slow deliberate gestures"
    emotion: str = ""          # "sacred" / "conflict" — из VisualContext.emotion.name
    timing: str = ""           # "throughout" / "opening" / "climax" — directorial
    provenance: ScenarioProvenance = Field(default_factory=ScenarioProvenance)


class ScenarioEnvironmentAction(BaseModel):
    """Действие/состояние среды (огонь, туман, ветер, вода).

    Источник: VideoIntelligence._determine_object_motion() (derived)
    + VisualContext.atmosphere (existing).
    """
    model_config = _MODEL_CONFIG

    element: str = ""          # "fog" | "fire" | "wind" | "water" | "particles"
    action: str = ""           # "rising" | "flickering" | "flowing"
    intensity: str = "subtle"  # "subtle" | "gentle" | "moderate" | "strong"
    provenance: ScenarioProvenance = Field(default_factory=ScenarioProvenance)


class ScenarioShot(BaseModel):
    """Один план (shot) в видеосценарии.

    Описывает что происходит в конкретный момент времени:
    тип плана, описание действия, движение камеры, действия персонажей.

    Источник: directorial logic (derived) + VideoIntelligence output + VisualContext.
    """
    model_config = _MODEL_CONFIG

    shot_id: str = ""
    order: int = 0
    shot_type: str = "medium_shot"         # wide | medium | close-up | detail | establishing
    description: str = ""                  # Что происходит в этом плане (directorial)
    duration_sec: float = 3.0
    camera_action: str = ""                # "slow dolly in" | "static" | "pan left" — из VideoIntelligence
    camera_angle: str = "eye_level"        # из VisualContext.camera.angle
    character_actions: list[ScenarioCharacterAction] = Field(default_factory=list)
    environment_actions: list[ScenarioEnvironmentAction] = Field(default_factory=list)
    transition_to_next: str = "cut"        # cut | dissolve | fade | crossfade
    lighting_note: str = ""                # из VisualContext.lighting
    mood_note: str = ""                    # directorial
    provenance: ScenarioProvenance = Field(default_factory=ScenarioProvenance)


class ScenarioRhythm(BaseModel):
    """Ритм и pacing сценария.

    Источник: VideoIntelligence._determine_rhythm() (derived)
    + VIDEO_RULES.json (existing knowledge).
    """
    model_config = _MODEL_CONFIG

    pace: str = "medium"           # slow | medium | fast
    beat_duration_sec: float = 3.0
    mood_arc: str = ""             # "от спокойствия к тревоге" — directorial
    provenance: ScenarioProvenance = Field(default_factory=ScenarioProvenance)


class ScenarioSoundDesign(BaseModel):
    """Звуковой дизайн сценария.

    Источник: VisualContext.atmosphere.sound (existing)
    + VisualContext.location.sound (existing)
    + VisualContext.environment (existing).

    Sound design — это НЕ execution-параметры (sample rate, codec).
    Это семантическое описание звуковой атмосферы сцены.
    """
    model_config = _MODEL_CONFIG

    atmosphere_sounds: str = ""    # "crackling fire, distant wind" — из VisualContext.atmosphere.sound
    location_sounds: str = ""      # "echoing stone halls" — из VisualContext.location.sound
    silence_notes: str = ""        # directorial: "moment of silence before action"
    provenance: ScenarioProvenance = Field(default_factory=ScenarioProvenance)


class VideoScenario(BaseModel):
    """Full Video Scenario — полное сценарное описание сцены.

    НЕ execution-контракт: нет model/steps/seed/workflow/provider.
    НЕ самостоятельная система описаний: строится из Arkaim Description System.
    НЕ подменяет World Model: использует существующие данные о мире.

    Каждое поле имеет provenance-ссылку на источник данных.
    Directorial-поля (inferred) помечены отдельно от data-driven (existing/derived).

    Pipeline: VisualContext + VideoIntelligence + WorldModel → VideoScenarioBuilder → VideoScenario
    """
    model_config = _MODEL_CONFIG

    # ── Идентификация ──
    scenario_id: str = ""
    scenario_version: str = SCENARIO_VERSION
    scene_id: str = ""              # Ссылка на сцену в genome

    # ── Общее описание сцены ──
    title: str = ""                 # из VisualContext.scene.title (existing)
    synopsis: str = ""              # directorial: краткое описание сцены (2-3 предложения)
    total_duration_sec: float = 30.0

    # ── Последовательность планов (temporal sequence) ──
    shots: list[ScenarioShot] = Field(default_factory=list)

    # ── Режиссёрские указания ──
    direction_notes: str = ""       # directorial: общие указания
    rhythm: ScenarioRhythm = Field(default_factory=ScenarioRhythm)

    # ── Персонажи (действия во времени) ──
    character_arcs: list[ScenarioCharacterAction] = Field(default_factory=list)

    # ── Среда (динамика окружения) ──
    environment_actions: list[ScenarioEnvironmentAction] = Field(default_factory=list)

    # ── Звуковой дизайн ──
    sound_design: ScenarioSoundDesign = Field(default_factory=ScenarioSoundDesign)

    # ── Ссылки и происхождение (наследование из SceneContext) ──
    source_refs: SourceRefs = Field(default_factory=SourceRefs)
    temporal_context: TemporalSceneRef | None = None
    provenance: list[ProvenanceRef] = Field(default_factory=list)

    def to_dict(self) -> dict:
        """JSON-представление сценария."""
        data = self.model_dump(mode="json")
        data["source_refs"] = self.source_refs.to_dict()
        if self.temporal_context is not None:
            data["temporal_context"] = {
                "epoch_id": self.temporal_context.epoch_id,
                "name_ru": self.temporal_context.name_ru,
                "confidence": self.temporal_context.confidence,
            }
        if self.provenance:
            data["provenance"] = [
                {"category": p.category, "source": p.source, "confidence": p.confidence}
                for p in self.provenance
            ]
        return data
