"""Гейт провенанса для знаний, которые читают потребители.

Правило проекта: LLM-кандидат — предложение, а не знание. Запись с
``requires_author_review=true`` (или незакрытым статусом ``PENDING_REVIEW``)
не должна попадать в ответы Pulse, RAG-поиск и карточки знаний до решения
автора. Маркировка ставится ``DeepAnalyzer.LLM_PROVENANCE`` и сохраняется
``KnowledgeStore`` на уровне записи и её ``metadata``.

Гейт намеренно «пропускает всё, что не помечено»: существующие проверенные
записи без полей провенанса читаются как раньше.
"""

from __future__ import annotations

from typing import Any, Mapping

#: Статусы, означающие, что автор уже принял запись. Явное одобрение сильнее
#: оставшегося флага requires_author_review.
APPROVED_STATUSES = frozenset(
    {
        "APPROVED",
        "ACCEPTED",
        "ACCEPTED_BY_OWNER",
        "OWNER_APPROVED",
        "CANON",
    }
)

#: Незакрытые статусы: запись ещё не проверена автором.
UNVERIFIED_STATUSES = frozenset(
    {
        "PENDING_REVIEW",
        "REJECTED",
        "DRAFT",
        "PROPOSED",
    }
)

_METADATA_KEYS = ("_provenance_metadata", "provenance_metadata")


def _status(value: Any) -> str:
    return str(value or "").strip().upper()


def _flag(value: Any) -> bool:
    """Флаг «требует проверки»: bool True либо строковое true/yes/1."""
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1"}
    return False


def _metadata_blocks(metadata: Any) -> bool:
    """Считать ли блок провенанса непроверенным кандидатом."""
    if not isinstance(metadata, Mapping):
        return False
    status = _status(metadata.get("status"))
    if status in APPROVED_STATUSES:
        return False
    if _flag(metadata.get("requires_author_review")):
        return True
    return status in UNVERIFIED_STATUSES


def record_is_unverified(record: Any) -> bool:
    """Запись знания — непроверенный кандидат?

    Проверяются все места, куда пайплайн и стор кладут провенанс:
    сама запись, её ``metadata`` и плоский флаг ``requires_author_review``.
    """
    if not isinstance(record, Mapping):
        return False

    for key in _METADATA_KEYS:
        if _metadata_blocks(record.get(key)):
            return True

    if (
        _flag(record.get("requires_author_review"))
        and _status(record.get("status")) not in APPROVED_STATUSES
    ):
        return True

    nested = record.get("metadata")
    if isinstance(nested, Mapping):
        for key in _METADATA_KEYS:
            if _metadata_blocks(nested.get(key)):
                return True

    return False


def file_is_unverified(document: Any) -> bool:
    """Весь файл знаний помечен как непроверенный (file-level metadata)."""
    if not isinstance(document, Mapping):
        return False
    return any(_metadata_blocks(document.get(key)) for key in _METADATA_KEYS)


def item_is_unverified(item: Any, document: Any = None) -> bool:
    """Запись непроверена сама по себе или потому что непроверен файл."""
    return record_is_unverified(item) or file_is_unverified(document)
