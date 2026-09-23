"""Flux шаблон промпта — для Flux models."""
from __future__ import annotations
from .base import PromptTemplate


class FluxTemplate(PromptTemplate):
    """Генерирует промпт для Flux (более описательный, natural language)."""

    def render(self, ctx) -> str:
        parts = []

        # Flux любит自然ные описания
        if ctx.scene.title:
            parts.append(ctx.scene.title)

        if ctx.architecture.style:
            parts.append(f"The architecture features {ctx.architecture.style}")

        if ctx.lighting.description:
            parts.append(f"The lighting is {ctx.lighting.description}")

        if ctx.atmosphere.fog:
            parts.append(f"{ctx.atmosphere.fog}")

        if ctx.emotion.visual:
            parts.append(f"The atmosphere is {ctx.emotion.visual}")

        for char in ctx.characters:
            if char.appearance_summary:
                parts.append(f"featuring {char.appearance_summary}")

        if ctx.landscape.terrain:
            parts.append(f"set in {ctx.landscape.terrain}")

        if ctx.palette.description:
            parts.append(f"with a color palette of {ctx.palette.description}")

        # Quality
        parts.append("highly detailed, professional photography, 8k")

        return ". ".join(parts)

    def render_negative(self, ctx) -> str:
        return "blurry, low quality, deformed, ugly, watermark, text, signature"
