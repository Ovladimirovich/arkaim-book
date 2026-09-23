"""VisualContext — единый объект контекста для всех генераторов."""
from __future__ import annotations

from dataclasses import dataclass, field
from .visual_models import (
    SceneContext, LocationContext, EnvironmentContext, LightingContext,
    PaletteContext, AtmosphereContext, SymbolContext, HistoricalContext,
    CameraContext, StyleContext, EmotionContext, CharacterVisualContext,
    NegativePromptContext, ArchitectureContext, LandscapeContext,
)


@dataclass
class VisualContext:
    """Единый источник истины для визуальной генерации.

    Содержит всё что нужно для генерации изображения или видео:
    сцену, локацию, архитектуру, окружение, освещение, палитру,
    атмосферу, символику, исторический контекст, камеру, стиль,
    эмоцию, персонажей и negative prompt.

    MD-2 (Scene Context Consolidation): канонический Scene Context = этот
    класс + scene_extras (temporal/source_refs/integrity). Отдельный
    параллельный SceneContext-класс НЕ создаётся — поле additive,
    существующие 15 измерений не меняются. scene_extras всегда не-None
    после фабрики MD-2 (SceneContextExtras), media-neutral: execution-полей
    (model/steps/seed/workflow/provider) здесь нет и быть не может.
    """
    scene: SceneContext = field(default_factory=SceneContext)
    location: LocationContext = field(default_factory=LocationContext)
    architecture: ArchitectureContext = field(default_factory=ArchitectureContext)
    landscape: LandscapeContext = field(default_factory=LandscapeContext)
    environment: EnvironmentContext = field(default_factory=EnvironmentContext)
    lighting: LightingContext = field(default_factory=LightingContext)
    palette: PaletteContext = field(default_factory=PaletteContext)
    atmosphere: AtmosphereContext = field(default_factory=AtmosphereContext)
    symbols: list[SymbolContext] = field(default_factory=list)
    historical: HistoricalContext = field(default_factory=HistoricalContext)
    camera: CameraContext = field(default_factory=CameraContext)
    style: StyleContext = field(default_factory=StyleContext)
    emotion: EmotionContext = field(default_factory=EmotionContext)
    characters: list[CharacterVisualContext] = field(default_factory=list)
    negative_prompt: NegativePromptContext = field(default_factory=NegativePromptContext)
    scene_extras: "SceneContextExtras | None" = None

    def to_dict(self) -> dict:
        """Сериализация в dict (для JSON/логирования)."""
        from dataclasses import asdict
        result = asdict(self)
        # scene_extras сериализуется только если задан (legacy-потребители
        # VisualContext до MD-2 не знают об этом поле).
        result["scene_extras"] = (
            self.scene_extras.to_dict() if self.scene_extras is not None else None
        )
        return result

    def summary(self) -> str:
        """Краткое описание контекста для логов."""
        parts = [
            f"scene={self.scene.title or self.scene.scene_id}",
            f"location={self.location.name or self.location.location_id}",
            f"time={self.environment.time_of_day}",
            f"emotion={self.emotion.name}",
            f"style={self.style.name}",
            f"chars={len(self.characters)}",
        ]
        if self.scene_extras is not None and self.scene_extras.temporal.is_temporal:
            parts.append(f"epoch={self.scene_extras.temporal.epoch_id}")
        return "VisualContext(" + ", ".join(parts) + ")"


from .scene_context import SceneContextExtras  # noqa: E402

