"""SourceHierarchy — иерархия авторских источников с приоритетами.

M1: определяет, какие источники являются AUTHOR_CANON,
а какие — вспомогательными.

Иерархия:
  BOOK (КНИГА.md)          → PRIMARY AUTHOR CANON      (weight 1.0)
  SCRIPT (Сценарий_Full.md) → SECONDARY AUTHOR SOURCE   (weight 0.9)
  AUTHOR_NOTES              → AUTHOR SUPPLEMENT         (weight 0.8)

При конфликте: BOOK > SCRIPT > NOTES.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from narrative_engine.source_levels import ProvenanceCategory, SourceLevel


class SourceTier(str, Enum):
    """Уровень авторского источника."""

    PRIMARY_CANON = "PRIMARY_CANON"
    """Первичный канон — текст книги."""

    SECONDARY_AUTHOR = "SECONDARY_AUTHOR"
    """Вторичный авторский источник — сценарий, синопсис."""

    AUTHOR_SUPPLEMENT = "AUTHOR_SUPPLEMENT"
    """Авторские дополнения — заметки, интервью, аннотации."""

    EXTERNAL = "EXTERNAL"
    """Внешние источники — археология, академические работы."""

    SYSTEM_DERIVED = "SYSTEM_DERIVED"
    """Производные системы — индексы, профили, Обогащения."""


@dataclass(frozen=True)
class SourceEntry:
    """Запись об источнике."""

    path: str
    tier: SourceTier
    weight: float
    description: str
    is_canon: bool = False
    is_primary: bool = False


class SourceHierarchy:
    """Иерархия авторских источников.

    Хранит все источники проекта и их приоритеты.
    Методы позволяют определить, является ли источник каноном,
    и какой приоритет имеет конфликт между источниками.
    """

    # ── Определение источников ─────────────────────────────────────────

    SOURCES: list[SourceEntry] = [
        SourceEntry(
            path="SOURCE_OF_TRUTH/BOOK/КНИГА.md",
            tier=SourceTier.PRIMARY_CANON,
            weight=1.0,
            description="Первичный текст книги «Наследие Аркаима»",
            is_canon=True,
            is_primary=True,
        ),
        SourceEntry(
            path="SOURCE_OF_TRUTH/SYNOPSIS/Наследие_Аркаима_Сценарий_Full.md",
            tier=SourceTier.SECONDARY_AUTHOR,
            weight=0.9,
            description="Сценарий/синопсис — вторичный авторский источник",
            is_canon=False,
            is_primary=False,
        ),
        SourceEntry(
            path="SOURCE_OF_TRUTH/AUTHOR_NOTES/Аннотация.pdf",
            tier=SourceTier.AUTHOR_SUPPLEMENT,
            weight=0.8,
            description="Авторская аннотация",
            is_canon=False,
            is_primary=False,
        ),
        SourceEntry(
            path="SOURCE_OF_TRUTH/AUTHOR_NOTES/Письмо.pdf",
            tier=SourceTier.AUTHOR_SUPPLEMENT,
            weight=0.8,
            description="Письмо автора",
            is_canon=False,
            is_primary=False,
        ),
        # External sources — populated dynamically
    ]

    # ── Lookup ───────────────────────────────────────────────────────────

    @classmethod
    def get_source(cls, path: str) -> Optional[SourceEntry]:
        """Найти источник по пути."""
        for entry in cls.SOURCES:
            if entry.path == path:
                return entry
        return None

    @classmethod
    def get_canon_sources(cls) -> list[SourceEntry]:
        """Все источники, классифицированные как канон."""
        return [e for e in cls.SOURCES if e.is_canon]

    @classmethod
    def get_primary_canon(cls) -> Optional[SourceEntry]:
        """Первичный канон (книга)."""
        for entry in cls.SOURCES:
            if entry.is_primary:
                return entry
        return None

    @classmethod
    def resolve_conflict(cls, sources: list[SourceEntry]) -> Optional[SourceEntry]:
        """Определить приоритетный источник при конфликте.

        Возвращает источник с максимальным weight.
        """
        if not sources:
            return None
        return max(sources, key=lambda s: s.weight)

    @classmethod
    def classify_source(cls, path: str) -> tuple[SourceEntry | None, ProvenanceCategory]:
        """Классифицировать источник: возвращает (entry, category).

        Если путь не найден в иерархии — возвращает UNKNOWN.
        """
        entry = cls.get_source(path)
        if entry is None:
            return None, ProvenanceCategory.UNKNOWN

        if entry.tier == SourceTier.PRIMARY_CANON:
            return entry, ProvenanceCategory.AUTHOR_CANON
        elif entry.tier == SourceTier.SECONDARY_AUTHOR:
            return entry, ProvenanceCategory.AUTHOR_CANON  # secondary canon
        elif entry.tier == SourceTier.AUTHOR_SUPPLEMENT:
            return entry, ProvenanceCategory.DERIVED
        elif entry.tier == SourceTier.EXTERNAL:
            return entry, ProvenanceCategory.EXTERNAL_SOURCE
        elif entry.tier == SourceTier.SYSTEM_DERIVED:
            return entry, ProvenanceCategory.DERIVED

        return entry, ProvenanceCategory.UNKNOWN

    @classmethod
    def is_canon_source(cls, path: str) -> bool:
        """Является ли путь авторским каноном."""
        entry = cls.get_source(path)
        if entry is None:
            return False
        return entry.is_canon or entry.tier in (
            SourceTier.PRIMARY_CANON,
            SourceTier.SECONDARY_AUTHOR,
        )

    @classmethod
    def list_all(cls) -> list[SourceEntry]:
        """Все источники."""
        return list(cls.SOURCES)
