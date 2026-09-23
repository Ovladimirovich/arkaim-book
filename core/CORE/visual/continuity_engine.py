"""ContinuityEngine — обеспечивает консистентность между кадрами."""
from __future__ import annotations

import logging
from .visual_context import VisualContext
from .continuity_state import ContinuityState

log = logging.getLogger("visual.continuity_engine")


class ContinuityEngine:
    """Обеспечивает визуальную непрерывность между шотами."""

    def __init__(self):
        self._states: dict[str, ContinuityState] = {}  # project_id → state

    def apply(self, ctx: VisualContext, project_id: str, shot_index: int) -> VisualContext:
        """Применить непрерывность к контексту.

        Если это первый шот — просто сохраняем состояние.
        Если не первый — проверяем и корректируем.
        """
        prev = self._states.get(project_id)

        if prev and shot_index > 0:
            ctx = self._enforce_continuity(ctx, prev, shot_index)
            log.info("continuity_applied project=%s shot=%d", project_id, shot_index)
        else:
            log.info("continuity_init project=%s shot=%d", project_id, shot_index)

        # Сохраняем состояние
        state = ContinuityState()
        state.snapshot_from_context(ctx)
        self._states[project_id] = state

        return ctx

    def _enforce_continuity(self, ctx: VisualContext, prev: ContinuityState, shot_index: int) -> VisualContext:
        """Убедиться что архитектура, одежда, погода, освещение консистентны."""

        # 1. Architecture: same style unless explicitly changing
        if prev.architecture_style and not ctx.architecture.style:
            ctx.architecture.style = prev.architecture_style

        # 2. Characters: same appearance unless explicitly changed
        for char in ctx.characters:
            if char.character_id in prev.character_appearances:
                prev_appearance = prev.character_appearances[char.character_id]
                if not char.appearance_summary:
                    char.appearance_summary = prev_appearance
                # Не перезаписываем если уже есть описание — доверяем контексту

        # 3. Weather: gradual transitions
        if prev.weather and ctx.environment.weather == "clear" and prev.weather != "clear":
            # Плавный переход: не резко менять погоду
            ctx.environment.weather = prev.weather

        # 4. Lighting: consistent direction within scene
        if prev.lighting_angle and shot_index < 5:
            # В пределах одной сцены — сохраняем направление света
            ctx.lighting.direction = prev.lighting_angle

        # 5. Palette: maintain base palette
        if prev.palette_primary and not ctx.palette.primary:
            ctx.palette.primary = prev.palette_primary

        # 6. Atmosphere: same unless explicitly changing
        if prev.atmosphere_name and ctx.atmosphere.name == "neutral" and prev.atmosphere_name != "neutral":
            ctx.atmosphere.name = prev.atmosphere_name

        return ctx

    def reset(self, project_id: str):
        """Сбросить состояние для проекта."""
        self._states.pop(project_id, None)

    def get_state(self, project_id: str) -> ContinuityState | None:
        return self._states.get(project_id)
