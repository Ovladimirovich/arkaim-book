"""VideoScenarioBuilder — строит VideoScenario из Arkaim Description System.

Phase 1A. Minimal builder for Full Video Scenario.

Pipeline:
  VisualContext + VideoIntelligence + WorldModel → VideoScenarioBuilder → VideoScenario

Каждый элемент сценария несёт provenance, указывающий на источник данных.
Directorial-поля (inferred) формируются на основе existing data, НЕ выдумываются.

VideoScenarioBuilder НЕ:
  - придумывает новый мир;
  - создаёт факты о персонажах;
  - подменяет World Model / World Engine;
  - зависит от Studio;
  - содержит media execution.

ADR compliance: ADR_ARKAIM_MEDIA_BOUNDARY, ADR_MEDIA_PLAN_V0.
"""
from __future__ import annotations

import uuid
import logging

from visual.visual_context import VisualContext
from visual.video_context import VideoContext
from visual.video_intelligence import VideoIntelligence

from .scenario_schemas import (
    VideoScenario,
    ScenarioShot,
    ScenarioCharacterAction,
    ScenarioEnvironmentAction,
    ScenarioRhythm,
    ScenarioSoundDesign,
    ScenarioProvenance,
    SCENARIO_VERSION,
)

from visual.scene_context import ProvenanceRef, SourceRefs, TemporalSceneRef
from media_plan.schemas import scene_ref_from_context

log = logging.getLogger("studio.scenario_builder")

# ── Defaults for directorial layer ──

_EMOTION_TO_PACE = {
    "conflict": "fast",
    "sacred": "slow",
    "ceremonial": "slow",
    "warm_intimate": "slow",
    "hopeful_golden": "medium",
    "dark_mystical": "slow",
    "dramatic_contrast": "fast",
    "neutral": "medium",
}

_EMOTION_TO_SHOT_SEQUENCE = {
    "conflict": ["establishing", "medium", "close-up", "detail", "wide"],
    "sacred": ["establishing", "wide", "medium", "close-up", "wide"],
    "ceremonial": ["establishing", "wide", "medium", "close-up", "wide"],
    "warm_intimate": ["medium", "close-up", "detail", "medium"],
    "hopeful_golden": ["establishing", "wide", "medium", "close-up"],
    "dark_mystical": ["establishing", "detail", "medium", "close-up", "wide"],
    "neutral": ["establishing", "medium", "wide"],
}


def _new_scenario_id() -> str:
    return f"scenario_{uuid.uuid4().hex[:12]}"


def _provenance(source: str, source_id: str = "", confidence: float = 1.0) -> ScenarioProvenance:
    return ScenarioProvenance(source=source, source_id=source_id, confidence=confidence)


