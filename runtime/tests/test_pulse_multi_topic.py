"""Тесты многотемных Pulse-ответов KnowledgeLayer (core/CORE/pulse/layers.py).

Слой знаний раньше отвечал только по первой найденной теме: многотемный
вопрос («как A и B связаны?») давал короткий ответ с именем одного сюжета,
и related_entities не подтверждал сущности остальных сюжетов
(упоминание только в вопросе даёт <=30 баллов — ниже MIN_SCORE=60).
Теперь слой покрывает все подтверждённые в геноме темы вопроса, и имена
всех сюжетов попадают в контекст Knowledge Core.
"""

import copy
import json
import sys
import types
from pathlib import Path

import pytest

_CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))

from pulse.layers import IdentityLayer, KnowledgeLayer  # noqa: E402


GENOME = {
    "version": "1.0.0",
    "modules": {
        "characters": [
            {
                "name": "Велик",
                "aliases": ["Великий"],
                "archetype": "Гностик",
                "type": "main",
                "description": "Главный герой, проходит путь посвящения.",
                "values": ["Духовный рост"],
                "first_chapter": 2,
                "last_chapter": 16,
            },
        ],
        "themes": [
            {
                "name": "Космический импульс",
                "description": "Импульс космической трансформации, направленный на Землю.",
            },
            {
                "name": "Кали-юга и духовное пробуждение",
                "description": "Третья из четырнадцати юг — низшая точка духовного цикла.",
                "strength": "средняя",
            },
            {
                "name": "Пробуждение сознания",
                "description": "Восстановление духовного восприятия, утраченного в Кали-юге.",
            },
            {
                "name": "Замысел книги",
                "description": "Велик как гностик воплощает замысел книги.",
            },
        ],
        "symbols": [
            {"name": "Аарья-видья", "meaning": "Свет и знание", "chapters": [3, 9]},
        ],
        "conflicts": [{"name": "Бегство и разрушение", "type": "внешний"}],
    },
    "world_entities": [
        {
            "name": "Эра духовного пробуждения",
            "description": "Эпоха великого духовного пробуждения человечества.",
        },
        {
            "name": "Великий (Велик)",
            "description": "Первый человек, достигший состояния пробуждения.",
        },
        {
            "name": "Гиперборея",
            "type": "локация",
            "description": "Древняя цивилизация Севера.",
        },
    ],
}


def make_layer() -> KnowledgeLayer:
    return KnowledgeLayer(copy.deepcopy(GENOME))


class TestMultiTopicDetection:
    def test_two_theme_question_covers_all_topics(self):
        layer = make_layer()
        question = "Как космический импульс и наступление Кали Юги связаны между собой?"
        resp = layer.respond_to(question)
        assert resp is not None
        assert resp.source == "knowledge:multi_topic"
        assert "Космический импульс" in resp.text
        assert "Кали-юга" in resp.text
        # Каждая тема — своя карточка, данные из генома
        assert "Тема: Космический импульс" in resp.text
        assert "Тема: Кали-юга и духовное пробуждение" in resp.text
        assert len(resp.provenance) == 2

    def test_three_topic_question_includes_character(self):
        layer = make_layer()
        question = "Как пробуждение сознания связано с путешествием Велика и Кали Югой?"
        resp = layer.respond_to(question)
        assert resp is not None
        assert resp.source == "knowledge:multi_topic"
        assert "Тема: Пробуждение сознания" in resp.text
        assert "Велик" in resp.text
        assert "Кали-юга" in resp.text
        # Один и тот же сюжет — одна карточка: дубли из других категорий
        # не создают отдельные секции
        assert "Эра духовного пробуждения" not in resp.text
        assert "Великий (Велик)" not in resp.text
        assert len(resp.provenance) == 3

    def test_topics_ordered_by_appearance_in_query(self):
        layer = make_layer()
        question = "Как пробуждение сознания связано с путешествием Велика и Кали Югой?"
        resp = layer.respond_to(question)
        pos_awakening = resp.text.index("Пробуждение сознания")
        pos_velik = resp.text.index("Велик")
        pos_kali = resp.text.index("Кали-юга")
        assert pos_awakening < pos_velik < pos_kali

    def test_single_topic_answer_unchanged(self):
        layer = make_layer()
        resp = layer.respond_to("Расскажи о Велике")
        assert resp is not None
        assert resp.source == "knowledge:character"

    def test_single_theme_answer_unchanged(self):
        layer = make_layer()
        resp = layer.respond_to("Что такое космический импульс?")
        assert resp is not None
        assert resp.source == "knowledge:theme"
        assert "Кали-юга" not in resp.text

    def test_unknown_question_returns_none(self):
        layer = make_layer()
        assert layer.respond_to("Привет, как дела?") is None

    def test_multi_topic_is_deterministic(self):
        layer = make_layer()
        question = "Как космический импульс и наступление Кали Юги связаны между собой?"
        a = layer.respond_to(question)
        b = layer.respond_to(question)
        assert a.text == b.text
        assert a.source == b.source

    def test_multi_topic_answer_passes_identity_validation(self):
        layer = make_layer()
        identity = IdentityLayer(copy.deepcopy(GENOME))
        question = "Как пробуждение сознания связано с путешествием Велика и Кали Югой?"
        resp = layer.respond_to(question)
        assert identity.validate(resp.text) is True

    def test_character_card_uses_readable_type_label(self):
        """Внутренний код типа «(main)» не попадает в текст ответа:
        он случайно подтверждал нерелевантную сущность «main» в related_entities."""
        layer = make_layer()
        single = layer.respond_to("Расскажи о Велике")
        assert single is not None
        assert "(main)" not in single.text
        assert "главная роль" in single.text
        multi = layer.respond_to("Как пробуждение сознания связано с путешествием Велика и Кали Югой?")
        assert "(main)" not in multi.text


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


