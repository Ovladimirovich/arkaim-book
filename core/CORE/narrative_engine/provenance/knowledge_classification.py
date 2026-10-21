"""Классификация KNOWLEDGE/*.json по provenance category.

M1: каждый JSON-файл в KNOWLEDGE/ получает явную provenance-категорию.
Это НЕ меняет файлы — это документация и справочник для системы.

Критическое правило:
  АКАДЕМИЧЕСКИЕ ПОДТВЕРЖДЕНИЯ + ГЛУБОКИЙ АНАЛИЗ LLM ≠ AUTHOR_CANON

Файлы с суффиксами *_DEEP, *_EXPANDED, ACADEMIC_CONFIRMATIONS, ARCHAEOLOGY_DEEP
содержат внешние/LLM-сгенерированные данные и НЕ являются каноном.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class KnowledgeCategory(str, Enum):
    """Категория provenance для KNOWLEDGE/*.json файлов."""

    AUTHOR_CANON = "AUTHOR_CANON"
    """Прямые структурированные данные из книги."""

    DERIVED = "DERIVED"
    """Производные данные (профили, индексы)."""

    EXTERNAL_SOURCE = "EXTERNAL_SOURCE"
    """Внешние исторические/археологические/академические данные."""

    RECONSTRUCTION = "RECONSTRUCTION"
    """Реконструкция на основе внешних данных."""

    HYPOTHESIS = "HYPOTHESIS"
    """LLM-обогащённые гипотезы."""

    ARTISTIC_MODEL = "ARTISTIC_MODEL"
    """Художественные модели."""

    MIXED = "MIXED"
    """Содержит смешанные источники (часть канон, часть нет)."""

    UNKNOWN = "UNKNOWN"
    """Категория не определена."""


@dataclass(frozen=True)
class KnowledgeFileClassification:
    """Классификация одного KNOWLEDGE файла.

    ``source_path`` — где файл физически лежит, если он не в ``core/KNOWLEDGE``
    (например, визуальный слой ``core/CORE/visual/VISUAL_KNOWLEDGE``).
    """

    filename: str
    category: KnowledgeCategory
    description: str
    is_canon: bool = False
    requires_author_review: bool = False
    confidence: float = 1.0
    source_path: str = ""


# ── Классификация всех файлов ─────────────────────────────────────────────────

KNOWLEDGE_CLASSIFICATION: list[KnowledgeFileClassification] = [
    # ── PRIMARY AUTHOR CANON ─────────────────────────────────────────────
    KnowledgeFileClassification(
        filename="BOOK_DOCUMENT.json",
        category=KnowledgeCategory.AUTHOR_CANON,
        description="Структурированный документ книги — первичный канон",
        is_canon=True,
    ),
    KnowledgeFileClassification(
        filename="BOOK_PROFILE.json",
        category=KnowledgeCategory.AUTHOR_CANON,
        description="Паспорт книги — производное от первичного канона",
        is_canon=True,
    ),
    KnowledgeFileClassification(
        filename="BOOK_GENOME.json",
        category=KnowledgeCategory.DERIVED,
        description="Геном книги — производная структура от BOOK_DOCUMENT",
        is_canon=False,
    ),
    KnowledgeFileClassification(
        filename="PLOT.json",
        category=KnowledgeCategory.AUTHOR_CANON,
        description="Сюжет книги — первичный канон",
        is_canon=True,
    ),
    KnowledgeFileClassification(
        filename="SYNOPSIS_DOCUMENT.json",
        category=KnowledgeCategory.AUTHOR_CANON,
        description="Документ синопсиса — вторичный авторский источник",
        is_canon=True,
        confidence=0.9,
    ),
    KnowledgeFileClassification(
        filename="SYNOPSIS_PROFILE.json",
        category=KnowledgeCategory.DERIVED,
        description="Паспорт синопсиса — производное",
        is_canon=False,
    ),

    # ── CHARACTER PROFILES ───────────────────────────────────────────────
    KnowledgeFileClassification(
        filename="CHARACTERS.json",
        category=KnowledgeCategory.DERIVED,
        description="Профили персонажей — извлечены из книги",
        is_canon=False,
    ),
    KnowledgeFileClassification(
        filename="character_profiles.json",
        category=KnowledgeCategory.DERIVED,
        description="Расширенные профили персонажей",
        is_canon=False,
    ),
    KnowledgeFileClassification(
        filename="character_deep_profiles.json",
        category=KnowledgeCategory.HYPOTHESIS,
        description="Глубокие профили — LLM-анализ, требует проверки",
        is_canon=False,
        requires_author_review=True,
    ),
    KnowledgeFileClassification(
        filename="deep_characters.json",
        category=KnowledgeCategory.HYPOTHESIS,
        description="Глубокие персонажи — гипотезы системы",
        is_canon=False,
        requires_author_review=True,
    ),

    # ── THEMES ───────────────────────────────────────────────────────────
    KnowledgeFileClassification(
        filename="THEMES_EXPANDED.json",
        category=KnowledgeCategory.HYPOTHESIS,
        description="Расширенные темы — LLM-обогащение, требует проверки",
        is_canon=False,
        requires_author_review=True,
    ),
    KnowledgeFileClassification(
        filename="THEMES_DEEP.json",
        category=KnowledgeCategory.HYPOTHESIS,
        description="Глубокие темы — LLM-анализ слоёв",
        is_canon=False,
        requires_author_review=True,
    ),

    # ── SYMBOLS ──────────────────────────────────────────────────────────
    KnowledgeFileClassification(
        filename="SYMBOLS.json",
        category=KnowledgeCategory.AUTHOR_CANON,
        description="Символы книги — канон",
        is_canon=True,
    ),
    KnowledgeFileClassification(
        filename="SYMBOLS_EXPANDED.json",
        category=KnowledgeCategory.HYPOTHESIS,
        description="Расширенные символы — LLM-анализ",
        is_canon=False,
        requires_author_review=True,
    ),
    KnowledgeFileClassification(
        filename="SYMBOLS_DEEP.json",
        category=KnowledgeCategory.HYPOTHESIS,
        description="Глубокие символы — LLM-анализ",
        is_canon=False,
        requires_author_review=True,
    ),

    # ── PHILOSOPHY & VALUES ──────────────────────────────────────────────
    KnowledgeFileClassification(
        filename="PHILOSOPHY.json",
        category=KnowledgeCategory.AUTHOR_CANON,
        description="Философия книги — канон",
        is_canon=True,
    ),
    KnowledgeFileClassification(
        filename="PHILOSOPHY_DEEP.json",
        category=KnowledgeCategory.HYPOTHESIS,
        description="Глубокая философия — LLM-анализ",
        is_canon=False,
        requires_author_review=True,
    ),
    KnowledgeFileClassification(
        filename="VALUES.json",
        category=KnowledgeCategory.AUTHOR_CANON,
        description="Ценности книги — канон",
        is_canon=True,
    ),
    KnowledgeFileClassification(
        filename="AUTHOR_INTENT.json",
        category=KnowledgeCategory.AUTHOR_CANON,
        description="Замысел автора — канон",
        is_canon=True,
    ),

    # ── GEOGRAPHY & ARCHAEOLOGY ──────────────────────────────────────────
    KnowledgeFileClassification(
        filename="GEOGRAPHY.json",
        category=KnowledgeCategory.MIXED,
        description="География — канон + внешние данные",
        is_canon=False,
        requires_author_review=True,
    ),
    KnowledgeFileClassification(
        filename="MAP_DATA.json",
        category=KnowledgeCategory.EXTERNAL_SOURCE,
        description="Данные карт — внешние/археологические",
        is_canon=False,
    ),
    KnowledgeFileClassification(
        filename="ARCHAEOLOGY.json",
        category=KnowledgeCategory.EXTERNAL_SOURCE,
        description="Археологические данные — внешние источники",
        is_canon=False,
    ),
    KnowledgeFileClassification(
        filename="ARCHAEOLOGY_DEEP.json",
        category=KnowledgeCategory.RECONSTRUCTION,
        description="Глубокая археология — реконструкция",
        is_canon=False,
        requires_author_review=True,
    ),

    # ── COSMOLOGY ────────────────────────────────────────────────────────
    KnowledgeFileClassification(
        filename="COSMOLOGY.json",
        category=KnowledgeCategory.MIXED,
        description="Космология — канон + интерпретации",
        is_canon=False,
        requires_author_review=True,
    ),
    KnowledgeFileClassification(
        filename="COSMOLOGY_DEEP.json",
        category=KnowledgeCategory.HYPOTHESIS,
        description="Глубокая космология — LLM-гипотезы",
        is_canon=False,
        requires_author_review=True,
    ),

    # ── EXTERNAL / ACADEMIC ──────────────────────────────────────────────
    KnowledgeFileClassification(
        filename="ACADEMIC_CONFIRMATIONS.json",
        category=KnowledgeCategory.EXTERNAL_SOURCE,
        description="Академические подтверждения — внешние источники",
        is_canon=False,
    ),
    KnowledgeFileClassification(
        filename="CROSS_REFERENCES.json",
        category=KnowledgeCategory.MIXED,
        description="Кросс-ссылки — смешанные источники",
        is_canon=False,
        requires_author_review=True,
    ),
    KnowledgeFileClassification(
        filename="CROSS_REFERENCES_DEEP.json",
        category=KnowledgeCategory.HYPOTHESIS,
        description="Глубокие кросс-ссылки — LLM-анализ",
        is_canon=False,
        requires_author_review=True,
    ),
    KnowledgeFileClassification(
        filename="ESOTERIC_CONNECTIONS.json",
        category=KnowledgeCategory.HYPOTHESIS,
        description="Эзотерические связи — гипотезы",
        is_canon=False,
        requires_author_review=True,
    ),
    KnowledgeFileClassification(
        filename="HIERARCHY_OF_LIGHT.json",
        category=KnowledgeCategory.HYPOTHESIS,
        description="Иерархия света — гипотезы системы",
        is_canon=False,
        requires_author_review=True,
    ),

    # ── CULTURAL ─────────────────────────────────────────────────────────
    KnowledgeFileClassification(
        filename="RITUALS.json",
        category=KnowledgeCategory.MIXED,
        description="Ритуалы — канон + реконструкция",
        is_canon=False,
        requires_author_review=True,
    ),
    KnowledgeFileClassification(
        filename="LANGUAGE.json",
        category=KnowledgeCategory.MIXED,
        description="Язык — канон + исследования",
        is_canon=False,
        requires_author_review=True,
    ),
    KnowledgeFileClassification(
        filename="PSYCHOLOGY.json",
        category=KnowledgeCategory.HYPOTHESIS,
        description="Психология персонажей — LLM-анализ",
        is_canon=False,
        requires_author_review=True,
    ),
    KnowledgeFileClassification(
        filename="TECHNOLOGY.json",
        category=KnowledgeCategory.MIXED,
        description="Технологии — канон + археология",
        is_canon=False,
        requires_author_review=True,
    ),
    KnowledgeFileClassification(
        filename="civilization_profiles.json",
        category=KnowledgeCategory.RECONSTRUCTION,
        description="Профили цивилизаций — реконструкция",
        is_canon=False,
        requires_author_review=True,
    ),
    KnowledgeFileClassification(
        filename="deep_concepts.json",
        category=KnowledgeCategory.HYPOTHESIS,
        description="Глубокие концепты — гипотезы",
        is_canon=False,
        requires_author_review=True,
    ),

    # ── VISUAL ───────────────────────────────────────────────────────────
    KnowledgeFileClassification(
        filename="EPOCH_PALETTES.json",
        category=KnowledgeCategory.ARTISTIC_MODEL,
        description="Палитры эпох — художественная модель",
        is_canon=False,
    ),
    KnowledgeFileClassification(
        filename="ENERGY_OF_PLACES.json",
        category=KnowledgeCategory.ARTISTIC_MODEL,
        description="Энергия мест — художественная модель",
        is_canon=False,
    ),
    KnowledgeFileClassification(
        filename="SCENE_PROMPTS.json",
        category=KnowledgeCategory.ARTISTIC_MODEL,
        description="Промпты сцен — визуальная модель",
        is_canon=False,
    ),
    # ── VISUAL KNOWLEDGE (core/CORE/visual/VISUAL_KNOWLEDGE) ──────────
    # Созданы агентом по «план Visual Intelligence, 19.07.2026 (агентская визуальная модель)». Каноном не являются:
    # это визуальная интерпретация, а не утверждение из КНИГА.md.
    KnowledgeFileClassification(
        filename="LOCATION_VISUALS.json",
        category=KnowledgeCategory.ARTISTIC_MODEL,
        description="Визуальные карточки мест — художественная модель; в плане подробно был расписан только «Аркаим», остальные карточки — допущения агента (план Visual Intelligence, 19.07.2026 (агентская визуальная модель))",
        is_canon=False,
        requires_author_review=True,
        source_path="core/CORE/visual/VISUAL_KNOWLEDGE/LOCATION_VISUALS.json",
    ),
    KnowledgeFileClassification(
        filename="CHARACTER_VISUALS.json",
        category=KnowledgeCategory.ARTISTIC_MODEL,
        description="Визуальные карточки персонажей — художественная модель (план Visual Intelligence, 19.07.2026 (агентская визуальная модель))",
        is_canon=False,
        requires_author_review=True,
        source_path="core/CORE/visual/VISUAL_KNOWLEDGE/CHARACTER_VISUALS.json",
    ),
    KnowledgeFileClassification(
        filename="ATMOSPHERES.json",
        category=KnowledgeCategory.ARTISTIC_MODEL,
        description="Атмосферы — художественная модель (план Visual Intelligence, 19.07.2026 (агентская визуальная модель))",
        is_canon=False,
        requires_author_review=True,
        source_path="core/CORE/visual/VISUAL_KNOWLEDGE/ATMOSPHERES.json",
    ),
    KnowledgeFileClassification(
        filename="VISUAL_SYMBOLS.json",
        category=KnowledgeCategory.ARTISTIC_MODEL,
        description="Визуальные символы — художественная модель (план Visual Intelligence, 19.07.2026 (агентская визуальная модель))",
        is_canon=False,
        requires_author_review=True,
        source_path="core/CORE/visual/VISUAL_KNOWLEDGE/VISUAL_SYMBOLS.json",
    ),
    KnowledgeFileClassification(
        filename="CAMERA_LIBRARY.json",
        category=KnowledgeCategory.ARTISTIC_MODEL,
        description="Библиотека камер — художественная модель (план Visual Intelligence, 19.07.2026 (агентская визуальная модель))",
        is_canon=False,
        requires_author_review=True,
        source_path="core/CORE/visual/VISUAL_KNOWLEDGE/CAMERA_LIBRARY.json",
    ),
    KnowledgeFileClassification(
        filename="STYLE_LIBRARY.json",
        category=KnowledgeCategory.ARTISTIC_MODEL,
        description="Библиотека стилей — художественная модель (план Visual Intelligence, 19.07.2026 (агентская визуальная модель))",
        is_canon=False,
        requires_author_review=True,
        source_path="core/CORE/visual/VISUAL_KNOWLEDGE/STYLE_LIBRARY.json",
    ),
    KnowledgeFileClassification(
        filename="SHOT_LIBRARY.json",
        category=KnowledgeCategory.ARTISTIC_MODEL,
        description="Библиотека планов — художественная модель (план Visual Intelligence, 19.07.2026 (агентская визуальная модель))",
        is_canon=False,
        requires_author_review=True,
        source_path="core/CORE/visual/VISUAL_KNOWLEDGE/SHOT_LIBRARY.json",
    ),
    KnowledgeFileClassification(
        filename="VIDEO_RULES.json",
        category=KnowledgeCategory.ARTISTIC_MODEL,
        description="Правила видео — художественная модель (план Visual Intelligence, 19.07.2026 (агентская визуальная модель))",
        is_canon=False,
        requires_author_review=True,
        source_path="core/CORE/visual/VISUAL_KNOWLEDGE/VIDEO_RULES.json",
    ),

    KnowledgeFileClassification(
        filename="screenplay_extracts.json",
        category=KnowledgeCategory.DERIVED,
        description="Извлечения из сценария — производное",
        is_canon=False,
    ),

    # ── ANCHOR ───────────────────────────────────────────────────────────
    KnowledgeFileClassification(
        filename="ANCHOR_QUOTES.json",
        category=KnowledgeCategory.AUTHOR_CANON,
        description="Якорные цитаты — прямой канон",
        is_canon=True,
    ),
    KnowledgeFileClassification(
        filename="quotes.json",
        category=KnowledgeCategory.AUTHOR_CANON,
        description="Цитаты из книги — канон",
        is_canon=True,
    ),

    # ── MISC ─────────────────────────────────────────────────────────────
    KnowledgeFileClassification(
        filename="QUESTIONS_FOR_READER.json",
        category=KnowledgeCategory.DERIVED,
        description="Вопросы для читателей — производное",
        is_canon=False,
    ),
    KnowledgeFileClassification(
        filename="PATTERNS.json",
        category=KnowledgeCategory.HYPOTHESIS,
        description="Паттерны — LLM-анализ",
        is_canon=False,
        requires_author_review=True,
    ),
    KnowledgeFileClassification(
        filename="enriched_catalog.json",
        category=KnowledgeCategory.DERIVED,
        description="Enriched catalog — системный индекс",
        is_canon=False,
    ),
    KnowledgeFileClassification(
        filename="enriched_chunks.json",
        category=KnowledgeCategory.DERIVED,
        description="Enriched chunks — RAG индекс",
        is_canon=False,
    ),
    KnowledgeFileClassification(
        filename="deep_daily_life.json",
        category=KnowledgeCategory.HYPOTHESIS,
        description="Повседневная жизнь — гипотезы",
        is_canon=False,
        requires_author_review=True,
    ),
    KnowledgeFileClassification(
        filename="SPIRITUAL_TRANSFORMATION.json",
        category=KnowledgeCategory.HYPOTHESIS,
        description="Духовная трансформация — гипотезы",
        is_canon=False,
        requires_author_review=True,
    ),
    KnowledgeFileClassification(
        filename="ARCHETYPES_EXPANDED.json",
        category=KnowledgeCategory.HYPOTHESIS,
        description="Расширенные архетипы — LLM-анализ",
        is_canon=False,
        requires_author_review=True,
    ),
    # .md narrative files
    KnowledgeFileClassification(
        filename="narrative_rumors.md",
        category=KnowledgeCategory.HYPOTHESIS,
        description="Нарративные слухи — гипотезы",
        is_canon=False,
        requires_author_review=True,
    ),
    KnowledgeFileClassification(
        filename="narrative_search.md",
        category=KnowledgeCategory.HYPOTHESIS,
        description="Нарративный поиск — гипотезы",
        is_canon=False,
        requires_author_review=True,
    ),
    KnowledgeFileClassification(
        filename="narrative_soldier.md",
        category=KnowledgeCategory.HYPOTHESIS,
        description="Нарратив солдат — гипотезы",
        is_canon=False,
        requires_author_review=True,
    ),
]


def get_classification(filename: str) -> Optional[KnowledgeFileClassification]:
    """Получить классификацию для файла."""
    for fc in KNOWLEDGE_CLASSIFICATION:
        if fc.filename == filename:
            return fc
    return None


def is_canon_file(filename: str) -> bool:
    """Является ли файл авторским каноном."""
    fc = get_classification(filename)
    return fc is not None and fc.is_canon


def requires_author_review(filename: str) -> bool:
    """Требует ли файл проверки автором."""
    fc = get_classification(filename)
    return fc is not None and fc.requires_author_review


def get_all_canon_files() -> list[str]:
    """Все файлы, классифицированные как канон."""
    return [fc.filename for fc in KNOWLEDGE_CLASSIFICATION if fc.is_canon]


def get_all_hypothesis_files() -> list[str]:
    """Все файлы, классифицированные как гипотезы."""
    return [fc.filename for fc in KNOWLEDGE_CLASSIFICATION if fc.category == KnowledgeCategory.HYPOTHESIS]


def classify_all() -> dict[str, str]:
    """Полная классификация всех файлов: filename → category."""
    return {fc.filename: fc.category.value for fc in KNOWLEDGE_CLASSIFICATION}
