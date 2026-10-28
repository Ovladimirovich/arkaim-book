"""Гейт провенанса на входе world_extraction (Этап 6e).

Единый механизм — предикаты Этапа 6d из ``knowledge_expansion.provenance_gate``.
Здесь только адаптация под мир: модули извлечения читают KNOWLEDGE-файлы
разных форматов (bare-list, ``{"items": [...]}``, именованные контейнеры) и
кладут текст в ``WorldKnowledge`` без ссылки на исходную запись. Поэтому
фильтр применяется на границе пайплайна — после экстрактора, но до сохранения.

Правило:
  * file-level ``requires_author_review`` → весь файл-источник карантин;
  * запись с ``requires_author_review``/незакрытым статусом → карантин по теме;
  * одобренная запись (``APPROVED`` и т.п.) проходит как раньше;
  * записи без провенанса проходят как раньше.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from knowledge_expansion.provenance_gate import file_is_unverified, item_is_unverified

log = logging.getLogger("hermes.world_extraction.provenance")

#: Контейнеры записей, которые встречаются в KNOWLEDGE-файлах.
ENTRY_CONTAINERS: tuple[str, ...] = (
    "items",
    "themes",
    "symbols",
    "archetypes",
    "confirmations",
)


def normalize(value: Any) -> str:
    """Нормализованное имя для сопоставления темы с сущностью мира."""
    return " ".join(str(value or "").split()).casefold()


def _source_name(path: Any) -> str:
    return Path(str(path or "")).name


def iter_records(document: Any) -> Iterable[dict]:
    """Записи знания из документа: список или именованные контейнеры.

    Свободные словари (``deep_daily_life.json``, ``civilization_profiles.json``)
    не разбираются: у их полей нет record-level провенанса, а тема не является
    отдельной записью.
    """
    if isinstance(document, list):
        for item in document:
            if isinstance(item, dict):
                yield item
        return
    if not isinstance(document, dict):
        return
    for key in ENTRY_CONTAINERS:
        entries = document.get(key)
        if isinstance(entries, list):
            for item in entries:
                if isinstance(item, dict):
                    yield item


def _record_topic(record: dict) -> str:
    for key in ("topic", "name", "category"):
        value = str(record.get(key) or "").strip()
        if value:
            return value
    return ""


def _load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:  # noqa: BLE001
        log.warning("provenance_source_read_failed path=%s error=%s", path, exc)
        return None


@dataclass
class CandidateIndex:
    """Что нельзя переносить в мир: файлы целиком и темы внутри файлов.

    Темы привязаны к файлу-источнику: одноимённая проверенная сущность из
    другого файла не должна отсекаться.
    """

    blocked_files: set[str] = field(default_factory=set)
    topics_by_file: dict[str, set[str]] = field(default_factory=dict)
    inspected: int = 0


def build_candidate_index(source_files: Iterable[Any]) -> CandidateIndex:
    """Собрать индекс кандидатов из файлов-источников экстрактора."""
    index = CandidateIndex()
    for raw_path in source_files:
        path = Path(str(raw_path))
        if not path.is_file():
            continue
        document = _load(path)
        if document is None:
            continue
        index.inspected += 1
        if file_is_unverified(document):
            index.blocked_files.add(path.name)
            log.warning("world_source_quarantined file=%s", path.name)
            continue
        for record in iter_records(document):
            if item_is_unverified(record):
                topic = _record_topic(record)
                if topic:
                    bucket = index.topics_by_file.setdefault(path.name, set())
                    bucket.add(normalize(topic))
    return index


def is_blocked(item: Any, index: CandidateIndex) -> bool:
    """Попадает ли готовая сущность мира под карантин кандидатов."""
    source = _source_name(getattr(item, "source", ""))
    if source in index.blocked_files:
        return True
    name = normalize(getattr(item, "name", "")) or normalize(
        getattr(item, "name_ru", "")
    )
    return bool(name) and name in index.topics_by_file.get(source, set())


def filter_extraction_result(result: Any) -> int:
    """Убрать из результата экстрактора сущности из непроверенных источников.

    Returns: сколько сущностей отсечено.
    """
    index = build_candidate_index(getattr(result, "source_files", []) or [])
    if not index.blocked_files and not index.topics_by_file:
        return 0

    kept = [item for item in result.items if not is_blocked(item, index)]
    dropped = len(result.items) - len(kept)
    if dropped:
        result.items = kept
        result.items_count = len(kept)
        log.info(
            "world_candidates_filtered sources=%d blocked_files=%d topic_files=%d "
            "dropped=%d",
            index.inspected,
            len(index.blocked_files),
            len(index.topics_by_file),
            dropped,
        )
    return dropped
