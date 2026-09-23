"""Tests for Narrative Engine — Post Validator."""

import sys
from pathlib import Path

import pytest

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from narrative_engine.story.post_validator import validate_story, PostValidation
from narrative_engine.constraint_engine import ConstraintModel, StoryRequest, ResolvedContext
from narrative_engine.world_model import WorldModel


def _make_constraints(epoch_id: str = "satya_yuga") -> ConstraintModel:
    return ConstraintModel(
        story_request=StoryRequest(prompt="test", max_length=500),
        resolved_context=ResolvedContext(
            epoch={"id": epoch_id, "name_ru": "Сатья Юга"},
            location={"id": "hyperborea", "name_ru": "Гиперборея"},
            characters_alive=[
                {"character_name": "Велик", "status": "alive"},
                {"character_name": "Архат", "status": "alive"},
            ],
            technologies_available=[
                {"name_ru": "Кристальная технология"},
            ],
            applicable_rules=[
                {"description": "Нет технологий раньше эпохи"},
            ],
        ),
        hard_constraints=["Эпоха: Сатья Юга"],
        forbidden_elements=["Нельзя нарушать канон"],
    )


class TestPostValidator:
    def test_valid_story_passes(self):
        # Use longer text to avoid "too_short" soft violation
        text = "Велик шёл по Гиперборее. Он чувствовал энергию кристаллов. " * 10
        constraints = _make_constraints()
        result = validate_story(text, constraints)
        assert result.passed is True
        # Allow soft violations but no hard violations
        hard_violations = [v for v in result.violations if v.severity == "hard"]
        assert len(hard_violations) == 0

    def test_anachronism_detected(self):
        text = "Велик достал ружье и выстрелил. Порох взорвался."
        constraints = _make_constraints()
        result = validate_story(text, constraints)
        assert result.passed is False
        assert any("ружье" in v.rule_text.lower() or "порох" in v.rule_text.lower()
                    for v in result.violations)

    def test_location_not_mentioned_warning(self):
        text = "Он шёл по дорогеไกล от дома."
        constraints = _make_constraints()
        result = validate_story(text, constraints)
        assert any("Гиперборея" in w for w in result.warnings)

    def test_long_text_warning(self):
        text = "Слово " * 1000
        constraints = _make_constraints()
        constraints.story_request.max_length = 10
        result = validate_story(text, constraints)
        assert any("длинный" in w.lower() for w in result.warnings)

    def test_post_validation_model(self):
        pv = PostValidation(passed=True, violations=[], warnings=["test"])
        assert pv.passed is True
        assert len(pv.warnings) == 1

