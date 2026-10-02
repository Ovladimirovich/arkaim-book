"""Tests for deterministic World Engine entity-card relevance."""
import sys
import types

import pytest


class FakeWorldModel:
    def __init__(self, categories: dict[str, list[dict]]) -> None:
        self._categories = categories

    def get_categories(self) -> list[str]:
        return list(self._categories)

    def get_category(self, category: str) -> list[dict]:
        return self._categories.get(category, [])


class FakeEngine:
    def __init__(self, categories: dict[str, list[dict]]) -> None:
        self._world_model = FakeWorldModel(categories)


@pytest.fixture(autouse=True)
def clean_related_imports():
    for module in [
        "core.services.related_entities",
        "narrative_engine",
        "narrative_engine.world_engine",
    ]:
        sys.modules.pop(module, None)
    yield
    for module in [
        "core.services.related_entities",
        "narrative_engine",
        "narrative_engine.world_engine",
    ]:
        sys.modules.pop(module, None)


def _install_fake_engine(categories: dict[str, list[dict]]):
    narrative_engine = types.ModuleType("narrative_engine")
    world_engine = types.ModuleType("narrative_engine.world_engine")
    engine = FakeEngine(categories)
    world_engine.get_world_engine = lambda: engine
    narrative_engine.world_engine = world_engine
    sys.modules["narrative_engine"] = narrative_engine
    sys.modules["narrative_engine.world_engine"] = world_engine
    return engine


def test_relevant_character_is_selected_and_random_descriptions_are_rejected():
    _install_fake_engine({
        "character": [
            {"id": "character_velik", "name": "Велик", "description": "Главный герой книги, юный путник."},
            {"id": "character_other", "name": "Софья", "description": "Другой персонаж."},
        ],
        "location": [
            {"id": "location_noise", "name": "Случайный лес", "description": "Лес, где упоминается книга, главный герой и вопросы."},
        ],
    })

    from core.services.related_entities import resolve_related_entities

    result = resolve_related_entities({
        "question": "Кто такой Велик?",
        "answer": "Велик — главный герой книги. Он проходит путь самопознания.",
    })

    assert [item["entity_id"] for item in result] == ["character_velik"]
    assert result[0]["entity_type"] == "character"


def test_cards_do_not_fallback_when_entities_are_not_confirmed():
    _install_fake_engine({
        "location": [
            {"id": "location_noise", "name": "Случайный лес", "description": "Место с совпадающими общими словами."},
        ],
    })

    from core.services.related_entities import resolve_related_entities

    assert resolve_related_entities({
        "question": "Что такое неизвестная сущность?",
        "answer": "В этом тексте нет подтверждённой сущности мира.",
    }) == []


def test_multiple_confirmed_entities_are_ranked_by_specificity():
    _install_fake_engine({
        "themes": [
            {"id": "theme_unity", "name": "Единство", "description": "Сквозная тема пути."},
        ],
        "characters": [
            {"id": "character_velik", "name": "Велик", "description": "Главный герой."},
        ],
        "locations": [
            {"id": "location_hyperborea", "name": "Гиперборея", "description": "Древняя земля пути."},
        ],
    })

    from core.services.related_entities import resolve_related_entities

    result = resolve_related_entities({
        "question": "Кто такой Велик и где он был?",
        "answer": "Велик шёл через Гиперборею, а тема пути раскрывала Единство.",
    })

    assert [item["entity_id"] for item in result] == [
        "character_velik",
        "theme_unity",
        "location_hyperborea",
    ]