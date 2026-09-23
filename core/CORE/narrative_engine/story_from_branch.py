"""Story from Branch — генерация текста истории из ветви World Explorer.

Реализует архитектура World Explorer: Этап 9 — Генерация текста (LLM).

Берёт RankedBranch из World Explorer и конвертирует его в входные данные
для существующего Story Engine pipeline:
  Branch → StoryRequest → CanonValidator → ContextAssembler → UnifiedPlanner → Composer → LLM
"""

import json
import logging
from typing import Optional

from pydantic import BaseModel, Field

from narrative_engine.world_model import WorldModel
from narrative_engine.constraint_engine import StoryRequest, build_constraints
from narrative_engine.canon_validator import CanonValidator
from narrative_engine.context_assembler import ContextAssembler, FullContext
from narrative_engine.planner import UnifiedPlanner, NarrativePlan
from narrative_engine.story.composer import compose_prompt, format_composer_prompt
from narrative_engine.quality_evaluator import QualityReport

log = logging.getLogger("hermes.narrative.story_from_branch")


class BranchToStoryRequest(BaseModel):
    """Запрос на генерацию текста из ветви."""
    exploration_prompt: str
    branch_title: str
    branch_type: str
    epoch: Optional[str] = None
    location: Optional[str] = None
    style: str = "literary"
    max_length: int = 2000
    quality_score: float = 0.0
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


class StoryFromBranchResult(BaseModel):
    """Результат генерации текста из ветви."""
    system_instruction: str
    user_prompt: str
    style: str
    max_length: int
    branch_title: str
    quality_score: float
    constraints_summary: str = ""


def build_story_from_branch(
    branch_request: BranchToStoryRequest,
    world_model: WorldModel,
) -> StoryFromBranchResult:
    """Построить промпт для LLM на основе ветви World Explorer.

    Не отправляет запрос к LLM — только формирует промпт.
    LLM вызывается на уровне API route.
    """
    # 1. Создаём StoryRequest из данных ветви
    story_request = StoryRequest(
        prompt=f"{branch_request.exploration_prompt}\n\nРазвитие: {branch_request.branch_title}",
        epoch=branch_request.epoch,
        location=branch_request.location,
        style=branch_request.style,
        max_length=branch_request.max_length,
    )

    # 2. CanonValidator
    validator = CanonValidator(world_model)
    canon_result = validator.validate(story_request)

    # 3. ContextAssembler
    assembler = ContextAssembler(world_model)
    full_context = assembler.assemble(canon_result)

    # 4. UnifiedPlanner
    planner = UnifiedPlanner(world_model)
    narrative_plan = planner.plan(story_request, full_context)

    # 5. Composer — формируем промпт
    composed = compose_prompt(
        canon_result.constraints,
        full_context,
        narrative_plan,
        style=branch_request.style,
        max_length=branch_request.max_length,
    )

    # 6. Добавляем контекст ветви в промпт
    branch_context = _build_branch_context(branch_request)
    composed["user_prompt"] += branch_context

    # 7. Формируем краткую сводку ограничений
    constraints_summary = _build_constraints_summary(canon_result.constraints)

    return StoryFromBranchResult(
        system_instruction=composed["system_instruction"],
        user_prompt=composed["user_prompt"],
        style=branch_request.style,
        max_length=branch_request.max_length,
        branch_title=branch_request.branch_title,
        quality_score=branch_request.quality_score,
        constraints_summary=constraints_summary,
    )


def _build_branch_context(branch: BranchToStoryRequest) -> str:
    """Построить дополнительный контекст из данных ветви."""
    parts = [
        "",
        "КОНТЕКСТ ВЕТВИ ИССЛЕДОВАНИЯ:",
        f"  Тип развития: {branch.branch_type}",
        f"  Качество: {branch.quality_score:.2f}",
    ]

    if branch.strengths:
        parts.append("  Сильные стороны:")
        for s in branch.strengths[:3]:
            parts.append(f"    + {s}")

    if branch.weaknesses:
        parts.append("  Слабые стороны:")
        for w in branch.weaknesses[:3]:
            parts.append(f"    - {w}")

    parts.append("")
    parts.append("Используй контекст ветви для создания связного повествования.")
    parts.append("Следуй канону мира. Не нарушай логику.")

    return "\n".join(parts)


def _build_constraints_summary(constraints) -> str:
    """Краткая сводка ограничений."""
    parts = []

    if constraints.hard_constraints:
        parts.append(f"Жёстких ограничений: {len(constraints.hard_constraints)}")

    if constraints.forbidden_elements:
        parts.append(f"Запрещённых элементов: {len(constraints.forbidden_elements)}")

    ctx = constraints.resolved_context
    if ctx.epoch:
        parts.append(f"Эпоха: {ctx.epoch.get('name_ru', '')}")
    if ctx.location:
        parts.append(f"Локация: {ctx.location.get('name_ru', '')}")

    return "; ".join(parts) if parts else "Ограничения не определены"
