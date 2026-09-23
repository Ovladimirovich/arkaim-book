"""Tests for Narrative Engine — Constraint Engine."""

import sys
from pathlib import Path

import pytest

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from narrative_engine.constraint_engine import (
    parse_prompt, build_constraints, StoryRequest, ConstraintModel,
)
from narrative_engine.world_model import WorldModel


def _make_world_model() -> WorldModel:
    data = {
        "epochs": [
            {"id": "satya_yuga", "name": "Satya Yuga", "name_ru": "Сатья Юга", "order": 1},
            {"id": "kali_yuga", "name": "Kali Yuga", "name_ru": "Кали Юга", "order": 4},
        ],
        "locations": [
            {"id": "hyperborea", "name": "Hyperborea", "name_ru": "Гиперборея", "type": "region",
             "description": "Земля предков"},
            {"id": "arkaim", "name": "Arkaim", "name_ru": "Аркаим", "type": "sacred_site"},
        ],
        "canonical_events": [
            {"id": "ev1", "title": "Event1", "title_ru": "Событие 1", "epoch": "satya_yuga", "order_in_epoch": 1},
        ],
        "causal_rules": [
            {"id": "r1", "description": "Нет технологий раньше эпохи", "rule_type": "exclusion"},
        ],
        "technologies": [
            {"id": "crystal_tech", "name": "Crystal Tech", "name_ru": "Кристальная технология"},
        ],
        "characters_living": {
            "satya_yuga": [
                {"character_name": "Велик", "epoch": "satya_yuga", "status": "alive"},
            ],
        },
    }
    return WorldModel(data)


class TestParsePrompt:
    def test_parse_epoch(self):
        req = parse_prompt("История в Сатья Юге")
        assert req.epoch == "satya_yuga"

    def test_parse_kali_yuga(self):
        req = parse_prompt("Что было в Кали Юге?")
        assert req.epoch == "kali_yuga"

    def test_parse_location(self):
        req = parse_prompt("Расскажи о Гиперборее")
        assert req.location == "hyperborea"

    def test_parse_arkaim(self):
        req = parse_prompt("История Аркаима")
        assert req.location == "arkaim"

    def test_parse_character_type_priest(self):
        req = parse_prompt("История жреца в храме")
        assert req.character_type == "priest"

    def test_parse_character_type_warrior(self):
        req = parse_prompt("История воина")
        assert req.character_type == "warrior"

    def test_parse_no_match(self):
        req = parse_prompt("Привет, как дела?")
        assert req.epoch is None
        assert req.location is None

    def test_parse_time_offset(self):
        req = parse_prompt("За 30 лет до появления Велика")
        assert req.time_offset is not None


class TestBuildConstraints:
    def test_basic_constraints(self):
        wm = _make_world_model()
        req = StoryRequest(prompt="История в Сатья Юге в Гиперборее")
        req = parse_prompt(req.prompt)
        constraints = build_constraints(req, wm)
        assert isinstance(constraints, ConstraintModel)
        assert len(constraints.hard_constraints) > 0
        assert len(constraints.forbidden_elements) > 0

    def test_epoch_resolved(self):
        wm = _make_world_model()
        req = parse_prompt("История в Сатья Юге")
        constraints = build_constraints(req, wm)
        assert constraints.resolved_context.epoch is not None
        assert constraints.resolved_context.epoch["id"] == "satya_yuga"

    def test_location_resolved(self):
        wm = _make_world_model()
        req = parse_prompt("История в Гиперборее")
        constraints = build_constraints(req, wm)
        assert constraints.resolved_context.location is not None
        assert constraints.resolved_context.location["id"] == "hyperborea"

    def test_characters_alive(self):
        wm = _make_world_model()
        req = parse_prompt("История в Сатья Юге")
        constraints = build_constraints(req, wm)
        chars = constraints.resolved_context.characters_alive
        assert len(chars) == 1
        assert chars[0]["character_name"] == "Велик"

    def test_forbidden_elements_include_rules(self):
        wm = _make_world_model()
        req = parse_prompt("История в Сатья Юге")
        constraints = build_constraints(req, wm)
        assert any("нарушать" in f.lower() or "технологии" in f.lower() or "события" in f.lower()
                    for f in constraints.forbidden_elements)

    def test_soft_constraints_style(self):
        wm = _make_world_model()
        req = parse_prompt("История в Сатья Юге")
        req.style = "poetic"
        constraints = build_constraints(req, wm)
        assert any("поэтич" in s.lower() for s in constraints.soft_constraints)
