"""ComfyUI шаблон промпта — для SD/SDXL через ComfyUI."""
from __future__ import annotations
from .base import PromptTemplate


class ComfyUITemplate(PromptTemplate):
    """Генерирует промпт для ComfyUI (Stable Diffusion)."""

    def render(self, ctx) -> str:
        parts = []

        # 1. Style prefix
        if ctx.style.prefix:
            parts.append(ctx.style.prefix)

        # 2. Scene title
        if ctx.scene.title:
            parts.append(ctx.scene.title)

        # 3. Location architecture
        if ctx.architecture.style:
            parts.append(ctx.architecture.style)
        elif ctx.location.name:
            parts.append(f"ancient {ctx.location.name}")

        # 4. Landscape
        if ctx.landscape.terrain:
            parts.append(ctx.landscape.terrain)
        if ctx.landscape.vegetation:
            parts.append(ctx.landscape.vegetation)

        # 5. Atmosphere
        if ctx.atmosphere.light:
            parts.append(ctx.atmosphere.light)
        elif ctx.lighting.description:
            parts.append(ctx.lighting.description)

        # 6. Fog and particles
        if ctx.atmosphere.fog:
            parts.append(ctx.atmosphere.fog)
        if ctx.atmosphere.particles:
            parts.append(ctx.atmosphere.particles)

        # 7. Emotion
        if ctx.emotion.visual:
            parts.append(ctx.emotion.visual)

        # 8. Characters
        for char in ctx.characters:
            if char.appearance_summary:
                parts.append(char.appearance_summary)

        # 9. Palette
        if ctx.palette.description:
            parts.append(ctx.palette.description)

        # 10. Camera
        if ctx.camera.composition:
            parts.append(ctx.camera.composition)
        if ctx.camera.shot_type:
            parts.append(ctx.camera.shot_type.replace("_", " "))

        # 11. Symbols (literal only)
        for sym in ctx.symbols[:3]:
            if sym.literal:
                parts.append(sym.literal)

        # 12. Quality suffixes
        for q in ctx.style.quality_suffixes:
            if q not in parts:
                parts.append(q)

        # Deduplicate and join
        seen = set()
        deduped = []
        for p in parts:
            key = p.lower().strip()
            if key and key not in seen:
                seen.add(key)
                deduped.append(p)

        return ", ".join(deduped)

    def render_negative(self, ctx) -> str:
        parts = list(ctx.negative_prompt.base)
        parts.extend(ctx.negative_prompt.extra)
        return ", ".join(parts)
