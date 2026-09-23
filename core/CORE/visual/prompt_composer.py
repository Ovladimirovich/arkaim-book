"""PromptComposer — VisualContext → промпт для конкретного генератора."""
from __future__ import annotations

import logging
from .visual_context import VisualContext
from .prompt_templates import get_template

log = logging.getLogger("visual.prompt_composer")


class PromptComposer:
    """Компонует промпт из VisualContext для конкретного генератора."""

    def __init__(self, generator: str = "comfyui"):
        self._generator = generator
        self._template = get_template(generator)

    def compose(self, ctx: VisualContext) -> str:
        """VisualContext → строковый промпт."""
        prompt = self._template.render(ctx)
        log.info("prompt_composed generator=%s length=%d", self._generator, len(prompt))
        return prompt

    def compose_negative(self, ctx: VisualContext) -> str:
        """VisualContext → negative prompt."""
        return self._template.render_negative(ctx)

    def compose_pair(self, ctx: VisualContext) -> tuple[str, str]:
        """VisualContext → (positive, negative) tuple."""
        return self.compose(ctx), self.compose_negative(ctx)
