"""VideoContext — расширение VisualContext для видео-генерации."""
from __future__ import annotations

from dataclasses import dataclass, field
from .visual_context import VisualContext
from .visual_models import CameraContext


@dataclass
class CameraMovement:
    """Движение камеры."""
    type: str = "static"
    speed: str = "slow"
    direction: str = ""
    effect: str = ""


@dataclass
class CharacterMotion:
    """Движение персонажа."""
    character_id: str = ""
    action: str = ""
    speed: str = "normal"
    emotion: str = ""


@dataclass
class ObjectMotion:
    """Движение объекта среды."""
    object_type: str = ""  # fire, fog, wind, water, particles
    intensity: str = "subtle"
    direction: str = ""


@dataclass
class LightDynamics:
    """Изменение света во времени."""
    start_color_temperature: str = ""
    end_color_temperature: str = ""
    direction_change: str = ""
    intensity_change: str = ""


@dataclass
class TransitionSpec:
    """Спецификация перехода."""
    type: str = "cut"
    duration_sec: float = 0.0
    description: str = ""


@dataclass
class RhythmSpec:
    """Ритм видео."""
    pace: str = "medium"
    beat_duration: float = 3.0
    pauses: list[float] = field(default_factory=list)


@dataclass
class VideoContext(VisualContext):
    """Расширенный контекст для видео-генерации.

    Содержит всё из VisualContext плюс:
    - движение камеры
    - движение персонажей
    - движение объектов среды
    - динамика света
    - переходы
    - ритм
    """
    camera_movement: CameraMovement = field(default_factory=CameraMovement)
    character_motion: list[CharacterMotion] = field(default_factory=list)
    object_motion: list[ObjectMotion] = field(default_factory=list)
    light_dynamics: LightDynamics = field(default_factory=LightDynamics)
    transitions: list[TransitionSpec] = field(default_factory=list)
    duration_sec: float = 5.0
    rhythm: RhythmSpec = field(default_factory=RhythmSpec)
    fps: int = 24

    @classmethod
    def from_visual_context(cls, ctx: VisualContext) -> "VideoContext":
        """Создать VideoContext из VisualContext."""
        return cls(
            scene=ctx.scene,
            location=ctx.location,
            architecture=ctx.architecture,
            landscape=ctx.landscape,
            environment=ctx.environment,
            lighting=ctx.lighting,
            palette=ctx.palette,
            atmosphere=ctx.atmosphere,
            symbols=ctx.symbols,
            historical=ctx.historical,
            camera=ctx.camera,
            style=ctx.style,
            emotion=ctx.emotion,
            characters=ctx.characters,
            negative_prompt=ctx.negative_prompt,
        )