class VideoScenarioBuilder:
    """Строит VideoScenario из VisualContext + VideoIntelligence.

    Не зависит от Studio. Не содержит media execution.
    Используется Studio как первый consumer, но может использоваться
    и вне Studio (API endpoint, CLI, etc.).
    """

    def __init__(self, video_intelligence: VideoIntelligence | None = None):
        self._vi = video_intelligence or VideoIntelligence()

    def build(
        self,
        ctx: VisualContext,
        duration_sec: float = 30.0,
    ) -> VideoScenario:
        """VisualContext → VideoScenario.

        Каждый элемент помечен provenance:
          - "visual_knowledge" — данные из VISUAL_KNOWLEDGE / genome
          - "video_intelligence" — derived из VideoIntelligence
          - "inferred" — directorial logic (на основе existing data)
        """
        # 1. Получаем VideoContext через существующий VideoIntelligence
        vctx = self._vi.create_video_context(ctx, duration_sec=duration_sec)

        # 2. Provenance из SceneContext
        source_refs, temporal, provenance = scene_ref_from_context(ctx)

        # 3. Shots (directorial sequence)
        shots = self._build_shots(ctx, vctx)

        # 4. Character arcs (from VideoIntelligence character_motion)
        character_arcs = self._build_character_arcs(ctx, vctx)

        # 5. Environment actions (from VideoIntelligence object_motion)
        environment_actions = self._build_environment_actions(vctx)

        # 6. Rhythm (from VideoIntelligence rhythm)
        rhythm = self._build_rhythm(ctx, vctx)

        # 7. Sound design (from VisualContext atmosphere)
        sound_design = self._build_sound_design(ctx)

        # 8. Synopsis and direction notes (directorial, based on existing data)
        synopsis = self._build_synopsis(ctx)
        direction_notes = self._build_direction_notes(ctx, vctx)

        scenario = VideoScenario(
            scenario_id=_new_scenario_id(),
            scenario_version=SCENARIO_VERSION,
            scene_id=ctx.scene.scene_id,
            title=ctx.scene.title,
            synopsis=synopsis,
            total_duration_sec=duration_sec,
            shots=shots,
            direction_notes=direction_notes,
            rhythm=rhythm,
            character_arcs=character_arcs,
            environment_actions=environment_actions,
            sound_design=sound_design,
            source_refs=source_refs,
            temporal_context=temporal,
            provenance=provenance,
        )

        log.info(
            "video_scenario_built scene=%s shots=%d chars=%d env=%d duration=%.1f",
            ctx.scene.scene_id, len(shots), len(character_arcs),
            len(environment_actions), duration_sec,
        )

        return scenario

    # ── Shot sequence (directorial layer) ──

    def _build_shots(
        self,
        ctx: VisualContext,
        vctx: VideoContext,
    ) -> list[ScenarioShot]:
        """Построить последовательность планов.

        Directorial logic: типы планов определяются эмоцией сцены.
        Содержание каждого плана — из VisualContext + VideoIntelligence.
        """
        emotion = ctx.emotion.name
        shot_types = _EMOTION_TO_SHOT_SEQUENCE.get(emotion, _EMOTION_TO_SHOT_SEQUENCE["neutral"])

        shots = []
        base_duration = max(2.0, vctx.duration_sec / len(shot_types))

        for i, shot_type in enumerate(shot_types):
            # Camera action from VideoIntelligence
            camera_action = vctx.camera_movement.type if i > 0 else "static"

            # Character actions in this shot
            char_actions = []
            for cm in vctx.character_motion:
                char_name = ""
                for c in ctx.characters:
                    if c.character_id == cm.character_id:
                        char_name = c.name
                        break
                char_actions.append(ScenarioCharacterAction(
                    character_id=cm.character_id,
                    character_name=char_name,
                    action=cm.action,
                    emotion=cm.emotion,
                    timing=self._shot_timing(i, len(shot_types)),
                    provenance=_provenance("video_intelligence", cm.character_id, 0.9),
                ))

            # Environment actions in this shot
            env_actions = []
            for om in vctx.object_motion:
                env_actions.append(ScenarioEnvironmentAction(
                    element=om.object_type,
                    action=om.direction,
                    intensity=om.intensity,
                    provenance=_provenance("video_intelligence", om.object_type, 0.9),
                ))

            # Transition
            transition = "cut"
            if i < len(vctx.transitions):
                transition = vctx.transitions[i].type

            shot = ScenarioShot(
                shot_id=f"shot_{i+1:03d}",
                order=i,
                shot_type=shot_type,
                description=self._shot_description(shot_type, ctx, i),
                duration_sec=round(base_duration, 1),
                camera_action=camera_action,
                camera_angle=ctx.camera.angle,
                character_actions=char_actions,
                environment_actions=env_actions,
                transition_to_next=transition,
                lighting_note=ctx.lighting.description or ctx.atmosphere.light,
                mood_note=ctx.emotion.suffix or "",
                provenance=_provenance("inferred", ctx.scene.scene_id, 0.8),
            )
            shots.append(shot)

        return shots

    def _shot_description(self, shot_type: str, ctx: VisualContext, index: int) -> str:
        """Directorial описание плана на основе existing data."""
        loc_name = ctx.location.name or "scene"
        char_names = ", ".join(c.name for c in ctx.characters[:3]) or "characters"

        descriptions = {
            "establishing": f"Establishing shot of {loc_name}, setting the scene",
            "wide": f"Wide view of {loc_name} with {char_names}",
            "medium": f"Medium shot focusing on {char_names}",
            "close-up": f"Close-up detail of {char_names} in {ctx.atmosphere.name} atmosphere",
            "detail": f"Detail shot of environment — {ctx.atmosphere.particles or ctx.atmosphere.fog or 'atmospheric elements'}",
        }
        return descriptions.get(shot_type, f"{shot_type} shot of {loc_name}")

    def _shot_timing(self, index: int, total: int) -> str:
        if index == 0:
            return "opening"
        if index == total - 1:
            return "closing"
        return "throughout"

    # ── Character arcs (from VideoIntelligence) ──

    def _build_character_arcs(
        self,
        ctx: VisualContext,
        vctx: VideoContext,
    ) -> list[ScenarioCharacterAction]:
        """Действия персонажей во времени.

        Source: VideoIntelligence.character_motion (derived) + VisualContext.characters (existing).
        """
        arcs = []
        for cm in vctx.character_motion:
            char_name = ""
            for c in ctx.characters:
                if c.character_id == cm.character_id:
                    char_name = c.name
                    break
            arcs.append(ScenarioCharacterAction(
                character_id=cm.character_id,
                character_name=char_name,
                action=cm.action,
                emotion=cm.emotion,
                timing="throughout",
                provenance=_provenance("video_intelligence", cm.character_id, 0.9),
            ))
        return arcs

    # ── Environment actions (from VideoIntelligence) ──

    def _build_environment_actions(self, vctx: VideoContext) -> list[ScenarioEnvironmentAction]:
        """Динамика среды.

        Source: VideoIntelligence.object_motion (derived) + VisualContext.atmosphere (existing).
        """
        actions = []
        for om in vctx.object_motion:
            actions.append(ScenarioEnvironmentAction(
                element=om.object_type,
                action=om.direction,
                intensity=om.intensity,
                provenance=_provenance("video_intelligence", om.object_type, 0.9),
            ))
        return actions

    # ── Rhythm (from VideoIntelligence) ──

    def _build_rhythm(self, ctx: VisualContext, vctx: VideoContext) -> ScenarioRhythm:
        """Ритм и pacing.

        Source: VideoIntelligence._determine_rhythm() (derived) + VIDEO_RULES.json (existing).
        """
        return ScenarioRhythm(
            pace=vctx.rhythm.pace,
            beat_duration_sec=vctx.rhythm.beat_duration,
            mood_arc=f"Based on {ctx.emotion.name} emotion",
            provenance=_provenance("video_intelligence", "rhythm", 0.9),
        )

    # ── Sound design (from VisualContext) ──

    def _build_sound_design(self, ctx: VisualContext) -> ScenarioSoundDesign:
        """Звуковой дизайн.

        Source: VisualContext.atmosphere.sound + VisualContext.location.sound (existing).
        Это семантическое описание, НЕ execution-параметры.
        """
        return ScenarioSoundDesign(
            atmosphere_sounds=ctx.atmosphere.sound or "",
            location_sounds=ctx.location.sound or "",
            silence_notes="",
            provenance=_provenance("visual_knowledge", "atmosphere+location", 1.0),
        )

    # ── Synopsis and direction (directorial, based on existing data) ──

    def _build_synopsis(self, ctx: VisualContext) -> str:
        """Краткое описание сцены (2-3 предложения).

        Source: VisualContext.scene (existing) + directorial framing.
        """
        parts = []
        if ctx.scene.title:
            parts.append(ctx.scene.title)
        if ctx.scene.description:
            parts.append(ctx.scene.description)
        if ctx.location.name:
            parts.append(f"Location: {ctx.location.name}")
        if ctx.emotion.name != "neutral":
            parts.append(f"Mood: {ctx.emotion.name}")
        return ". ".join(parts) if parts else "Scene description"

    def _build_direction_notes(self, ctx: VisualContext, vctx: VideoContext) -> str:
        """Общие режиссёрские указания.

        Derived from: VisualContext.emotion + VideoIntelligence output.
        """
        notes = []
        if ctx.emotion.name != "neutral":
            notes.append(f"Overall emotion: {ctx.emotion.name} — {ctx.emotion.suffix}")
        if vctx.rhythm.pace != "medium":
            notes.append(f"Pacing: {vctx.rhythm.pace}")
        if vctx.light_dynamics.intensity_change:
            notes.append(f"Light dynamics: {vctx.light_dynamics.intensity_change}")
        return ". ".join(notes) if notes else "Standard cinematic approach"
