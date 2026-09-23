"""Hailuo шаблон промпта — для видео-генерации."""
from __future__ import annotations
from .base import PromptTemplate


class HailuoTemplate(PromptTemplate):
    """Генерирует промпт для Hailuo MiniMax (text-to-video)."""

    def render(self, ctx) -> str:
        parts = []

        if ctx.scene.title:
            parts.append(ctx.scene.title)

        if ctx.lighting.description:
            parts.append(ctx.lighting.description)

        for char in ctx.characters:
            if char.appearance_summary:
                parts.append(char.appearance_summary)

        if ctx.atmosphere.camera_dynamics:
            parts.append(ctx.atmosphere.camera_dynamics)

        if ctx.emotion.visual:
            parts.append(ctx.emotion.visual)

        parts.append("cinematic, high quality, detailed")

        return ", ".join(parts)

    def render_negative(self, ctx) -> str:
        return "static, blurry, low quality"
