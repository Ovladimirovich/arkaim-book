"""Уровни источников и протокол provenance для каждого факта мира.

M1: добавлен ProvenanceCategory — семантическая категория происхождения,
независимая от SourceLevel (вес достоверности).

Принцип двух измерений:
  category  →  ОТКУДА взялось утверждение?
  confidence →  НАСКОЛЬКО уверены в нём?

HYPOTHESIS с confidence=1.0 остаётся HYPOTHESIS.
EXTERNAL_SOURCE с confidence=1.0 не становится AUTHOR_CANON.
"""

from __future__ import annotations

from enum import Enum
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


# ── Category: семантика происхождения ────────────────────────────────────────
# NOT confounded with confidence. Category is an ontological label.
# ─────────────────────────────────────────────────────────────────────────────

class ProvenanceCategory(str, Enum):
    """Категория происхождения факта.

    Каждое утверждение в системе должно иметь category.
    Category определяет, может ли этот факт быть использован
    для автоматического изменения канона.

    Иерархия доверия (category → can override):
      AUTHOR_CANON   →  никто не может переписать
      DERIVED        →  производное от канона
      RECONSTRUCTION →  внешние данные + канон
      HYPOTHESIS     →  системная гипотеза
      ARTISTIC_MODEL →  визуальное/творческое допущение
      FUTURE_EXTRAPOLATION →  проекция в будущее
      EXTERNAL_SOURCE →  данные извне (не могут стать каноном автоматически)
    """

    AUTHOR_CANON = "AUTHOR_CANON"
    """Прямое утверждение из первоисточника (КНИГА.md)."""

    DERIVED = "DERIVED"
    """Выведено из канона логическим анализом."""

    EXTERNAL_SOURCE = "EXTERNAL_SOURCE"
    """Внешний исторический/научный/академический источник."""

    RECONSTRUCTION = "RECONSTRUCTION"
    """Восстановление на основе внешних данных + канона."""

    HYPOTHESIS = "HYPOTHESIS"
    """Системная гипотеза, выдвинутая анализом."""

    ARTISTIC_MODEL = "ARTISTIC_MODEL"
    """Художественное допущение, визуальная интерпретация."""

    FUTURE_EXTRAPOLATION = "FUTURE_EXTRAPOLATION"
    """Проекция развития от канона в будущее."""

    UNKNOWN = "UNKNOWN"
    """Происхождение не определено (legacy данные)."""


# ── SourceLevel: вес достоверности (legacy, backward-compatible) ─────────────
# ─────────────────────────────────────────────────────────────────────────────

class SourceLevel(str, Enum):
    """Каждый факт должен иметь метку происхождения.

    Уровни упорядочены по убыванию достоверности (вес для совместимости):
    CANON=1.0, AUTHOR_INTERPRETATION=0.85, HISTORICAL=0.8, MYTHOLOGICAL=0.7,
    SCIENTIFIC=0.6, SYSTEM_INTERPRETATION=0.5, USER_HYPOTHESIS=0.3.

    M1: SourceLevel остаётся как weight-измерение.
    ProvenanceCategory — как category-измерение.
    """

    CANON = "CANON"
    AUTHOR_INTERPRETATION = "AUTHOR_INTERPRETATION"
    HISTORICAL = "HISTORICAL"
    MYTHOLOGICAL = "MYTHOLOGICAL"
    SCIENTIFIC = "SCIENTIFIC"
    SYSTEM_INTERPRETATION = "SYSTEM_INTERPRETATION"
    USER_HYPOTHESIS = "USER_HYPOTHESIS"


# ── Mapping: category → default source_level (backward compat) ──────────────

SOURCE_LEVEL_WEIGHTS: dict[SourceLevel, float] = {
    SourceLevel.CANON: 1.0,
    SourceLevel.AUTHOR_INTERPRETATION: 0.85,
    SourceLevel.HISTORICAL: 0.8,
    SourceLevel.MYTHOLOGICAL: 0.7,
    SourceLevel.SCIENTIFIC: 0.6,
    SourceLevel.SYSTEM_INTERPRETATION: 0.5,
    SourceLevel.USER_HYPOTHESIS: 0.3,
}

