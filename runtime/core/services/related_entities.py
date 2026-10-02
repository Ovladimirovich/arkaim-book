"""Определение сущностей, упомянутых в вопросе и ответе книги.

World Engine используется как источник истины. Здесь нет LLM: кандидатов
отбирает детерминированный скоринг по имени и описанию из канонической модели.
Нерелевантные совпадения отбрасываются, чтобы под ответом не появлялся случайный
«шум» (например, персонаж «Велик» не должен тянуть случайную локацию только
потому, что она упомянута рядом).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
import re
from typing import Any, Iterable

log = logging.getLogger("hermes.related_entities")

MAX_RESULTS = 3
MIN_SCORE = 60
_STOP_WORDS = {
    "какие", "какой", "какая", "какое", "кого", "кто", "что", "где", "когда",
    "почему", "зачем", "такой", "такая", "такое", "такие", "этот", "эта",
    "это", "эти", "книга", "книги", "книге", "главный", "главная", "главное",
    "герой", "героя", "герои", "действие", "происходит", "раскрывает",
    "проповедует", "миссия", "ценности", "расскажи", "опиши", "объясни",
}
_RUSSIAN_SUFFIXES = (
    "иями", "иях", "ами", "ях", "ого", "его", "ому", "ему", "ыми", "ими",
    "ую", "юю", "ах", "ях", "ов", "ев", "ам", "ям", "ах", "ех", "у", "ю",
    "ы", "и", "а", "о", "е", "й", "ь",
)


@dataclass(frozen=True)
class _Candidate:
    entity_id: str
    entity_type: str
    name: str
    description: str
    score: int
    specificity: int

    @property
    def sort_key(self) -> tuple[int, int, str]:
        # Более конкретные категории (person, theme, event) имеют приоритет над
        # общими справочными категориями, даже если скоры одинаковы.
        return self.score, self.specificity, self.name


def _normalize(value: str) -> str:
    return (value or "").lower().replace("ё", "е")


def _word_stems(word: str) -> set[str]:
    """Разрешает окончания и несколько последних вариантов основы."""
    candidates = {word}
    for suffix in _RUSSIAN_SUFFIXES:
        if len(word) - len(suffix) >= 4 and word.endswith(suffix):
            candidates.add(word[:-len(suffix)])
    # Примеры: гиперборею → гиперборе → гиперборе; гиперборея → гиперборея/гиперборе.
    # Тримминг последних 1-3 символов помогает формам, которые не покрываются
    # окончанием из списка, не прибегая к LLM.
    for cut in (1, 2, 3):
        if len(word) - cut >= 5:
            candidates.add(word[:-cut])
    return candidates


def _stems(value: str) -> set[str]:
    """Достаточно грубый, но детерминированный Russian-aware stemmer."""
    normalized = _normalize(value)
    result: set[str] = set()
    for word in re.findall(r"[а-яa-z0-9]+", normalized):
        if len(word) >= 4 and word not in _STOP_WORDS:
            result.update(_word_stems(word))
    return result


def _specificity(entity_type: str) -> int:
    return {
        "character": 50, "characters": 50,
        "person": 50, "people": 50,
        "theme": 45, "themes": 45,
        "event": 40, "events": 40,
        "location": 35, "locations": 35,
        "artifact": 30, "artifacts": 30,
        "value": 20, "values": 20,
        "concept": 15, "concepts": 15,
    }.get(entity_type.lower(), 10)


def _entity_text(item: dict[str, Any], category: str) -> tuple[str, str, str]:
    entity_id = str(item.get("id") or "")
    name = str(item.get("name") or item.get("name_ru") or item.get("title") or entity_id)
    description = str(item.get("description") or item.get("description_ru") or item.get("summary") or "")
    entity_type = str(item.get("category") or item.get("type") or item.get("entity_type") or category)
    return entity_id, name or entity_type, description


def _score_entity(
    *,
    entity_id: str,
    entity_type: str,
    name: str,
    description: str,
    query_stems: set[str],
    answer_stems: set[str],
    answer_text: str,
) -> _Candidate:
    score = 0
    name_stems = _stems(name)
    matched_query = name_stems & query_stems
    matched_answer = name_stems & answer_stems
    matched_any = matched_query | matched_answer

    if not matched_any:
        score = 0
    else:
        # Целое имя прямо присутствует в тексте ответа — сильнейший сигнал.
        if len(name) >= 4 and _normalize(name) in answer_text:
            score += 100
        # Инфлексированная форма («Гиперборею») тоже является подтверждённым
        # упоминанием, если совпала достаточно длинная часть имени.
        elif any(len(stem) >= 6 and stem in answer_text for stem in matched_answer):
            score += 60
        if matched_query:
            score += 30
        if matched_answer:
            score += 30
        if len(matched_any) > 1:
            score += 10 * (len(matched_any) - 1)

        # Совпадения описания только дополняют имя; они не должны сами вытаскивать
        # случайную сущность.
        overlap = len(_stems(description) & (query_stems | answer_stems))
        score += min(15, overlap * 3)

        # Полнотекстовое короткое имя без явного вопроса тоже может быть полезным,
        # но требует подтверждения описанием.
        if len(name) <= 3 and not matched_query and score < 60:
            score = 0

    return _Candidate(
        entity_id=entity_id,
        entity_type=entity_type,
        name=name,
        description=description,
        score=min(score, 100),
        specificity=_specificity(entity_type),
    )


def _iter_entities(engine: Any) -> Iterable[tuple[str, dict[str, Any]]]:
    for category in engine._world_model.get_categories():
        for item in engine._world_model.get_category(category):
            if item.get("id"):
                yield str(category), item


def resolve_related_entities(payload: dict[str, Any]) -> list[dict[str, str]]:
    """Вернуть максимум три подтверждённые сущности, связанные с вопросом/ответом."""
    question = str(payload.get("question") or "")
    answer = str(payload.get("answer") or "")
    answer_text = _normalize(answer)
    query_stems = _stems(question)
    answer_stems = _stems(answer)

    try:
        from narrative_engine.world_engine import get_world_engine

        engine = get_world_engine()
        candidates: list[_Candidate] = []
        for category, item in _iter_entities(engine):
            entity_id, name, description = _entity_text(item, category)
            candidate = _score_entity(
                entity_id=entity_id,
                entity_type=category,
                name=name,
                description=description,
                query_stems=query_stems,
                answer_stems=answer_stems,
                answer_text=answer_text,
            )
            if candidate.score >= MIN_SCORE:
                candidates.append(candidate)

        candidates.sort(key=lambda item: item.sort_key, reverse=True)
        return [
            {
                "entity_id": candidate.entity_id,
                "entity_type": candidate.entity_type,
                "name": candidate.name,
                "description": candidate.description[:160],
            }
            for candidate in candidates[:MAX_RESULTS]
        ]
    except Exception as exc:
        log.warning("related_entities_error error=%s", exc)
        return []