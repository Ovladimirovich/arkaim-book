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

# Верхний предел количества сущностей, возвращаемых resolve_related_entities.
# Был 3: при мультитематических вопросах («Как X связано с Y и Z?») темы,
# названные в вопросе и прошедшие порог MIN_SCORE, но попавшие ниже среза,
# пропадали из related_entities и из контекста Knowledge Core.
# 10 даёт всем вопросным темам место в контексте, не раздувая его случайными
# совпадениями — шум отсеивается скорингом >= MIN_SCORE и дедупликацией семейств.
MAX_RESULTS = 10
MIN_SCORE = 60
# Пол в скоринге для значимых тем вопроса: если тема названа в вопросе полностью
# (100% совпадение content-слов имени), она обязана дойти до Knowledge Core, даже
# если краткий Pulse-ответ её не подтвердил. Без этого мультитематический вопрос
# «Как X связано с Y и Z?» терял темы при кратком ответе.
MULTI_TOPIC_MIN_SCORE = 60
_STOP_WORDS = {
    "какие",
    "какой",
    "какая",
    "какое",
    "кого",
    "кто",
    "что",
    "где",
    "когда",
    "почему",
    "зачем",
    "такой",
    "такая",
    "такое",
    "такие",
    "этот",
    "эта",
    "это",
    "эти",
    "книга",
    "книги",
    "книге",
    "главный",
    "главная",
    "главное",
    "герой",
    "героя",
    "герои",
    "действие",
    "происходит",
    "раскрывает",
    "проповедует",
    "миссия",
    "ценности",
    "расскажи",
    "опиши",
    "объясни",
}
_RUSSIAN_SUFFIXES = (
    "иями",
    "иях",
    "ами",
    "ях",
    "ого",
    "его",
    "ому",
    "ему",
    "ыми",
    "ими",
    "ую",
    "юю",
    "ах",
    "ях",
    "ов",
    "ев",
    "ам",
    "ям",
    "ах",
    "ех",
    "у",
    "ю",
    "ы",
    "и",
    "а",
    "о",
    "е",
    "й",
    "ь",
)


@dataclass(frozen=True)
class _Candidate:
    entity_id: str
    entity_type: str
    name: str
    description: str
    score: int
    specificity: int
    in_question: bool = False
    name_coverage: int = 0

    @property
    def sort_key(self) -> tuple[bool, int, int, int, str, str]:
        # Первый слой приоритета: сущность, которую пользователь НАЗВАЛ в
        # вопросе (coverage имени >= 50% — половина и более слов имени
        # встречается в вопросе). Без этого многотемные Pulse-ответы
        # (тема + «Связанные темы») вытесняли бы сюжеты вопроса ответными
        # упоминаниями: «Кали Юга» (спросили) проигрывала бы «Великая Битва»
        # (протянута общим словом «велик» у персонажа «Велик») лишь алфавиту.
        # Затем — прежний порядок: чем выше coverage/score/specificity, тем
        # выше; name и entity_id — детерминированные tie-breaker'ы по
        # возрастанию (в том числе для зеркальных дублей семейства
        # lang_/phil_/phil_deep_).
        return (
            not self.in_question,
            -self.name_coverage,
            -self.score,
            -self.specificity,
            self.name,
            self.entity_id,
        )


def _normalize(value: str) -> str:
    return (value or "").lower().replace("ё", "е")


def _word_stems(word: str) -> set[str]:
    """Разрешает окончания и несколько последних вариантов основы."""
    candidates = {word}
    for suffix in _RUSSIAN_SUFFIXES:
        if len(word) - len(suffix) >= 4 and word.endswith(suffix):
            candidates.add(word[: -len(suffix)])
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


def _duplicates(left: _Candidate, right: _Candidate) -> bool:
    """Реальное соответствие сущностей, а не вслепое удаление префиксов id.

    Дубли — только при одинаковом нормализованном названии И совместимых
    описаниях: равных нормализованных или хотя бы у одного пустом (покрытие
    полной карточкой). Разные сущности с похожими, но не совпадающими
    названиями или разными описаниями не объединяются.
    """
    if _normalize(left.name) != _normalize(right.name):
        return False
    left_desc = _normalize(left.description)
    right_desc = _normalize(right.description)
    if not left_desc or not right_desc:
        return True
    return left_desc == right_desc


def _dedupe_families(candidates: list[_Candidate]) -> list[_Candidate]:
    """Оставить одного представителя на семейство дублей.

    Кандидаты уже отсортированы по релевантности. Представитель семейства —
    первый по ранжированию; при прочих равных предпочитается карточка с
    непустым описанием (пустой дубль не должен вытеснять полную карточку).
    Позиция в итоговом списке соответствует лучшему ранжированию семейства.
    """
    kept: list[_Candidate] = []
    for candidate in candidates:
        duplicate_index = next(
            (index for index, existing in enumerate(kept) if _duplicates(candidate, existing)),
            None,
        )
        if duplicate_index is None:
            kept.append(candidate)
            continue
        existing = kept[duplicate_index]
        candidate_richness = bool(_normalize(candidate.description))
        existing_richness = bool(_normalize(existing.description))
        if candidate_richness and not existing_richness:
            kept[duplicate_index] = candidate
    return kept


def _specificity(entity_type: str) -> int:
    return {
        "character": 50,
        "characters": 50,
        "person": 50,
        "people": 50,
        "theme": 45,
        "themes": 45,
        "event": 40,
        "events": 40,
        "location": 35,
        "locations": 35,
        "artifact": 30,
        "artifacts": 30,
        "value": 20,
        "values": 20,
        "concept": 15,
        "concepts": 15,
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

    # Насколько имя сущности пользователь НАЗВАЛ в вопросе: доля слов имени
    # (>=4 символа, без стоп-слов), чьи основы встречаются в основах вопроса.
    # «Кали Юга» в вопросе «...Кали Юги...» — 100%; «Великая Битва» в вопросе
    # о персонаже «Велик» — 50% (одна общая основа), и в следующем ранге.
    content_words = [w for w in re.findall(r"[а-яa-z0-9]+", _normalize(name)) if len(w) >= 4 and w not in _STOP_WORDS]
    if content_words:
        matched_content = sum(1 for w in content_words if _word_stems(w) & query_stems)
        name_coverage = int(100 * matched_content / len(content_words))
    else:
        name_coverage = 0
    in_question = name_coverage >= 50

    # Пол для полностью названной в вопросе темы (100% совпадение content-слов
    # имени): она доходит до Knowledge Core даже без подтверждения кратким
    # ответом. Частичное имя (доля < 100%) остаётся ниже порога — это
    # исключает ложные связи.
    if content_words and matched_content == len(content_words) and score < MULTI_TOPIC_MIN_SCORE:
        score = MULTI_TOPIC_MIN_SCORE

    return _Candidate(
        entity_id=entity_id,
        entity_type=entity_type,
        name=name,
        description=description,
        score=min(score, 100),
        specificity=_specificity(entity_type),
        in_question=in_question,
        name_coverage=name_coverage,
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

        candidates.sort(key=lambda item: item.sort_key)
        # Дедупликация семейств ДО лимита: свободные слоты отдаются следующим
        # по ранжированию действительно разным сущностям, а не заполняются
        # дублями одной темы.
        unique = _dedupe_families(candidates)
        return [
            {
                "entity_id": candidate.entity_id,
                "entity_type": candidate.entity_type,
                "name": candidate.name,
                "description": candidate.description[:160],
            }
            for candidate in unique[:MAX_RESULTS]
        ]
    except Exception as exc:
        log.warning("related_entities_error error=%s", exc)
        return []