SOURCE_CATEGORY_DEFAULT_LEVEL: dict[ProvenanceCategory, SourceLevel] = {
    ProvenanceCategory.AUTHOR_CANON: SourceLevel.CANON,
    ProvenanceCategory.DERIVED: SourceLevel.SYSTEM_INTERPRETATION,
    ProvenanceCategory.EXTERNAL_SOURCE: SourceLevel.HISTORICAL,
    ProvenanceCategory.RECONSTRUCTION: SourceLevel.HISTORICAL,
    ProvenanceCategory.HYPOTHESIS: SourceLevel.USER_HYPOTHESIS,
    ProvenanceCategory.ARTISTIC_MODEL: SourceLevel.MYTHOLOGICAL,
    ProvenanceCategory.FUTURE_EXTRAPOLATION: SourceLevel.USER_HYPOTHESIS,
    ProvenanceCategory.UNKNOWN: SourceLevel.SYSTEM_INTERPRETATION,
}

SOURCE_CATEGORY_LABELS: dict[ProvenanceCategory, dict[str, str]] = {
    ProvenanceCategory.AUTHOR_CANON: {
        "label": "Авторский канон",
        "color": "green",
        "description": "Прямо из текста КНИГА.md",
    },
    ProvenanceCategory.DERIVED: {
        "label": "Производное",
        "color": "blue",
        "description": "Выведено из канона анализом",
    },
    ProvenanceCategory.EXTERNAL_SOURCE: {
        "label": "Внешний источник",
        "color": "orange",
        "description": "Википедия, Semantic Scholar, OpenAlex",
    },
    ProvenanceCategory.RECONSTRUCTION: {
        "label": "Реконструкция",
        "color": "purple",
        "description": "Восстановление на основе археологии и канона",
    },
    ProvenanceCategory.HYPOTHESIS: {
        "label": "Гипотеза",
        "color": "gold",
        "description": "Системная гипотеза, требует проверки",
    },
    ProvenanceCategory.ARTISTIC_MODEL: {
        "label": "Художественная модель",
        "color": "cyan",
        "description": "Визуальная/творческая интерпретация",
    },
    ProvenanceCategory.FUTURE_EXTRAPOLATION: {
        "label": "Будущее extrapolation",
        "color": "magenta",
        "description": "Проекция от канона в будущее",
    },
    ProvenanceCategory.UNKNOWN: {
        "label": "Неизвестно",
        "color": "default",
        "description": "Происхождение не классифицировано",
    },
}


# ── ProvenanceTag: два измерения (category + confidence) ─────────────────────
# ─────────────────────────────────────────────────────────────────────────────

