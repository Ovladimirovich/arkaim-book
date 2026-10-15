# -*- coding: utf-8 -*-
"""Пол в скоринге related_entities (целевой сценарий мультитематических вопросов).

Если пользователь полностью назвал тему в вопросе, но краткий Pulse-ответ её
не подтвердил, тематическая сущность всё равно должна дойти до Knowledge Core.
Это реализуется «полом» в _score_candidate: 100% совпадение content-слов имени
в вопросе поднимает score до MULTI_TOPIC_MIN_SCORE. Частичное совпадение
(доля < 100%) такой поддержки не получает — инвариант против ложных связей.

Тесты изолированы от состояния реального WorldEngine и от кэша решалера:
в полном сюите другой файл мог закэшировать реальный narrative_engine и заполнить
_related_cache — результат искажался бы. Перед каждым тестом чистим кэш,
обнуляем модули в sys.modules и ставим детерминированный фейк (тот же FakeEngine,
что и в test_related_entities.py), а результат гарантированно воспроизводим.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
_CORE = _REPO / "core" / "CORE"
for _candidate in (_CORE, _REPO):
    _path = str(_candidate)
    if _path not in sys.path:
        sys.path.insert(0, _path)

_MODULE_NAMES = [
    "core.services.related_entities",
    "narrative_engine",
    "narrative_engine.world_engine",
]


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


def _install_robust_fake(categories: dict[str, list[dict]], monkeypatch) -> None:
    """Ставит фейк World Engine и обеспечивает чистый, детерминированный решалер."""
    for module in _MODULE_NAMES:
        sys.modules.pop(module, None)
    fake_pkg = types.ModuleType("narrative_engine")
    world_engine = types.ModuleType("narrative_engine.world_engine")
    engine = FakeEngine(categories)
    world_engine.get_world_engine = lambda: engine
    fake_pkg.world_engine = world_engine
    monkeypatch.setitem(sys.modules, "narrative_engine", fake_pkg)
    monkeypatch.setitem(sys.modules, "narrative_engine.world_engine", world_engine)

    import core.services.related_entities as resolver

    cache = getattr(resolver, "_related_cache", None)
    if cache is not None:
        cache.clear()


def test_fully_named_topic_surfaces_when_brief_answer_omits_it(monkeypatch) -> None:
    """Полностью назанная в вопросе тема доходит до контекста, даже если
    краткий ответ её не назвал."""
    _install_robust_fake(
        {
            "language": [
                {"id": "lang_kali", "name": "Кали Юга", "description": "Кали Юга — низшая точка духовного цикла."},
                {"id": "lang_awake", "name": "Духовное пробуждение", "description": "Духовное пробуждение — переосмысление ценностей."},
            ],
            "location": [
                {"id": "loc_noise", "name": "Случайный лес", "description": "Место без совпадений с тематикой вопроса."},
            ],
        },
        monkeypatch,
    )

    import core.services.related_entities as resolver

    question = "Как пробуждение сознания связано с путешествием Велика и Кали Югой?"
    answer = "Духовное пробуждение — путь к осознанию."  # «Кали Юга» в кратком ответе нет
    ids = [item["entity_id"] for item in resolver.resolve_related_entities({"question": question, "answer": answer})]

    assert "lang_kali" in ids, "полностью назанная в вопросе тема должна занять слот контекста"
    assert "loc_noise" not in ids, "случайная сущность не должна попадать в контекст"


def test_partial_shared_stem_does_not_false_link(monkeypatch) -> None:
    """Частичное совпадение имени (доля < 100%) без подтверждения кратким ответом
    не вытаскивает слабую сущность; полностью назанная — проходит."""
    _install_robust_fake(
        {
            "theme": [
                {"id": "theme_battle", "name": "Великая Битва", "description": "Решающее сражение эпохи."},
            ],
            "character": [
                {"id": "character_velik", "name": "Велик", "description": "Главный герой."},
            ],
        },
        monkeypatch,
    )

    import core.services.related_entities as resolver

    question = "Кто такой Велик?"
    answer = "Он шёл по пути посвящения."  # ни «Велик» в явном виде, ни «Великая Битва»
    ids = [item["entity_id"] for item in resolver.resolve_related_entities({"question": question, "answer": answer})]

    assert "character_velik" in ids, "полностью назанный персонаж должен дойти до контекста"
    assert "theme_battle" not in ids, "общая основа «велик» не даёт ложную связь"
