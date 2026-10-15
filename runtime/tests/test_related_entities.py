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
    _install_fake_engine(
        {
            "character": [
                {"id": "character_velik", "name": "Велик", "description": "Главный герой книги, юный путник."},
                {"id": "character_other", "name": "Софья", "description": "Другой персонаж."},
            ],
            "location": [
                {"id": "location_noise", "name": "Случайный лес", "description": "Лес, где упоминается книга, главный герой и вопросы."},
            ],
        }
    )

    from core.services.related_entities import resolve_related_entities

    result = resolve_related_entities(
        {
            "question": "Кто такой Велик?",
            "answer": "Велик — главный герой книги. Он проходит путь самопознания.",
        }
    )

    assert [item["entity_id"] for item in result] == ["character_velik"]
    assert result[0]["entity_type"] == "character"


def test_cards_do_not_fallback_when_entities_are_not_confirmed():
    _install_fake_engine(
        {
            "location": [
                {"id": "location_noise", "name": "Случайный лес", "description": "Место с совпадающими общими словами."},
            ],
        }
    )

    from core.services.related_entities import resolve_related_entities

    assert (
        resolve_related_entities(
            {
                "question": "Что такое неизвестная сущность?",
                "answer": "В этом тексте нет подтверждённой сущности мира.",
            }
        )
        == []
    )


def test_multiple_confirmed_entities_are_ranked_by_specificity():
    _install_fake_engine(
        {
            "themes": [
                {"id": "theme_unity", "name": "Единство", "description": "Сквозная тема пути."},
            ],
            "characters": [
                {"id": "character_velik", "name": "Велик", "description": "Главный герой."},
            ],
            "locations": [
                {"id": "location_hyperborea", "name": "Гиперборея", "description": "Древняя земля пути."},
            ],
        }
    )

    from core.services.related_entities import resolve_related_entities

    result = resolve_related_entities(
        {
            "question": "Кто такой Велик и где он был?",
            "answer": "Велик шёл через Гиперборею, а тема пути раскрывала Единство.",
        }
    )

    assert [item["entity_id"] for item in result] == [
        "character_velik",
        "theme_unity",
        "location_hyperborea",
    ]


def test_mirror_family_duplicates_do_not_consume_slots():
    """Семейство lang_/phil_/phil_deep_ с одним name+desc — одна позиция."""
    _install_fake_engine(
        {
            "language": [
                {
                    "id": "lang_kali_yuga",
                    "name": "Эпоха Кали Юги",
                    "description": "Приход эпохи темных сил на всей Земле.",
                },
                {
                    "id": "lang_kali_yuga_2",
                    "name": "Эпоха Кали Юги",
                    "description": "Приход эпохи темных сил на всей Земле.",
                },
                {
                    "id": "lang_kali_yuga_3",
                    "name": "Эпоха Кали Юги",
                    "description": "Приход эпохи темных сил на всей Земле.",
                },
            ],
            "philosophy": [
                {
                    "id": "phil_kali_yuga",
                    "name": "Эпоха Кали Юги",
                    "description": "Приход эпохи темных сил на всей Земле.",
                },
            ],
            "character": [
                {
                    "id": "character_velik",
                    "name": "Велик",
                    "description": "Главный герой.",
                },
            ],
            "mythology": [
                {
                    "id": "myth_awakening",
                    "name": "Духовное пробуждение",
                    "description": "Огонь сердечного энтузиазма.",
                },
            ],
        }
    )

    from core.services.related_entities import resolve_related_entities

    result = resolve_related_entities(
        {
            "question": "Что означает наступление Кали Юги?",
            "answer": "Наступление Кали Юги — приход эпохи темных сил. Велик и Духовное пробуждение тоже важны.",
        }
    )

    ids = [item["entity_id"] for item in result]
    assert len(ids) == len(set(ids)), f"дубли в результате: {ids}"
    assert "lang_kali_yuga" in ids
    assert "phil_kali_yuga" not in ids, "дубль семейства не должен занимать слот"
    assert "lang_kali_yuga_2" not in ids
    assert "lang_kali_yuga_3" not in ids
    assert "character_velik" in ids, "свободный слот должен отдан следующей релевантной сущности"
    assert "myth_awakening" in ids


