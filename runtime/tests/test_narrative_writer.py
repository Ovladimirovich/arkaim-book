"""Tests for Narrative Engine — Writer."""

import sys
from pathlib import Path

import pytest

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from narrative_engine.story.writer import build_writer_brief, format_story_prompt
from narrative_engine.story.composer import compose_prompt, format_composer_prompt
from narrative_engine.context_assembler import FullContext
from narrative_engine.planner import NarrativePlan
from narrative_engine.planners.cause_effect import CauseEffectTree
from narrative_engine.constraint_engine import (
    ConstraintModel, StoryRequest, ResolvedContext,
)


def _make_constraints() -> ConstraintModel:
    return ConstraintModel(
        story_request=StoryRequest(prompt="История о гиперборейце", style="literary", max_length=1000),
        resolved_context=ResolvedContext(
            epoch={"id": "satya_yuga", "name_ru": "Сатья Юга", "description": "Золотой век"},
            location={"id": "hyperborea", "name_ru": "Гиперборея", "description": "Земля предков"},
            characters_alive=[
                {"character_name": "Велик", "status": "alive"},
            ],
            technologies_available=[
                {"name_ru": "Кристальная технология"},
            ],
            applicable_rules=[
                {"description": "Нет анахронизмов"},
            ],
        ),
        hard_constraints=["Эпоха: Сатья Юга", "Локация: Гиперборея"],
        soft_constraints=["Стиль: литературный"],
        forbidden_elements=["Нельзя нарушать канон"],
    )


class TestWriter:
    def test_build_brief_has_system_instruction(self):
        brief = build_writer_brief(_make_constraints())
        assert "system_instruction" in brief
        assert "писатель" in brief["system_instruction"].lower() or "мир" in brief["system_instruction"].lower()

    def test_build_brief_has_world_context(self):
        brief = build_writer_brief(_make_constraints())
        assert "Сатья Юга" in brief["world_context"]
        assert "Гиперборея" in brief["world_context"]

    def test_build_brief_has_user_prompt(self):
        brief = build_writer_brief(_make_constraints())
        assert brief["user_prompt"] == "История о гиперборейце"

    def test_build_brief_constraints_included(self):
        brief = build_writer_brief(_make_constraints())
        assert len(brief["hard_constraints"]) == 2
        assert len(brief["soft_constraints"]) == 1

    def test_format_story_prompt(self):
        brief = build_writer_brief(_make_constraints())
        prompt = format_story_prompt(brief)
        assert "писатель" in prompt.lower() or "Сатья Юга" in prompt
        assert "История о гиперборейце" in prompt
        assert "запрещено" in prompt.lower() or "нарушать" in prompt.lower()

class TestComposer:
    """Tests for new Composer API (replaces Writer)."""

    def test_compose_prompt(self):
        constraints = _make_constraints()
        context = FullContext(
            world_state=constraints.resolved_context.model_dump()
        )
        plan = NarrativePlan(
            cause_effect=CauseEffectTree(root="test"),
        )
        composed = compose_prompt(constraints, context, plan, "literary", 1000)
        assert "system_instruction" in composed
        assert "user_prompt" in composed
        assert len(composed["system_instruction"]) > 100

    def test_format_composer_prompt(self):
        constraints = _make_constraints()
        context = FullContext()
        plan = NarrativePlan(
            cause_effect=CauseEffectTree(root="test"),
        )
        composed = compose_prompt(constraints, context, plan, "literary", 1000)
        full = format_composer_prompt(composed)
        assert len(full) > 500
        assert "Наследие Аркаима" in full

    def test_compose_includes_plan(self):
        constraints = _make_constraints()
        context = FullContext()
        plan = NarrativePlan(
            cause_effect=CauseEffectTree(
                root="test",
                matched_pattern="Путешествие героя",
                nodes=[],
            ),
            story_structure=["Экспозиция", "Завязка", "Развязка"],
        )
        composed = compose_prompt(constraints, context, plan, "literary", 1000)
        assert "Экспозиция" in composed["user_prompt"]
        assert "Завязка" in composed["user_prompt"]
