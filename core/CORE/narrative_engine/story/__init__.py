"""Story Engine — генерация историй внутри ограничений World Model.

Новый API: composer.compose_prompt() + composer.format_composer_prompt()
Старый API: writer.build_writer_brief() + writer.format_story_prompt() (deprecated)
"""

# Новый API
from narrative_engine.story.composer import compose_prompt, format_composer_prompt

# Старый API (deprecated, для обратной совместимости)
from narrative_engine.story.writer import build_writer_brief, format_story_prompt

from narrative_engine.story.post_validator import validate_story, PostValidation, ConstraintViolation
from narrative_engine.story import store

__all__ = [
    # Новый API
    "compose_prompt",
    "format_composer_prompt",
    # Старый API (deprecated)
    "build_writer_brief",
    "format_story_prompt",
    # Общее
    "validate_story",
    "PostValidation",
    "ConstraintViolation",
    "store",
]
