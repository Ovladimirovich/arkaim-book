"""Q1: индекс кандидатов LLM для очереди проверки.

Сканирует ``core/KNOWLEDGE/*.json`` и возвращает только записи, помеченные как
кандидаты (``requires_author_review`` или явный статус проверки). Записи без
провенанса в очередь не попадают — это проверенное знание, а не предложение.

Формат файлов не меняется: поддерживаются и массив записей, и обёртка
``{"items": [...]}``; индекс лишь читает.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from ..provenance_gate import file_is_unverified, record_is_unverified

log = logging.getLogger("hermes.knowledge_expansion.review.candidates")

KNOWLEDGE_DIR = Path(__file__).resolve().parents[3] / "core" / "KNOWLEDGE"

#: Контейнеры записей в KNOWLEDGE-файлах (как у загрузчиков и гейтов).
ENTRY_CONTAINERS: tuple[str, ...] = (
    "items",
    "themes",
    "symbols",
    "archetypes",
    "confirmations",
    "traditions",
    "connections",
)

STATUS_PENDING = "PENDING_REVIEW"
STATUS_APPROVED = "APPROVED"
STATUS_REJECTED = "REJECTED"

#: Статусы, которые очередь знает и показывает.
KNOWN_STATUSES = frozenset({STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED})

#: Поля провенанса, где может лежать статус (в порядке приоритета).
_METADATA_KEYS = ("_provenance_metadata", "provenance_metadata")

_PREVIEW_LIMIT = 240


def _normalize(value: Any) -> str:
    return " ".join(str(value or "").split())


def _status(value: Any) -> str:
    return str(value or "").strip().upper()


def review_metadata(record: Mapping[str, Any]) -> dict[str, Any]:
    """Сводный блок провенанса записи (верхний уровень + ``metadata``).

    Верхний уровень имеет приоритет: стор кладёт провенанс и в запись, и в её
    ``metadata``; после решения оба места обновляются согласованно.
    """
    merged: dict[str, Any] = {}
    nested = record.get("metadata")
    if isinstance(nested, Mapping):
        for key in _METADATA_KEYS:
            block = nested.get(key)
            if isinstance(block, Mapping):
                merged.update(block)
    for key in _METADATA_KEYS:
        block = record.get(key)
        if isinstance(block, Mapping):
            merged.update(block)
    return merged


def _explicit_status(record: Mapping[str, Any]) -> str:
    return _status(review_metadata(record).get("status"))


def _is_candidate(record: Mapping[str, Any], document: Any) -> bool:
    """Показывать ли запись в очереди.

    Кандидат — запись с явным статусом проверки либо с флагом
    ``requires_author_review``; file-level флаг тоже делает записи кандидатами.
    """
    if _explicit_status(record) in KNOWN_STATUSES:
        return True
    return record_is_unverified(record) or file_is_unverified(document)


def _topic(record: Mapping[str, Any]) -> str:
    for key in ("topic", "name", "title", "category"):
        value = _normalize(record.get(key))
        if value:
            return value
    return ""


def _preview(record: Mapping[str, Any]) -> str:
    layers = record.get("layers")
    if isinstance(layers, Mapping):
        for key in ("literal", "metaphorical", "cosmic"):
            value = _normalize(layers.get(key))
            if value:
                return value[:_PREVIEW_LIMIT]
    for key in ("content", "description", "text", "core_teaching"):
        value = _normalize(record.get(key))
        if value:
            return value[:_PREVIEW_LIMIT]
    return ""


def candidate_id_for(file_name: str, record: Mapping[str, Any]) -> str:
    """Стабильный базовый id кандидата (не зависит от порядка записей).

    В хеш входят файл, тема, ``content`` и ``layers.literal``: у записей
    пайплайна ``content`` часто пуст, а смысл лежит в слоях.

    Если в одном файле есть полностью одинаковые записи (известный дефект
    данных — дубли сущностей), сканер добавляет к id суффикс ``-2``, ``-3``:
    иначе обе записи имели бы один id и вторую нельзя было бы проверить.
    """
    layers = record.get("layers")
    literal = _normalize(layers.get("literal")) if isinstance(layers, Mapping) else ""
    payload = "|".join(
        (file_name, _topic(record), _normalize(record.get("content")), literal)
    )
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return f"cand_{digest[:12]}"


def base_candidate_id(candidate_id: str) -> str:
    """Базовый id без суффикса дубликата (``cand_x`` из ``cand_x-2``)."""
    return re.sub(r"-\d+$", "", str(candidate_id or ""))


@dataclass(frozen=True)
class CandidateRecord:
    """Кандидат в очереди проверки."""

    candidate_id: str
    file: str
    container: str | None
    index: int
    topic: str
    status: str
    source: str
    model: str
    generated_at: str
    reviewed_by: str
    reviewed_at: str
    review_comment: str
    preview: str
    file_blocked: bool

    @property
    def locator(self) -> str:
        """Человекочитаемое место записи в файле."""
        if self.container:
            return f"{self.file}#{self.container}[{self.index}]"
        return f"{self.file}#[{self.index}]"


def _load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:  # noqa: BLE001
        log.warning("review_index_read_failed path=%s error=%s", path, exc)
        return None


def _entries(document: Any) -> Iterable[tuple[str | None, int, Mapping[str, Any]]]:
    """Записи документа: (контейнер, индекс, запись)."""
    if isinstance(document, list):
        for index, entry in enumerate(document):
            if isinstance(entry, Mapping):
                yield None, index, entry
        return
    if not isinstance(document, Mapping):
        return
    for container in ENTRY_CONTAINERS:
        entries = document.get(container)
        if not isinstance(entries, list):
            continue
        for index, entry in enumerate(entries):
            if isinstance(entry, Mapping):
                yield container, index, entry


def scan_candidates(knowledge_dir: Path | str | None = None) -> list[CandidateRecord]:
    """Собрать актуальный список кандидатов (свежий скан файлов)."""
    root = Path(knowledge_dir) if knowledge_dir else KNOWLEDGE_DIR
    records: list[CandidateRecord] = []
    if not root.is_dir():
        log.warning("review_index_dir_missing path=%s", root)
        return records

    for path in sorted(root.glob("*.json")):
        document = _load(path)
        if document is None:
            continue
        blocked = file_is_unverified(document)
        seen: dict[str, int] = {}
        for container, index, entry in _entries(document):
            if not _is_candidate(entry, document):
                continue
            meta = review_metadata(entry)
            base_id = candidate_id_for(path.name, entry)
            seen[base_id] = seen.get(base_id, 0) + 1
            occurrence = seen[base_id]
            candidate_id = base_id if occurrence == 1 else f"{base_id}-{occurrence}"
            records.append(
                CandidateRecord(
                    candidate_id=candidate_id,
                    file=path.name,
                    container=container,
                    index=index,
                    topic=_topic(entry),
                    status=_explicit_status(entry) or STATUS_PENDING,
                    source=str(meta.get("source") or ""),
                    model=str(meta.get("model") or ""),
                    generated_at=str(meta.get("generated_at") or ""),
                    reviewed_by=str(meta.get("reviewed_by") or ""),
                    reviewed_at=str(meta.get("reviewed_at") or ""),
                    review_comment=str(meta.get("review_comment") or ""),
                    preview=_preview(entry),
                    file_blocked=blocked,
                )
            )
    log.info("review_index_built files_dir=%s candidates=%d", root, len(records))
    return records


def find_candidate(
    candidate_id: str, knowledge_dir: Path | str | None = None
) -> CandidateRecord | None:
    """Найти кандидата по id (None, если запись пересобрана/удалена)."""
    for record in scan_candidates(knowledge_dir):
        if record.candidate_id == candidate_id:
            return record
    return None


def filter_candidates(
    records: Iterable[CandidateRecord],
    *,
    status: str | None = None,
    file: str | None = None,
    source: str | None = None,
    query: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[CandidateRecord]:
    """Отфильтровать и постранично выдать кандидатов."""
    wanted_status = _status(status) if status else ""
    wanted_file = _normalize(file)
    wanted_source = _normalize(source)
    needle = _normalize(query).casefold()

    selected = [
        record
        for record in records
        if (not wanted_status or record.status == wanted_status)
        and (not wanted_file or record.file == wanted_file)
        and (not wanted_source or record.source.casefold() == wanted_source.casefold())
        and (
            not needle
            or needle in record.topic.casefold()
            or needle in record.preview.casefold()
        )
    ]
    start = max(int(offset or 0), 0)
    if limit is None:
        return selected[start:]
    return selected[start : start + max(int(limit), 0)]


def candidate_stats(records: Iterable[CandidateRecord]) -> dict[str, Any]:
    """Счётчики для бейджа и экрана очереди."""
    by_status: dict[str, int] = {status: 0 for status in sorted(KNOWN_STATUSES)}
    by_file: dict[str, int] = {}
    by_source: dict[str, int] = {}
    total = 0
    for record in records:
        total += 1
        by_status[record.status] = by_status.get(record.status, 0) + 1
        by_file[record.file] = by_file.get(record.file, 0) + 1
        source = record.source or "UNKNOWN"
        by_source[source] = by_source.get(source, 0) + 1
    return {
        "total": total,
        "pending": by_status.get(STATUS_PENDING, 0),
        "by_status": by_status,
        "by_file": dict(sorted(by_file.items())),
        "by_source": dict(sorted(by_source.items())),
    }
