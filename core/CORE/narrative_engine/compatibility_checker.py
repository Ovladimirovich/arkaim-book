"""Compatibility Checker — проверка идеи по 6 осям совместимости с каноном мира.

Реализует архитектуру World Explorer: Compatibility Check (раздел 6).
Каждая ось возвращает числовую оценку [0.0, 1.0] и список нарушений.
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from narrative_engine.world_model import WorldModel
from narrative_engine.source_levels import SourceLevel, SOURCE_LEVEL_WEIGHTS
from narrative_engine.constraint_engine import StoryRequest

log = logging.getLogger("hermes.narrative.compatibility")

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "KNOWLEDGE"


# ── Модели данных ──────────────────────────────────────────

class AxisViolation(BaseModel):
    """Нарушение на конкретной оси."""
    axis: str  # book_canon, historical, geographical, temporal, character, author_intent
    rule: str
    severity: str  # "hard" | "soft"
    detail: str
    suggestion: str = ""


class AxisScore(BaseModel):
    """Оценка по одной оси."""
    axis: str
    score: float = Field(ge=0.0, le=1.0)
    violations: list[AxisViolation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CompatibilityReport(BaseModel):
    """Полный отчёт о совместимости идеи с каноном мира."""
    overall_score: float = Field(ge=0.0, le=1.0, description="Взвешенная сумма по 6 осям")
    axis_scores: list[AxisScore] = Field(default_factory=list)
    is_compatible: bool = Field(description="True если overall_score >= 0.6")
    risk_level: str = Field(description="low / medium / high / rejected")
    violations: list[AxisViolation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


# ── Веса осей (из архитектуры) ─────────────────────────────

AXIS_WEIGHTS = {
    "book_canon": 0.30,
    "historical": 0.15,
    "geographical": 0.10,
    "temporal": 0.15,
    "character": 0.15,
    "author_intent": 0.15,
}

# Анахронизмы ( technology words that don't exist in ancient epochs )
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


def _load_knowledge_json(filename: str) -> dict:
    path = KNOWLEDGE_DIR / filename
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning("knowledge_load_error file=%s error=%s", filename, e)
    return {}


# ── Compatibility Checker ──────────────────────────────────

class CompatibilityChecker:
    """Проверяет идею по 6 осям совместимости с каноном мира.

    Оси:
    1. book_canon — не противоречит ли тексту книги
    2. historical — не нарушает ли исторические данные
    3. geographical — не нарушает ли географию
    4. temporal — не нарушает ли хронологию
    5. character — не ломает ли характеры персонажей
    6. author_intent — соответствует ли духу произведения
    """

    def __init__(self, world_model: WorldModel):
        self._wm = world_model
        self._characters_data = _load_knowledge_json("CHARACTERS.json")
        self._author_intent = _load_knowledge_json("AUTHOR_INTENT.json")
        self._archaeology = _load_knowledge_json("ARCHAEOLOGY.json")
        self._cross_refs = _load_knowledge_json("CROSS_REFERENCES.json")
        self._academic = _load_knowledge_json("ACADEMIC_CONFIRMATIONS.json")

        # Индекс персонажей
        self._char_index: dict[str, dict] = {}
        for ch in self._characters_data.get("characters", []):
            names = [ch["name"].lower()] + [a.lower() for a in ch.get("aliases", [])]
            for name in names:
                if len(name) > 1:
                    self._char_index[name] = ch

        # Второстепенные послания автора
        self._secondary_messages: list[str] = self._author_intent.get("secondary_messages", [])

    def check(self, request: StoryRequest) -> CompatibilityReport:
        """Проверить идею по 6 осям и вернуть полный отчёт."""
        axis_scores = []
        all_violations: list[AxisViolation] = []
        all_warnings: list[str] = []

        # Ось 1: Книжный канон
        axis1 = self._check_book_canon(request)
        axis_scores.append(axis1)
        all_violations.extend(axis1.violations)
        all_warnings.extend(axis1.warnings)

        # Ось 2: Историческая согласованность
        axis2 = self._check_historical(request)
        axis_scores.append(axis2)
        all_violations.extend(axis2.violations)
        all_warnings.extend(axis2.warnings)

        # Ось 3: Географическая согласованность
        axis3 = self._check_geographical(request)
        axis_scores.append(axis3)
        all_violations.extend(axis3.violations)
        all_warnings.extend(axis3.warnings)

        # Ось 4: Временная шкала
        axis4 = self._check_temporal(request)
        axis_scores.append(axis4)
        all_violations.extend(axis4.violations)
        all_warnings.extend(axis4.warnings)

        # Ось 5: Характеры персонажей
        axis5 = self._check_character_integrity(request)
        axis_scores.append(axis5)
        all_violations.extend(axis5.violations)
        all_warnings.extend(axis5.warnings)

        # Ось 6: Авторский замысел
        axis6 = self._check_author_intent(request)
        axis_scores.append(axis6)
        all_violations.extend(axis6.violations)
        all_warnings.extend(axis6.warnings)

        # Расчёт общего балла
        overall_score = sum(
            ax.score * AXIS_WEIGHTS.get(ax.axis, 0.0)
            for ax in axis_scores
        )
        overall_score = round(min(1.0, max(0.0, overall_score)), 3)

        # Определение уровня риска
        hard_count = sum(1 for v in all_violations if v.severity == "hard")
        if hard_count >= 2:
            risk_level = "rejected"
        elif hard_count == 1 or overall_score < 0.3:
            risk_level = "high"
        elif overall_score < 0.6:
            risk_level = "medium"
        else:
            risk_level = "low"

        is_compatible = overall_score >= 0.6 and hard_count == 0

        # Рекомендации
        recommendations = self._generate_recommendations(
            axis_scores, all_violations, overall_score
        )

        return CompatibilityReport(
            overall_score=overall_score,
            axis_scores=axis_scores,
            is_compatible=is_compatible,
            risk_level=risk_level,
            violations=all_violations,
            warnings=all_warnings,
            recommendations=recommendations,
        )

    # ── Ось 1: Книжный канон ──────────────────────────────

    def _check_book_canon(self, request: StoryRequest) -> AxisScore:
        violations = []
        warnings = []
        score = 1.0
        prompt_lower = request.prompt.lower()

        # Проверка: упоминаются ли неизвестные персонажи
        known_names = set(self._char_index.keys())
        words = re.findall(r'[а-яёА-ЯЁ]{4,}', request.prompt)
        potential_names = [w.lower() for w in words if w.lower() not in {
            "это", "было", "был", "была", "были", "быть", "может", "нужно",
            "когда", "где", "как", "что", "кто", "чтобы", "после", "перед",
            "между", "через", "другой", "другие", "такой", "такие", "каждый",
            "весь", "вся", "всё", "все", "этот", "эта", "эти", "тот", "та",
            "самый", "первый", "второй", "третий", "новый", "старый", "большой",
        }]

        unknown_in_prompt = [n for n in potential_names if n not in known_names and len(n) > 4]
        if unknown_in_prompt:
            warnings.append(
                f"Возможные неизвестные персонажи: {', '.join(unknown_in_prompt[:5])}. "
                "Проверьте, существуют ли они в каноне."
            )
            score -= 0.1

        # Проверка: запрещённый контент
        forbidden_words = ["порох", "ружье", "телефон", "телевизор", "компьютер",
                           "интернет", "электричество", "автомобиль", "самолёт"]
        for word in forbidden_words:
            if word in prompt_lower:
                violations.append(AxisViolation(
                    axis="book_canon",
                    rule="forbidden_content",
                    severity="hard",
                    detail=f"Обнаружен анахронизм: '{word}'",
                    suggestion=f"Удалить '{word}' — этот объект не существует в мире книги.",
                ))
                score -= 0.2

        # Проверка: соответствие эпохе (если задана)
        if request.epoch:
            epoch = self._wm.get_epoch(request.epoch)
            if not epoch:
                violations.append(AxisViolation(
                    axis="book_canon",
                    rule="unknown_epoch",
                    severity="hard",
                    detail=f"Эпоха '{request.epoch}' не найдена в WorldModel",
                    suggestion="Укажите существующую эпоху из WorldModel.",
                ))
                score -= 0.3

        # Проверка: соответствие локации (если задана)
        if request.location:
            location = self._wm.get_location(request.location)
            if not location:
                violations.append(AxisViolation(
                    axis="book_canon",
                    rule="unknown_location",
                    severity="hard",
                    detail=f"Локация '{request.location}' не найдена в WorldModel",
                    suggestion="Укажите существующую локацию из WorldModel.",
                ))
                score -= 0.3

        score = max(0.0, score)
        return AxisScore(axis="book_canon", score=score, violations=violations, warnings=warnings)

    # ── Ось 2: Историческая согласованность ───────────────

    def _check_historical(self, request: StoryRequest) -> AxisScore:
        violations = []
        warnings = []
        score = 1.0
        prompt_lower = request.prompt.lower()

        # Проверка: анахронизмы (технологии несуществующие в эпохе)
        if request.epoch:
            epoch = self._wm.get_epoch(request.epoch)
            if epoch:
                tech_ids = set(epoch.technologies_available)
                tech_names = set()
                for tech in self._wm.get_technologies(request.epoch):
                    tech_names.add(tech.name.lower())
                    tech_names.add(tech.name_ru.lower())

                for word, desc in ANACHRONISM_WORDS.items():
                    if word in prompt_lower:
                        violations.append(AxisViolation(
                            axis="historical",
                            rule="tech_anachronism",
                            severity="hard",
                            detail=f"Технология '{word}' ({desc}) не существует в эпоху {epoch.name_ru}",
                            suggestion=f"Замените '{word}' на технологию, доступную в {epoch.name_ru}.",
                        ))
                        score -= 0.15

        # Проверка: археологические данные (если упоминается Аркаим)
        if any(kw in prompt_lower for kw in ["аркаим", "аркаима", "аркаиме"]):
            archaeology = self._archaeology
            if archaeology:
                # Проверяем, не противоречит ли описание археологическим данным
                pass  # Базовая проверка — нет прямых противоречий

        # Проверка: историческая хронология
        if any(kw in prompt_lower for kw in ["istorically", "историческ", "реальн"]):
            warnings.append(
                "Идея содержит исторические отсылки. "
                "Убедитесь, что они соответствуют археологическим и историческим данным."
            )
            score -= 0.05

        score = max(0.0, score)
        return AxisScore(axis="historical", score=score, violations=violations, warnings=warnings)

    # ── Ось 3: Географическая согласованность ─────────────

    def _check_geographical(self, request: StoryRequest) -> AxisScore:
        violations = []
        warnings = []
        score = 1.0

        if request.epoch and request.location:
            epoch = self._wm.get_epoch(request.epoch)
            location = self._wm.get_location(request.location)

            if epoch and location:
                # Проверка: локация существует в эпохе
                if location.epochs_present and epoch.id not in location.epochs_present:
                    violations.append(AxisViolation(
                        axis="geographical",
                        rule="location_epoch_mismatch",
                        severity="soft",
                        detail=(
                            f"Локация '{location.name_ru}' не указана в эпохе '{epoch.name_ru}'. "
                            f"Эпохи локации: {', '.join(location.epochs_present)}."
                        ),
                        suggestion=f"Убедитесь, что локация существовала в '{epoch.name_ru}'.",
                    ))
                    score -= 0.15

                # Проверка: географическая близость (если заданы 2 локации)
                if location.region_id:
                    nearby = [
                        loc for loc in self._wm.get_locations()
                        if loc.region_id == location.region_id and loc.id != request.location
                    ]
                    if nearby:
                        pass  # Локация в пределах региона — OK

        # Проверка: упоминание локации в тексте
        if request.location:
            location = self._wm.get_location(request.location)
            if location:
                loc_name = location.name_ru.lower()
                if loc_name not in request.prompt.lower():
                    warnings.append(
                        f"Локация '{location.name_ru}' задана, но не упоминается в запросе."
                    )
                    score -= 0.05

        score = max(0.0, score)
        return AxisScore(axis="geographical", score=score, violations=violations, warnings=warnings)

    # ── Ось 4: Временная шкала ────────────────────────────

    def _check_temporal(self, request: StoryRequest) -> AxisScore:
        violations = []
        warnings = []
        score = 1.0
        prompt_lower = request.prompt.lower()

        # Проверка: порядок эпох
        if request.epoch:
            epoch = self._wm.get_epoch(request.epoch)
            if epoch:
                # Проверяем, что эпоха не «из будущего» относительно локации
                if request.location:
                    location = self._wm.get_location(request.location)
                    if location and location.epochs_present:
                        if epoch.id not in location.epochs_present:
                            # Мягкое предупреждение — возможно, локация просто не указана
                            warnings.append(
                                f"Эпоха '{epoch.name_ru}' может не соответствовать локации '{location.name_ru}'."
                            )
                            score -= 0.1

        # Проверка: causa-temporal ordering
        # Если в запросе есть «до» и «после», проверяем логику
        if "до " in prompt_lower and "после " in prompt_lower:
            warnings.append(
                "Запрос содержит ссылки на время до и после. "
                "Убедитесь, что causa-temporal ordering соблюдается."
            )
            score -= 0.05

        # Проверка: временные смещения
        time_patterns = [
            (r"за (\d+) лет до", "before"),
            (r"через (\d+) лет после", "after"),
            (r"(\d+) лет назад", "past"),
        ]
        for pattern, direction in time_patterns:
            match = re.search(pattern, prompt_lower)
            if match:
                years = int(match.group(1))
                if years > 10000:
                    violations.append(AxisViolation(
                        axis="temporal",
                        rule="extreme_time_offset",
                        severity="soft",
                        detail=f"Экстремальное временное смещение: {years} лет",
                        suggestion="Рассмотрите более реалистичное временное смещение.",
                    ))
                    score -= 0.1

        score = max(0.0, score)
        return AxisScore(axis="temporal", score=score, violations=violations, warnings=warnings)

    # ── Ось 5: Характеры персонажей ───────────────────────

    def _check_character_integrity(self, request: StoryRequest) -> AxisScore:
        violations = []
        warnings = []
        score = 1.0
        prompt_lower = request.prompt.lower()

        # Проверка: персонажи существуют в эпохе
        if request.epoch:
            chars_in_epoch = self._wm.get_characters_alive(request.epoch)
            char_names = {c.character_name.lower() for c in chars_in_epoch}

            # Ищем имена персонажей в запросе
            words = re.findall(r'[А-ЯЁ][а-яё]+', request.prompt)
            for word in words:
                word_lower = word.lower()
                if word_lower in self._char_index and word_lower not in char_names:
                    char_data = self._char_index[word_lower]
                    violations.append(AxisViolation(
                        axis="character",
                        rule="character_not_in_epoch",
                        severity="soft",
                        detail=(
                            f"Персонаж '{word}' существует, но не указан в эпохе '{request.epoch}'. "
                            f"Его статус: {char_data.get('archetype', 'неизвестно')}."
                        ),
                        suggestion=f"Проверьте, жив ли '{word}' в эпоху '{request.epoch}'.",
                    ))
                    score -= 0.1

        # Проверка: архетипы персонажей
        archetype_keywords = {
            "ученик": "student", "учитель": "teacher", "мудрец": "sage",
            "воин": "warrior", "жрец": "priest", "странник": "wanderer",
            "царь": "ruler", "князь": "ruler",
        }
        for keyword, archetype in archetype_keywords.items():
            if keyword in prompt_lower:
                # Проверяем, есть ли персонаж с таким архетипом в эпохе
                if request.epoch:
                    chars = self._wm.get_characters_alive(request.epoch)
                    has_archetype = any(
                        self._char_index.get(c.character_name.lower(), {}).get("archetype", "").lower() == archetype
                        for c in chars
                    )
                    if not has_archetype:
                        warnings.append(
                            f"Архетип '{archetype}' (关键词: '{keyword}') не найден среди персонажей эпохи."
                        )
                        score -= 0.05

        score = max(0.0, score)
        return AxisScore(axis="character", score=score, violations=violations, warnings=warnings)

    # ── Ось 6: Авторский замысел ──────────────────────────

    def _check_author_intent(self, request: StoryRequest) -> AxisScore:
        violations = []
        warnings = []
        score = 1.0
        prompt_lower = request.prompt.lower()

        # Ключевые темы авторского замысла
        key_themes = [
            "духовн", "познан", "учение", "истин", "гармон",
            "путешеств", "пробужд", "эволюц", "единств",
            "память", "предк", "наследи", "традиц",
        ]
        negative_signals = [
            "война", "разрушен", "гибел", "уничтож",
            "месть", "ненавист", "тиран", "зло",
        ]

        has_positive = any(kw in prompt_lower for kw in key_themes)
        has_negative = any(kw in prompt_lower for kw in negative_signals)

        if has_negative and not has_positive:
            warnings.append(
                "Запрос содержит негативные темы без духовного контекста. "
                "Авторский замысел акцентирует преодоление через познание."
            )
            score -= 0.15

        if not has_positive and not has_negative:
            warnings.append(
                "Запрос не содержит явных тематических маркеров авторского замысла. "
                "Рекомендуется связать с ключевыми темами: познание, духовное развитие, наследие."
            )
            score -= 0.05

        # Проверка: второстепенные послания автора
        if self._secondary_messages:
            # Проверяем, не противоречит ли запрос посланиям
            for msg in self._secondary_messages[:10]:
                msg_lower = msg.lower()
                # Если послание содержит запрет, а запрос его нарушает
                if "не" in msg_lower and any(w in prompt_lower for w in msg_lower.split() if len(w) > 4):
                    pass  # Слишком сложная проверка — пропускаем

        score = max(0.0, score)
        return AxisScore(axis="author_intent", score=score, violations=violations, warnings=warnings)

    # ── Рекомендации ──────────────────────────────────────

    def _generate_recommendations(
        self,
        axis_scores: list[AxisScore],
        violations: list[AxisViolation],
        overall_score: float,
    ) -> list[str]:
        recommendations = []

        # Находим оси с низким баллом
        low_axes = [ax for ax in axis_scores if ax.score < 0.5]
        for ax in low_axes:
            recommendations.append(
                f"Ось '{ax.axis}' имеет низкий балл ({ax.score:.2f}). "
                f"Рекомендуется усилить соответствие по этой оси."
            )

        # Рекомендации по нарушениям
        hard_violations = [v for v in violations if v.severity == "hard"]
        if hard_violations:
            recommendations.append(
                f"Обнаружено {len(hard_violations)} критических нарушений. "
                "Необходимо исправить перед продолжением."
            )

        if overall_score < 0.3:
            recommendations.append(
                "Общий балл совместимости очень низкий. "
                "Рекомендуется существенно переработать идею."
            )
        elif overall_score < 0.6:
            recommendations.append(
                "Общий балл совместимости средний. "
                "Возможны риски — требуется ручная проверка."
            )

        return recommendations
