"""VideoIntelligence — создаёт VideoContext из VisualContext + shot plan."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from .visual_context import VisualContext
from .video_context import (
    VideoContext, CameraMovement, CharacterMotion,
    ObjectMotion, LightDynamics, TransitionSpec, RhythmSpec,
)

log = logging.getLogger("visual.video_intelligence")

_KNOWLEDGE_DIR = Path(__file__).parent / "VISUAL_KNOWLEDGE"


class VideoIntelligence:
    """Создаёт VideoContext для живого видео."""

    def __init__(self, knowledge_path: Path | None = None):
        self._knowledge = self._load(knowledge_path or _KNOWLEDGE_DIR)

    def _load(self, path: Path) -> dict:
        result = {}
        for name in ("CAMERA_LIBRARY", "VIDEO_RULES", "ATMOSPHERES"):
            f = path / f"{name}.json"
            if f.exists():
                result[name] = json.loads(f.read_text("utf-8-sig"))
        return result

    def create_video_context(
        self,
        ctx: VisualContext,
        shot_plan: list[dict] | None = None,
        duration_sec: float = 30.0,
    ) -> VideoContext:
        """VisualContext → VideoContext с motion, transitions, rhythm."""
        vctx = VideoContext.from_visual_context(ctx)

        # 1. Camera movement
        vctx.camera_movement = self._determine_camera_movement(ctx)

        # 2. Character motion
        vctx.character_motion = self._determine_character_motion(ctx)

        # 3. Object motion (fire, fog, wind, particles)
        vctx.object_motion = self._determine_object_motion(ctx)

        # 4. Light dynamics
        vctx.light_dynamics = self._determine_light_dynamics(ctx)

        # 5. Transitions
        vctx.transitions = self._determine_transitions(ctx, shot_plan)

        # 6. Duration and rhythm
        vctx.duration_sec = duration_sec
        vctx.rhythm = self._determine_rhythm(ctx)

        log.info("video_context_created duration=%.1f motion=%d objects=%d",
                 vctx.duration_sec, len(vctx.character_motion), len(vctx.object_motion))

        return vctx

    def _determine_camera_movement(self, ctx: VisualContext) -> CameraMovement:
        """Определить движение камеры по контексту."""
        camera_lib = self._knowledge.get("CAMERA_LIBRARY", {})
        movements = camera_lib.get("movements", {})

        # По умолчанию
        movement_type = "slow_dolly_in"

        # Эмоция → движение
        if "conflict" in ctx.emotion.name or "конфликт" in ctx.emotion.name:
            movement_type = "handheld"
        elif "sacred" in ctx.emotion.name or "ceremonial" in ctx.emotion.name:
            movement_type = "crane_up"
        elif ctx.scene.title and ("panoram" in ctx.scene.title.lower() or "взгляд" in ctx.scene.title.lower()):
            movement_type = "slow_pan"

        move_data = movements.get(movement_type, {})
        return CameraMovement(
            type=movement_type,
            speed=move_data.get("speed", "slow"),
            effect=move_data.get("effect", ""),
        )

    def _determine_character_motion(self, ctx: VisualContext) -> list[CharacterMotion]:
        """Определить движение персонажей."""
        motions = []
        for char in ctx.characters:
            action = "standing still"
            if "warrior" in char.appearance_summary.lower():
                action = "alert stance, hand on weapon"
            elif "wise" in char.appearance_summary.lower() or "учитель" in char.name.lower():
                action = "slow deliberate gestures"

            motions.append(CharacterMotion(
                character_id=char.character_id,
                action=action,
                speed="slow",
                emotion=ctx.emotion.name,
            ))
        return motions

    def _determine_object_motion(self, ctx: VisualContext) -> list[ObjectMotion]:
        """Определить движение объектов среды."""
        motions = []

        # Всегда: môi trường motion
        if ctx.atmosphere.fog:
            motions.append(ObjectMotion(object_type="fog", intensity="subtle", direction="rising"))
        if ctx.atmosphere.particles:
            motions.append(ObjectMotion(object_type="particles", intensity="subtle", direction="floating"))
        if ctx.atmosphere.wind and ctx.atmosphere.wind != "still":
            motions.append(ObjectMotion(object_type="wind", intensity="gentle", direction="flowing"))

        # Огонь если есть
        if "fire" in ctx.atmosphere.light.lower() or "fire" in ctx.atmosphere.sound.lower():
            motions.append(ObjectMotion(object_type="fire", intensity="flickering", direction="upward"))

        # Вода если есть
        if ctx.location.landscape.water:
            motions.append(ObjectMotion(object_type="water", intensity="gentle", direction="flowing"))

        return motions

    def _determine_light_dynamics(self, ctx: VisualContext) -> LightDynamics:
        """Определить динамику света."""
        return LightDynamics(
            start_color_temperature=ctx.atmosphere.color_temperature or "warm",
            end_color_temperature=ctx.atmosphere.color_temperature or "warm",
            intensity_change="gradual",
        )

    def _determine_transitions(self, ctx: VisualContext, shot_plan: list[dict] | None) -> list[TransitionSpec]:
        """Определить переходы."""
        transitions = []
        rules = self._knowledge.get("VIDEO_RULES", {}).get("transition_rules", {})

        # Default transitions
        transitions.append(TransitionSpec(type="fade_from_black", duration_sec=1.0, description="opening"))
        transitions.append(TransitionSpec(type="crossfade", duration_sec=1.5, description="between shots"))
        transitions.append(TransitionSpec(type="fade_to_black", duration_sec=1.0, description="closing"))

        return transitions

    def _determine_rhythm(self, ctx: VisualContext) -> RhythmSpec:
        """Определить ритм."""
        rules = self._knowledge.get("VIDEO_RULES", {}).get("rhythm", {})

        pace = "medium"
        if "conflict" in ctx.emotion.name or "конфликт" in ctx.emotion.name:
            pace = "fast"
        elif "sacred" in ctx.emotion.name or "ceremonial" in ctx.emotion.name:
            pace = "slow"

        return RhythmSpec(pace=pace, beat_duration=3.0 if pace == "medium" else 2.0)
