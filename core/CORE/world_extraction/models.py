"""Модели данных для World Extraction Pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Честная метка «системная интерпретация» для производных записей
# (план устранения разрывов, Этап 3): производные от KNOWLEDGE не могут
# претендовать на AUTHOR_CANON, но и не должны быть «UNKNOWN».
SYSTEM_INTERPRETATION = "SYSTEM_INTERPRETATION"
DERIVED_CATEGORY = "DERIVED"


@dataclass
class WorldKnowledge:
    """Единица знания о мире."""

    id: str
    name: str
    name_ru: str = ""
    category: str = ""  # geography, civilization, architecture, etc.
    description: str = ""
    properties: dict[str, Any] = field(default_factory=dict)
    relationships: list[str] = field(default_factory=list)  # IDs связанных сущностей
    source: str = ""  # откуда извлечено
    confidence: float = 1.0  # 0.0 - 1.0
    provenance_category: str = DERIVED_CATEGORY  # честная категория, не CANON
    provenance_notes: str = ""
    derived_from: str = ""  # DERIVED_FROM: разрешаемая ссылка на KNOWLEDGE-источник
    source_level: str = SYSTEM_INTERPRETATION
    book_link_status: str = (
        ""  # связь с книгой: VERIFIED | UNVERIFIED | REJECTS ("" если неприменимо)
    )

    def to_dict(self) -> dict:
        """Сериализация записи WORLD_MODEL (схема: id/name/... + provenance).

        ``derived_from``/``book_link_status`` добавляются только если заданы,
        чтобы не менять схему записей, для которых производность не применима.
        """
        data = {
            "id": self.id,
            "name": self.name,
            "name_ru": self.name_ru or self.name,
            "category": self.category,
            "description": self.description,
            "properties": self.properties,
            "relationships": self.relationships,
            "source": self.source,
            "confidence": self.confidence,
            "provenance_category": self.provenance_category,
            "provenance_notes": self.provenance_notes,
            "source_level": self.source_level,
        }
        if self.derived_from:
            data["derived_from"] = self.derived_from
        # НЕ пишем book_link_status в WORLD_MODEL-файлы: статус связи с книгой
        # живёт в KNOWLEDGE-источнике (ESOTERIC_CONNECTIONS.json#traditions[*].provenance),
        # чтобы не размножать копии статуса по проекциям.
        return data


@dataclass
class ExtractionResult:
    """Результат извлечения для одной категории."""

    category: str
    items: list[WorldKnowledge] = field(default_factory=list)
    source_files: list[str] = field(default_factory=list)
    success: bool = True
    error: str = ""
    items_count: int = 0

    def __post_init__(self):
        self.items_count = len(self.items)


@dataclass
class WorldModelManifest:
    """Манифест всех извлечённых данных мира."""

    categories: dict[str, ExtractionResult] = field(default_factory=dict)
    total_items: int = 0
    total_categories: int = 0

    def add_result(self, result: ExtractionResult):
        self.categories[result.category] = result
        self.total_items += result.items_count
        self.total_categories = len(self.categories)

    def summary(self) -> str:
        return f"Мир: {self.total_items} сущностей в {self.total_categories} категориях"