class ProvenanceTag(BaseModel):
    """Протокол происхождения факта.

    M1: добавлено поле category (ProvenanceCategory).
    Поле category — семантическая категория происхождения.
    Поле confidence — количественная уверенность.

    Примеры:
      ProvenanceTag(category=AUTHOR_CANON, confidence=1.0)
      ProvenanceTag(category=EXTERNAL_SOURCE, confidence=0.72)
      ProvenanceTag(category=HYPOTHESIS, confidence=0.41)
      ProvenanceTag(category=HYPOTHESIS, confidence=0.95)  # всё ещё HYPOTHESIS

    Backward compatibility: при отсутствии category используется дефолт
    из SOURCE_CATEGORY_DEFAULT_LEVEL[SourceLevel].
    """

    source_level: SourceLevel
    category: ProvenanceCategory = ProvenanceCategory.UNKNOWN
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    added_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    added_by: str = "system"
    notes: Optional[str] = None

    def is_canon(self) -> bool:
        """Является ли этот тег авторским каноном."""
        return self.category == ProvenanceCategory.AUTHOR_CANON

    def is_external(self) -> bool:
        """Является ли этот тег внешним источником."""
        return self.category == ProvenanceCategory.EXTERNAL_SOURCE

    def is_hypothesis(self) -> bool:
        """Является ли этот тег гипотезой."""
        return self.category == ProvenanceCategory.HYPOTHESIS

    def is_reconstruction(self) -> bool:
        """Является ли этот тег реконструкцией."""
        return self.category == ProvenanceCategory.RECONSTRUCTION

    def is_derived(self) -> bool:
        """Является ли этот тег производным."""
        return self.category == ProvenanceCategory.DERIVED

    def is_artistic(self) -> bool:
        """Является ли этот тег художественной моделью."""
        return self.category == ProvenanceCategory.ARTISTIC_MODEL

    def is_future(self) -> bool:
        """Является ли этот тег экстраполяцией в будущее."""
        return self.category == ProvenanceCategory.FUTURE_EXTRAPOLATION

    def is_unknown(self) -> bool:
        """Происхождение не определено."""
        return self.category == ProvenanceCategory.UNKNOWN

    def to_dict(self) -> dict:
        return {
            "source_level": self.source_level.value,
            "category": self.category.value,
            "source_url": self.source_url,
            "source_title": self.source_title,
            "confidence": self.confidence,
            "added_at": self.added_at.isoformat(),
            "added_by": self.added_by,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProvenanceTag":
        """Обратное преобразование из dict (для миграции legacy данных)."""
        category_val = data.get("category")
        if category_val is None:
            # Legacy: выводить category из source_level
            cat = SOURCE_CATEGORY_DEFAULT_LEVEL.get(
                SourceLevel(data.get("source_level", "CANON")),
                ProvenanceCategory.UNKNOWN,
            )
            data["category"] = cat
        return cls(**data)


# ── Helpers ──────────────────────────────────────────────────────────────────

def canonical_provenance(
    source_url: Optional[str] = None,
    source_title: Optional[str] = None,
    notes: Optional[str] = None,
) -> ProvenanceTag:
    """Создать канонический тег (автоматически для прямого извлечения из книги)."""
    return ProvenanceTag(
        source_level=SourceLevel.CANON,
        category=ProvenanceCategory.AUTHOR_CANON,
        source_url=source_url,
        source_title=source_title,
        confidence=1.0,
        notes=notes,
    )


def external_provenance(
    source_url: Optional[str] = None,
    source_title: Optional[str] = None,
    confidence: float = 0.7,
    notes: Optional[str] = None,
) -> ProvenanceTag:
    """Создать тег для внешнего источника."""
    return ProvenanceTag(
        source_level=SourceLevel.HISTORICAL,
        category=ProvenanceCategory.EXTERNAL_SOURCE,
        source_url=source_url,
        source_title=source_title,
        confidence=confidence,
        notes=notes,
    )


def hypothesis_provenance(
    source_title: Optional[str] = None,
    confidence: float = 0.5,
    notes: Optional[str] = None,
) -> ProvenanceTag:
    """Создать тег для гипотезы."""
    return ProvenanceTag(
        source_level=SourceLevel.USER_HYPOTHESIS,
        category=ProvenanceCategory.HYPOTHESIS,
        source_title=source_title,
        confidence=confidence,
        notes=notes,
    )


def derived_provenance(
    source_title: Optional[str] = None,
    confidence: float = 0.8,
    notes: Optional[str] = None,
) -> ProvenanceTag:
    """Создать тег для производного вывода."""
    return ProvenanceTag(
        source_level=SourceLevel.SYSTEM_INTERPRETATION,
        category=ProvenanceCategory.DERIVED,
        source_title=source_title,
        confidence=confidence,
        notes=notes,
    )


# ── Labels for UI ────────────────────────────────────────────────────────────

SOURCE_LEVEL_LABELS = {
    SourceLevel.CANON: {"label": "Канон книги", "color": "green", "description": "Прямо из текста"},
    SourceLevel.AUTHOR_INTERPRETATION: {"label": "Авторская интерпретация", "color": "blue", "description": "Материалы автора"},
    SourceLevel.HISTORICAL: {"label": "Исторические источники", "color": "orange", "description": "Летописи, археология"},
    SourceLevel.MYTHOLOGICAL: {"label": "Мифологические источники", "color": "purple", "description": "Эпосы, легенды"},
    SourceLevel.SCIENTIFIC: {"label": "Научные гипотезы", "color": "cyan", "description": "Исследования"},
    SourceLevel.SYSTEM_INTERPRETATION: {"label": "Интерпретация системы", "color": "geekblue", "description": "Выводы анализа"},
    SourceLevel.USER_HYPOTHESIS: {"label": "Гипотеза пользователя", "color": "magenta", "description": "Идеи читателей"},
}
