"""TemporalPrecision — точность датировки.

M2: четкое разделение temporal precision и confidence.

Precision отвечает: «Насколько точно мы знаем временные границы?»
Confidence отвечает: «Насколько уверены в существовании этого факта?»
"""

from __future__ import annotations

from enum import Enum


class TemporalPrecision(str, Enum):
    """Точность временной датировки.

    Упорядочены по убыванию точности.
    UNKNOWN — не ошибка, а честная оценка.
    """

    EXACT = "EXACT"
    """Точная дата известна (год, месяц, день)."""

    YEAR = "YEAR"
    """Год известен, месяц/день — нет."""

    YEAR_RANGE = "YEAR_RANGE"
    """Диапазон лет (например, 1500–1400 BCE)."""

    DECADE = "DECADE"
    """Десятилетие (например, 1450-е BCE)."""

    CENTURY = "CENTURY"
    """Века (например, XVI век BCE)."""

    MILLENNIUM = "MILLENNIUM"
    """Тысячелетие (например, II тысячелетие BCE)."""

    ARCHAEOLOGICAL_PERIOD = "ARCHAEOLOGICAL_PERIOD"
    """Археологический период (например, «эпоха бронзы», «ранний железный век»)."""

    RELATIVE = "RELATIVE"
    """Относительная датировка (например, «до Аркаима», «после катастрофы»)."""

    STRATIGRAPHIC = "STRATIGRAPHIC"
    """Стратиграфический порядок (например, «слой III над слоем IV»)."""

    UNKNOWN = "UNKNOWN"
    """Временные границы неизвестны. НЕ ошибка — честная оценка."""

    # Aliases for backward compatibility with narrative text
    ANCESTRAL = "RELATIVE"   # «в древности» → RELATIVE
    MYTHICAL = "RELATIVE"    # «в мифические времена» → RELATIVE
    LEGENDARY = "RELATIVE"   # «в легендарную эпоху» → RELATIVE


PRECISION_ORDER: dict[TemporalPrecision, int] = {
    TemporalPrecision.EXACT: 9,
    TemporalPrecision.YEAR: 8,
    TemporalPrecision.YEAR_RANGE: 7,
    TemporalPrecision.DECADE: 6,
    TemporalPrecision.CENTURY: 5,
    TemporalPrecision.MILLENNIUM: 4,
    TemporalPrecision.ARCHAEOLOGICAL_PERIOD: 3,
    TemporalPrecision.RELATIVE: 2,
    TemporalPrecision.STRATIGRAPHIC: 1,
    TemporalPrecision.UNKNOWN: 0,
}


def resolve_precision(value: str) -> TemporalPrecision:
    """Восстановить TemporalPrecision из строки (для миграции)."""
    try:
        return TemporalPrecision(value)
    except ValueError:
        # Aliases
        alias_map = {
            "ANCESTRAL": TemporalPrecision.RELATIVE,
            "MYTHICAL": TemporalPrecision.RELATIVE,
            "LEGENDARY": TemporalPrecision.RELATIVE,
            "relative": TemporalPrecision.RELATIVE,
            "unknown": TemporalPrecision.UNKNOWN,
            "exact": TemporalPrecision.EXACT,
            "year": TemporalPrecision.YEAR,
            "century": TemporalPrecision.CENTURY,
            "archaeological_period": TemporalPrecision.ARCHAEOLOGICAL_PERIOD,
        }
        return alias_map.get(value.lower(), TemporalPrecision.UNKNOWN)


def is_known_precision(precision: TemporalPrecision) -> bool:
    """Является ли precision известной (не UNKNOWN)."""
    return precision != TemporalPrecision.UNKNOWN


def precision_label(precision: TemporalPrecision) -> str:
    """Человеко-читаемая метка для precision."""
    labels = {
        TemporalPrecision.EXACT: "Точная дата",
        TemporalPrecision.YEAR: "Год",
        TemporalPrecision.YEAR_RANGE: "Диапазон лет",
        TemporalPrecision.DECADE: "Десятилетие",
        TemporalPrecision.CENTURY: "Век",
        TemporalPrecision.MILLENNIUM: "Тысячелетие",
        TemporalPrecision.ARCHAEOLOGICAL_PERIOD: "Археологический период",
        TemporalPrecision.RELATIVE: "Относительная",
        TemporalPrecision.STRATIGRAPHIC: "Стратиграфическая",
        TemporalPrecision.UNKNOWN: "Неизвестно",
    }
    return labels.get(precision, precision.value)
