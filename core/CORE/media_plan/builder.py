"""MediaPlanBuilder — детерминированная проекция SceneContext → MediaPlan (MD-3.1).

ADR_MEDIA_PLAN_V0:
  - Builder строит план ТОЛЬКО из canonical Scene Context
    (VisualContext + scene_extras) — никаких dict-сцен/VisualAsset
    на входе;
  - проекция чистая: без LLM, без HTTP, без providers;
  - structured_prompt/prompt/negative — рендер PromptComposer'ом
    (существующая механика, текст НЕ меняется — контракты промптов
    заморожены решением владельца PA-F1/MP-F12);
  - provenance/temporal/source_refs наследуются 1:1 из scene_extras;
  - regenerate/derived — через parent_plan_id (lineage), план
    НЕ мутируется: создается новый (immutable-паттерн MD-2).

Audio (media_kind="audio") — extension point: builder НЕ строит
audio-планы (схема не определена; прямой запрет ADR_MEDIA_PLAN_V0 D2).
"""
from __future__ import annotations

import uuid

from visual.visual_context import VisualContext
from visual.prompt_composer import PromptComposer
from visual.video_context import CameraMovement, CharacterMotion, TransitionSpec

from .schemas import (
    CameraPlan,
    CharacterPlan,
    ContinuityRef,
    LocationRef,
    MediaKind,
    MediaPlan,
    MotionPlan,
    PlanLineage,
    ShotPlan,
    scene_ref_from_context,
)


def _new_plan_id() -> str:
    return f"plan_{uuid.uuid4().hex[:12]}"


class MediaPlanBuilder:
    """Строит MediaPlan из SceneContext (единственный канонический путь плана)."""

    def __init__(self, generator: str = "comfyui"):
        # generator — выбор ПРОМПТ-ШАБЛОНА (comfyui/flux/runway/kling/hailuo),
        # НЕ выбор провайдера: механика рендера текста, существующая
        # с MD-2 (путь D: PromptComposer default=comfyui; шаблона "base"
        # не существует — MD3_PRE §2.1). Никакой execution-семантики.
        self._composer = PromptComposer(generator=generator)

    # ── public API ──

    def build_image_plan(
        self,
        ctx: VisualContext,
        intent: str = "key_frame",
        style_override: str | None = None,
        custom_prompt: str | None = None,
        parent_plan_id: str | None = None,
        derivation: str = "initial",
        created_from: str = "scene_context",
    ) -> MediaPlan:
        """Сцена → image-план (главный путь A/C/D/E-маршрутов)."""
        return self._build_plan(
            ctx,
            media_kind=MediaKind.IMAGE,
            intent=intent,
            style_override=style_override,
            custom_prompt=custom_prompt,
            parent_plan_id=parent_plan_id,
            derivation=derivation,
            created_from=created_from,
        )

    def build_video_plan(
        self,
        ctx: VisualContext,
        intent: str = "key_frame",
        style_override: str | None = None,
        duration_sec: float = 8.0,
        fps: int = 24,
        shots: list[ShotPlan] | None = None,
        camera_motion: CameraMovement | None = None,
        character_actions: list[CharacterMotion] | None = None,
        transitions: list[TransitionSpec] | None = None,
        continuity: ContinuityRef | None = None,
        parent_plan_id: str | None = None,
        derivation: str = "initial",
        created_from: str = "scene_context",
    ) -> MediaPlan:
        """Сцена → video-план (video-поля — проекция VideoContext-типов)."""
        plan = self._build_plan(
            ctx,
            media_kind=MediaKind.VIDEO,
            intent=intent,
            style_override=style_override,
            custom_prompt=None,
            parent_plan_id=parent_plan_id,
            derivation=derivation,
            created_from=created_from,
        )
        plan.duration_sec = duration_sec
        plan.fps = fps
        plan.sequence = shots or []
        plan.motion = MotionPlan(
            camera_motion=camera_motion.type if camera_motion else "static",
            character_actions=[
                {
                    "character_id": m.character_id,
                    "action": m.action,
                    "speed": m.speed,
                    "emotion": m.emotion,
                }
                for m in (character_actions or [])
            ],
            transitions=[
                {"type": t.type, "duration_sec": t.duration_sec, "description": t.description}
                for t in (transitions or [])
            ],
        )
        plan.temporal_consistency = continuity
        return plan

    # ── internal ──

    def _build_plan(
        self,
        ctx: VisualContext,
        media_kind: str,
        intent: str,
        style_override: str | None,
        custom_prompt: str | None,
        parent_plan_id: str | None,
        derivation: str,
        created_from: str,
    ) -> MediaPlan:
        # 1. Промпты — существующая composer-механика (текст заморожен).
        structured_prompt = self._composer.compose(ctx)
        negative = self._composer.compose_negative(ctx)

        # 2. Смысловые проекции измерений VisualContext.
        characters = [
            CharacterPlan(
                character_id=c.character_id,
                name=c.name,
                appearance_summary=c.appearance_summary,
                expression="",
                pose="",
            )
            for c in ctx.characters
        ]
        location = LocationRef(
            location_id=ctx.location.location_id,
            name=ctx.location.name,
            type=ctx.location.type,
            architecture_style=ctx.location.architecture.style,
            landscape_terrain=ctx.location.landscape.terrain,
        )
        camera = CameraPlan(
            shot_type=ctx.camera.shot_type,
            angle=ctx.camera.angle,
            movement=ctx.camera.movement,
            composition=ctx.camera.composition,
        )

        # 3. MD-2-наследование: source_refs/temporal/provenance 1:1.
        source_refs, temporal, provenance = scene_ref_from_context(ctx)

        # 4. Prompt: custom (film-шот/эпоха) или composer-проекция.
        #    PA-F1-вердикт: A/B-маршруты рендерят текст прежним контрактом;
        #    custom_prompt (E) замещает только текст, смысл остаётся из ctx.
        prompt = custom_prompt if custom_prompt else structured_prompt

        return MediaPlan(
            plan_id=_new_plan_id(),
            media_kind=media_kind,
            intent=intent,
            structured_prompt=structured_prompt,
            prompt=prompt,
            negative_constraints=_split_negative(negative),
            characters=characters,
            location=location,
            visual_style=style_override or ctx.style.name,
            atmosphere=ctx.atmosphere.name,
            camera=camera,
            constraints=list(ctx.scene.meaning_tags),
            source_refs=source_refs,
            temporal_context=temporal,
            provenance=provenance,
            lineage=PlanLineage(
                parent_plan_id=parent_plan_id,
                derivation=derivation,
                created_from=created_from,
            ),
        )


def _split_negative(negative: str) -> list[str]:
    """Строка negative → список смысловых запретов (без дубликатов)."""
    if not negative:
        return []
    parts = [p.strip() for p in negative.split(",")]
    seen: set[str] = set()
    result: list[str] = []
    for p in parts:
        if p and p not in seen:
            seen.add(p)
            result.append(p)
    return result
