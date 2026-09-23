"""Post Validator — проверка сгенерированного текста на соответствие ограничениям и плану."""

import re
import logging
from typing import Optional
from pydantic import BaseModel, Field

from narrative_engine.constraint_engine import ConstraintModel
from narrative_engine.world_model import WorldModel

log = logging.getLogger("hermes.narrative.validator")


# Type hint for NarrativePlan (avoids circular import)
class _NarrativePlanStub(BaseModel):
    """Minimal stub for type checking. Real type is NarrativePlan."""
    cause_effect: Optional[BaseModel] = None
    character_arcs: list = Field(default_factory=list)
    conflicts: list = Field(default_factory=list)
    story_structure: list = Field(default_factory=list)


class ConstraintViolation(BaseModel):
    rule_id: str
    rule_text: str
    severity: str  # hard, soft
    evidence: str


class PostValidation(BaseModel):
    passed: bool
    violations: list[ConstraintViolation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    score: float = 1.0  # 0.0 = completely invalid, 1.0 = perfect


# Words that indicate anachronistic technology
ANACHRONISM_WORDS = {
    "порох": "огнестрельное оружие",
    "ружье": "огнестрельное оружие",
    "пушка": "огнестрельное оружие",
    "телефон": "электросвязь",
    "телевизор": "электроника",
    "компьютер": "вычислительная техника",
    "интернет": "глобальная сеть",
    "электричество": "электроэнергия",
    "двигатель": "механический двигатель",
    "автомобиль": "механическое транспортное средство",
    "самолёт": "авиация",
    "поезд": "железнодорожный транспорт",
    "бумага": "бумажное производство",
    "печать": "книгопечатание",
    "стекло": "стеклоделие",
    "железо": "металлургия",
    "бронза": "металлургия",
    "сталь": "металлургия",
}

# Common words that look like names but aren't
PRONOUNS_AND_COMMON = {
    "я", "ты", "он", "она", "мы", "вы", "они", "это", "то",
    "как", "где", "когда", "что", "кто", "да", "нет",
    "был", "была", "было", "были", "быть",
    "его", "её", "их", "эти", "тот", "та", "те",
    "все", "вся", "всё", "каждый", "каждая", "каждое",
    "другой", "другая", "другое", "такой", "такая", "такое",
    "самый", "самая", "самое", "первый", "второй", "третий",
    "новый", "новая", "новое", "старый", "старая", "старое",
    "большой", "большая", "большое", "маленький", "маленькая",
    "хороший", "хорошая", "хорошее", "плохой", "плохая", "плохое",
    "один", "два", "три", "четыре", "пять",
    "сегодня", "вчера", "завтра", "сейчас", "потом", "теперь",
    "сюда", "туда", "здесь", "там", "тогда", "потому", "поэтому",
    "значит", "конечно", "действительно", "пожалуй", "вероятно",
    "может", "нужно", "надо", "можно", "нельзя", "должен", "должна",
}


def validate_story(text: str, constraints: ConstraintModel,
                   world_model: Optional[WorldModel] = None) -> PostValidation:
    """Проверить сгенерированный текст на соответствие ограничениям."""
    violations = []
    warnings = []
    ctx = constraints.resolved_context
    text_lower = text.lower()

    # 1. Проверка: персонажи не из этой эпохи
    if ctx.characters_alive and ctx.epoch:
        known_names = {ch["character_name"].lower() for ch in ctx.characters_alive}
        potential_names = re.findall(r'\b[А-ЯЁ][а-яё]+\b', text)
        unknown_chars = []
        for name in potential_names:
            name_lower = name.lower()
            if name_lower in PRONOUNS_AND_COMMON or len(name_lower) <= 3:
                continue
            if name_lower not in known_names:
                unknown_chars.append(name)

        if unknown_chars:
            # Only warn if more than 2 unknown characters (some are ok for narration)
            if len(unknown_chars) > 2:
                warnings.append(
                    f"Обнаружены персонажи, не указанные в эпохе: {', '.join(unknown_chars[:5])}."
                )

    # 2. Проверка: технологии эпохи (анахронизмы)
    if ctx.technologies_available and ctx.epoch:
        for word, tech_desc in ANACHRONISM_WORDS.items():
            if word in text_lower:
                violations.append(ConstraintViolation(
                    rule_id="tech_anachronism",
                    rule_text=f"Анахронизм: '{word}' ({tech_desc}) не существует в эпоху {ctx.epoch.get('name_ru', '?')}",
                    severity="hard",
                    evidence=f"Упомянуто: '{word}'",
                ))

    # 3. Проверка: географическая согласованность
    if ctx.location:
        loc_name = ctx.location.get("name", "").lower()
        loc_name_ru = ctx.location.get("name_ru", "").lower()
        loc_id = ctx.location.get("id", "").replace("_", " ").lower()
        names_to_check = [n for n in [loc_name, loc_name_ru, loc_id] if n]
        if names_to_check and not any(n in text_lower for n in names_to_check):
            label = ctx.location.get("name_ru") or ctx.location.get("id", "")
            warnings.append(f"Локация '{label}' не упоминается в тексте.")

    # 4. Проверка: длина текста
    word_count = len(text.split())
    max_words = constraints.story_request.max_length
    if word_count > max_words * 1.5:
        warnings.append(
            f"Текст слишком длинный: {word_count} слов (максимум ~{max_words})."
        )
    elif word_count < 20:
        violations.append(ConstraintViolation(
            rule_id="too_short",
            rule_text=f"Текст слишком короткий: {word_count} слов (минимум ~50).",
            severity="soft",
            evidence=f"Длина: {word_count} слов",
        ))

    # 5. Проверка: наличие диалога (опционально, soft)
    has_dialog = bool(re.search(r'[«""].*[»""]', text)) or bool(re.search(r'— ', text))
    if not has_dialog and word_count > 100:
        warnings.append("В тексте отсутствуют диалоги.")

    # 6. Проверка: эпоха упоминается или подразумевается
    if ctx.epoch:
        epoch_name = ctx.epoch.get("name_ru", "").lower()
        epoch_id = ctx.epoch.get("id", "").replace("_", " ").lower()
        # Check if epoch is mentioned or if context is consistent
        epoch_mentioned = any(kw in text_lower for kw in [epoch_name, epoch_id] if kw)
        if not epoch_mentioned and word_count > 50:
            # Soft warning only - the story might not need to explicitly name the epoch
            pass

    # 7. Проверка: правила причинно-следственной связи
    if ctx.applicable_rules:
        for rule in ctx.applicable_rules:
            rule_desc = rule.get("description", "").lower()
            # Check for explicit violations mentioned in text
            if "наруши" in text_lower or "противореч" in text_lower:
                warnings.append("В тексте упоминается нарушение правил мира.")

    # Calculate score
    hard_violations = sum(1 for v in violations if v.severity == "hard")
    soft_violations = sum(1 for v in violations if v.severity == "soft")
    score = max(0.0, 1.0 - (hard_violations * 0.3) - (soft_violations * 0.1) - (len(warnings) * 0.05))

    passed = hard_violations == 0

    return PostValidation(
        passed=passed,
        violations=violations,
        warnings=warnings,
        score=round(score, 2),
    )


def validate_story_with_plan(
    text: str,
    constraints: ConstraintModel,
    world_model: Optional[WorldModel] = None,
    plan: Optional[BaseModel] = None,
) -> PostValidation:
    """
    Расширенная валидация: проверка по ограничениям + по плану.

    Дополнительно к validate_story проверяет:
    - Упоминаются ли персонажи из арок
    - Есть ли конфликтная дуга в тексте
    - Соответствует ли структура плану
    """
    # Базовая валидация
    base = validate_story(text, constraints, world_model)

    if plan is None:
        return base

    violations = list(base.violations)
    warnings = list(base.warnings)
    text_lower = text.lower()

    # Проверка: персонажи из арок упоминаются в тексте
    arcs = getattr(plan, 'character_arcs', [])
    if arcs:
        mentioned_chars = set()
        for word in text.split():
            w = word.strip('.,!?;:').lower()
            if len(w) > 3:
                for arc in arcs:
                    if w in arc.character.lower():
                        mentioned_chars.add(arc.character)

        missing = [arc.character for arc in arcs if arc.character not in mentioned_chars]
        if missing and len(missing) == len(arcs):
            warnings.append(
                f"Ни один персонаж из арок не упомянут: {', '.join(missing)}."
            )

    # Проверка: конфликт отражён в тексте
    conflicts = getattr(plan, 'conflicts', [])
    if conflicts:
        conflict = conflicts[0]
        tension_words = conflict.tension_source.lower().split()[:3]
        if not any(w in text_lower for w in tension_words if len(w) > 3):
            warnings.append(
                f"Источник конфликта '{conflict.tension_source}' может не отражён в тексте."
            )

    # Проверка: структура истории
    structure = getattr(plan, 'story_structure', [])
    if structure:
        # Проверяем что есть хотя бы завязка и развязка
        has_beginning = any(
            kw in text_lower
            for kw in ["начал", "перв", "однажд", "в то время"]
        )
        has_ending = any(
            kw in text_lower
            for kw in ["заверш", "в конце", "наконец", "таким образом"]
        )
        if len(structure) >= 3 and not has_beginning and not has_ending:
            warnings.append("Структура плана (3+ шагов) может не отражена в тексте.")

    # Пересчёт score
    hard_violations = sum(1 for v in violations if v.severity == "hard")
    soft_violations = sum(1 for v in violations if v.severity == "soft")
    score = max(0.0, 1.0 - (hard_violations * 0.3) - (soft_violations * 0.1) - (len(warnings) * 0.05))
    passed = hard_violations == 0

    return PostValidation(
        passed=passed,
        violations=violations,
        warnings=warnings,
        score=round(score, 2),
    )