def test_duplicate_with_empty_description_is_covered_by_full_card():
    """Дубль с пустым описанием покрывается полной карточкой того же имени."""
    _install_fake_engine(
        {
            "language": [
                {
                    "id": "lang_cosmo",
                    "name": "Космическая изоляция Земли",
                    "description": "Плотная оболочка вокруг Земли из-за человеческих эманаций.",
                },
            ],
            "mythology": [
                {"id": "cosmo_myth_cosmo", "name": "Космическая изоляция Земли", "description": ""},
            ],
            "philosophy": [
                {
                    "id": "phil_deep_cosmo",
                    "name": "Космическая изоляция Земли",
                    "description": "Плотная оболочка вокруг Земли из-за человеческих эманаций.",
                },
            ],
        }
    )

    from core.services.related_entities import resolve_related_entities

    result = resolve_related_entities(
        {
            "question": "Что такое космическая изоляция Земли?",
            "answer": "Космическая изоляция Земли — плотная оболочка, препятствующая космическим лучам.",
        }
    )

    ids = [item["entity_id"] for item in result]
    assert ids == ["lang_cosmo"]


def test_similar_names_with_different_descriptions_are_not_merged():
    """Похожие названия с разными описаниями — разные сущности."""
    _install_fake_engine(
        {
            "themes": [
                {
                    "id": "theme_journey",
                    "name": "Путешествие героя",
                    "description": "Путь Велика через земли гипербореев.",
                },
                {
                    "id": "theme_journey_teaching",
                    "name": "Путешествие героя",
                    "description": "Передача знаний от Посвященных в пути.",
                },
            ],
        }
    )

    from core.services.related_entities import resolve_related_entities

    result = resolve_related_entities(
        {
            "question": "Что такое путешествие героя?",
            "answer": "Путешествие героя раскрывается через путь и передачу знаний от Посвященных.",
        }
    )

    ids = [item["entity_id"] for item in result]
    assert sorted(ids) == ["theme_journey", "theme_journey_teaching"]


def test_question_mentioned_entities_get_slot_priority():
    """Сущность из вопроса занимает слот раньше ответной с той же оценкой.

    Многотемный Pulse-ответ покрывает и сюжеты вопроса, и «Связанные темы».
    Ответные упоминания не должны вытеснять сюжеты, о которых спрашивали.
    """
    _install_fake_engine(
        {
            "language": [
                {
                    "id": "lang_kali",
                    "name": "Кали Юга",
                    "description": "Кали Юга — низшая эпоха духовного цикла.",
                },
                {
                    "id": "lang_brothers",
                    "name": "Встреча духовных братьев",
                    "description": "Встреча духовных братьев — духовное событие цикла.",
                },
            ],
            "philosophy": [
                {
                    "id": "phil_impulse",
                    "name": "Импульс преобразования",
                    "description": "Импульс преобразования — космический импульс трансформации.",
                },
            ],
        }
    )

    from core.services.related_entities import resolve_related_entities

    question = "Как космический импульс и наступление Кали Юги связаны между собой?"
    answer = (
        "Тема: Космический импульс. Импульс преобразования. "
        "Кали Юга и Сати Юга. Связанные темы: Встреча духовных братьев."
    )
    result = resolve_related_entities({"question": question, "answer": answer})
    ids = [item["entity_id"] for item in result]
    # Оба сюжета вопроса — в первых двух слотах
    assert ids[0] in ("lang_kali", "phil_impulse")
    assert ids[1] in ("lang_kali", "phil_impulse")
    assert "lang_kali" in ids and "phil_impulse" in ids


def test_answer_only_entity_ranks_after_question_mentioned():
    """При равной оценке вопросная сущность идёт первой, ответная — после."""
    _install_fake_engine(
        {
            "language": [
                {
                    "id": "lang_kali",
                    "name": "Кали Юга",
                    "description": "Кали Юга — низшая эпоха духовного цикла.",
                },
                {
                    "id": "lang_brothers",
                    "name": "Встреча духовных братьев",
                    "description": "Встреча духовных братьев — духовное событие цикла.",
                },
            ],
        }
    )

    from core.services.related_entities import resolve_related_entities

    question = "Что такое встреча духовных братьев?"
    answer = "Кали Юга — низшая эпоха. Встреча духовных братьев — духовное событие."
    result = resolve_related_entities({"question": question, "answer": answer})
    ids = [item["entity_id"] for item in result]
    assert ids[0] == "lang_brothers"
    assert ids[1] == "lang_kali"


def test_fewer_than_three_entities_are_not_padded():
    """Если подходящих сущностей меньше трёх — остальные слоты остаются пустыми."""
    _install_fake_engine(
        {
            "character": [
                {"id": "character_velik", "name": "Велик", "description": "Главный герой."},
            ],
            "location": [
                {
                    "id": "location_noise",
                    "name": "Случайный лес",
                    "description": "Нерелевантное описание без совпадений с вопросом о Велике.",
                },
            ],
        }
    )

    from core.services.related_entities import resolve_related_entities

    result = resolve_related_entities(
        {
            "question": "Кто такой Велик?",
            "answer": "Велик — главный герой.",
        }
    )

    assert [item["entity_id"] for item in result] == ["character_velik"]