def install_fake_engine(categories: dict[str, list[dict]]) -> None:
    narrative_engine = types.ModuleType("narrative_engine")
    world_engine = types.ModuleType("narrative_engine.world_engine")
    engine = FakeEngine(categories)
    world_engine.get_world_engine = lambda: engine
    narrative_engine.world_engine = world_engine
    sys.modules["narrative_engine"] = narrative_engine
    sys.modules["narrative_engine.world_engine"] = world_engine


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


class TestMultiTopicFeedsRelatedEntities:
    def test_multi_topic_answer_confirms_both_entities(self):
        install_fake_engine(
            {
                "language": [
                    {
                        "id": "lang_кали_юга",
                        "name": "Кали Юга",
                        "description": "Кали Юга — эпоха, когда на землю пришла смута.",
                    },
                    {
                        "id": "lang_импульс_преобразования",
                        "name": "Импульс преобразования",
                        "description": "Импульс преобразования — космический импульс, начинающий трансформацию.",
                    },
                ],
            }
        )
        question = "Как космический импульс и наступление Кали Юги связаны между собой?"
        resp = make_layer().respond_to(question)
        assert resp is not None and resp.source == "knowledge:multi_topic"

        from core.services.related_entities import resolve_related_entities

        result = resolve_related_entities({"question": question, "answer": resp.text})
        ids = [item["entity_id"] for item in result]
        assert "lang_кали_юга" in ids, "Кали Юга должна подтвердиться из текста ответа"
        assert "lang_импульс_преобразования" in ids

    def test_three_topic_answer_confirms_third_entity(self):
        install_fake_engine(
            {
                "language": [
                    {
                        "id": "lang_кали_юга",
                        "name": "Кали Юга",
                        "description": "Кали Юга — низшая точка духовного цикла.",
                    },
                    {
                        "id": "lang_пробуждение_сознания",
                        "name": "Пробуждение сознания",
                        "description": "Пробуждение сознания восстанавливает духовное восприятие.",
                    },
                    {
                        "id": "character_велик",
                        "name": "Велик",
                        "description": "Главный герой книги, проходит путь посвящения.",
                    },
                ],
            }
        )
        question = "Как пробуждение сознания связано с путешествием Велика и Кали Югой?"
        resp = make_layer().respond_to(question)
        assert resp is not None and resp.source == "knowledge:multi_topic"

        from core.services.related_entities import resolve_related_entities

        result = resolve_related_entities({"question": question, "answer": resp.text})
        ids = [item["entity_id"] for item in result]
        assert "lang_кали_юга" in ids
        assert "lang_пробуждение_сознания" in ids


def _load_real_genome() -> dict:
    # Реальный геном: arkaim/core/GENOME/GENOME_v1.0.0.json
    # (core/config.py: GENOME_DIR = CORE_DIR / "GENOME", CORE_DIR = arkaim/core)
    genome_path = _CORE_DIR.parent / "GENOME" / "GENOME_v1.0.0.json"
    if not genome_path.exists():
        pytest.skip("реальный геном не найден")
    return json.loads(genome_path.read_text(encoding="utf-8"))


def test_real_genome_multi_topic_question():
    """Интеграция с реальным геномом: тематический вопрос покрывает >=2 тем."""
    genome = _load_real_genome()
    layer = KnowledgeLayer(genome)
    resp = layer.respond_to("Как космическая изоляция Земли и наступление Кали Юги связаны между собой?")
    assert resp is not None
    assert resp.source == "knowledge:multi_topic"
    assert "Космическая изоляция Земли" in resp.text
    assert "Кали Юга" in resp.text
    # провенанс покрывает все секции
    assert len(resp.provenance) >= 2


def test_real_genome_three_topic_question_keeps_kali_yuga_in_context():
    """Сценарий: «пробуждение сознания / путешествие Велика / Кали Юга».

    Кали Юга — не первая тема вопроса и не первая в порядке генома:
    многотемный ответ обязан дойти до неё, и «Кали Юга» должна попасть
    в related_entities (приоритет вопросных сущностей).
    """
    install_fake_engine(
        {
            "language": [
                {
                    "id": "lang_кали_юга",
                    "name": "Кали Юга",
                    "description": "Кали Юга — низшая точка духовного цикла.",
                },
                {
                    "id": "lang_духовное_пробуждение",
                    "name": "Духовное пробуждение",
                    "description": "Духовное пробуждение — переосмысление ценностей и осознание глобальной проблемы.",
                },
            ],
        }
    )
    genome = _load_real_genome()
    layer = KnowledgeLayer(genome)
    question = "Как пробуждение сознания связано с путешествием Велика и Кали Югой?"
    resp = layer.respond_to(question)
    assert resp is not None and resp.source == "knowledge:multi_topic"
    # Все сюжеты вопроса в тексте ответа
    assert "Кали Юга" in resp.text
    assert "Велик" in resp.text
    assert "пробуждение" in resp.text.lower()

    from core.services.related_entities import resolve_related_entities

    result = resolve_related_entities({"question": question, "answer": resp.text})
    ids = [item["entity_id"] for item in result]
    assert "lang_кали_юга" in ids, "Кали Юга должна занять слот контекста"
    assert "lang_духовное_пробуждение" in ids
