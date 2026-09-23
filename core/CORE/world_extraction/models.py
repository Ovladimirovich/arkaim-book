"""Модели данных для World Extraction Pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from pathlib import Path


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
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "name_ru": self.name_ru or self.name,
            "category": self.category,
            "description": self.description,
            "properties": self.properties,
            "relationships": self.relationships,
            "source": self.source,
            "confidence": self.confidence,
        }


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
        return (
            f"Мир: {self.total_items} сущностей в {self.total_categories} категориях"
        )
