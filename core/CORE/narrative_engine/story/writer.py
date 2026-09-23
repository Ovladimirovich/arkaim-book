"""Writer — DEPRECATED. Используй composer.py.

Этот модуль сохранён для обратной совместимости.
Все вызовы делегируются в composer.py.
"""

import logging
import warnings
from typing import Optional

from narrative_engine.constraint_engine import ConstraintModel

log = logging.getLogger("hermes.narrative.writer")


def build_writer_brief(constraints: ConstraintModel) -> dict:
    """DEPRECATED: Используй compose_prompt() из composer.py."""
    warnings.warn(
        "build_writer_brief() deprecated. Use composer.compose_prompt() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    from narrative_engine.story.composer import compose_prompt
    from narrative_engine.context_assembler import FullContext
    from narrative_engine.planner import NarrativePlan
    from narrative_engine.planners.cause_effect import CauseEffectTree

    # Создаём пустой контекст и план для обратной совместимости
    context = FullContext(
        world_state=constraints.resolved_context.model_dump()
        if hasattr(constraints.resolved_context, 'model_dump')
        else constraints.resolved_context,
    )
    plan = NarrativePlan(
        cause_effect=CauseEffectTree(root=constraints.story_request.prompt[:100]),
    )

    composed = compose_prompt(constraints, context, plan, "literary", 2000)
    return {
        "system_instruction": composed["system_instruction"],
        "world_context": composed["user_prompt"],
        "hard_constraints": constraints.hard_constraints,
        "soft_constraints": constraints.soft_constraints,
        "user_prompt": constraints.story_request.prompt,
        "style_guide": f"Стиль: {constraints.story_request.style}. Максимум слов: {constraints.story_request.max_length}.",
    }


def format_story_prompt(brief: dict) -> str:
    """DEPRECATED: Используй format_composer_prompt() из composer.py."""
    warnings.warn(
        "format_story_prompt() deprecated. Use composer.format_composer_prompt() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    from narrative_engine.story.composer import format_composer_prompt
    return format_composer_prompt(brief)
