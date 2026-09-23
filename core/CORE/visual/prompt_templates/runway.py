"""Runway шаблон промпта — для видео-генерации."""
from __future__ import annotations
from .base import PromptTemplate


class RunwayTemplate(PromptTemplate):
    """Генерирует промпт для Runway ML (text-to-video)."""

    def render(self, ctx) -> str:
        parts = []

        # Runway: короткие, ёмкие промпты с акцентом на движение
        if ctx.scene.title:
            parts.append(ctx.scene.title)

        if ctx.camera.movement != "static":
            parts.append(f"camera {ctx.camera.movement.replace('_', ' ')}")

        if ctx.atmosphere.camera_dynamics:
            parts.append(ctx.atmosphere.camera_dynamics)

        for char in ctx.characters:
            if char.movement:
                parts.append(f"{char.name} {char.movement}")
            elif char.appearance_summary:
                parts.append(char.appearance_summary)

        if ctx.lighting.description:
            parts.append(ctx.lighting.description)

        if ctx.atmosphere.fog:
            parts.append(ctx.atmosphere.fog)
        if ctx.atmosphere.particles:
            parts.append(ctx.atmosphere.particles)

        if ctx.emotion.visual:
            parts.append(ctx.emotion.visual)

        parts.append("cinematic, high quality")

        return ", ".join(parts)

    def render_negative(self, ctx) -> str:
        return "static, still image, no movement, blurry, low quality"
