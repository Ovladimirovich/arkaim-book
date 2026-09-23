"""
Models — 데이터 모델ы для Knowledge Expansion Pipeline.
"""
from dataclasses import dataclass, field
from typing import Any, Optional
from pathlib import Path


@dataclass
class RawKnowledge:
    """Сырые знания, извлечённые из источника."""
    source: str                      # Источник (файл, URL, текст)
    topic: str                       # Тема
    content: str                     # Содержание
    metadata: dict = field(default_factory=dict)  # Доп. данные
    confidence: float = 1.0          # Уверенность (0-1)


@dataclass
class EnrichedKnowledge:
    """Обогащённые знания после LLM-анализа."""
    source: str
    topic: str
    content: str
    layers: dict = field(default_factory=dict)  # Буквальный, метафорический, космический
    cross_references: list[str] = field(default_factory=list)  # Ссылки на другие темы
    patterns: list[str] = field(default_factory=list)  # Обнаруженные паттерны
    connections: list[dict] = field(default_factory=list)  # Связи с другими знаниями
    metadata: dict = field(default_factory=dict)
    confidence: float = 1.0


@dataclass
class LinkedKnowledge:
    """Знания, связанные с существующим Knowledge Graph."""
    source: str
    topic: str
    content: str
    layers: dict = field(default_factory=dict)
    cross_references: list[str] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)
    connections: list[dict] = field(default_factory=list)
    graph_links: list[dict] = field(default_factory=list)  # Связи с KG
    metadata: dict = field(default_factory=dict)
    confidence: float = 1.0


@dataclass
class ValidatedKnowledge:
    """Валидированные знания, готовые к сохранению."""
    source: str
    topic: str
    content: str
    layers: dict = field(default_factory=dict)
    cross_references: list[str] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)
    connections: list[dict] = field(default_factory=list)
    graph_links: list[dict] = field(default_factory=list)
    validation_score: float = 1.0   # Оценка качества (0-1)
    duplicates_found: list[str] = field(default_factory=list)  # Найденные дубли
    metadata: dict = field(default_factory=dict)
    confidence: float = 1.0


@dataclass
class EnrichmentModule:
    """Контракт модуля обогащения."""
    name: str                          # "philosophy_deep"
    description: str                   # "Глубокий анализ философии"
    source_files: list[Path]           # Откуда берём данные
    output_file: Path                  # Куда сохраняем
    enricher_class: type               # Класс обогащения
    dependencies: list[str] = field(default_factory=list)  # Какие модули нужны beforehand


@dataclass
class SaveResult:
    """Результат сохранения."""
    success: bool
    items_saved: int
    items_skipped: int  # Дубли
    output_path: str
    graph_updates: int  # Обновлений в графе
