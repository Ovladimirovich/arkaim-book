"""Kling шаблон промпта — для видео-генерации."""
from __future__ import annotations
from .base import PromptTemplate


class KlingTemplate(PromptTemplate):
    """Генерирует промпт для Kling AI (text-to-video)."""

    def render(self, ctx) -> str:
        parts = []

        if ctx.scene.title:
            parts.append(ctx.scene.title)

        # Kling: описательный стиль с акцентом на детали
        if ctx.architecture.style:
            parts.append(ctx.architecture.style)

        if ctx.lighting.description:
            parts.append(ctx.lighting.description)

        for char in ctx.characters:
            if char.appearance_summary:
                parts.append(char.appearance_summary)

        if ctx.atmosphere.fog:
            parts.append(ctx.atmosphere.fog)

        if ctx.camera.movement != "static":
            parts.append(f"smooth camera {ctx.camera.movement.replace('_', ' ')}")

        if ctx.emotion.visual:
            parts.append(ctx.emotion.visual)

        if ctx.palette.description:
            parts.append(ctx.palette.description)

        parts.append("cinematic quality, detailed, 4k")

        return ", ".join(parts)

    def render_negative(self, ctx) -> str:
        return "static, no motion, blurry, low quality, deformed"
