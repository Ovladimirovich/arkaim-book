"""External Gate — гейт на вход нового внешнего знания (Этап 2 плана).

Контракт «Единый источник истины для внешних знаний» (ADR — см. Этап 2
в docs/ARKAIM_SEQUENTIAL_FIX_PLAN.md) фиксирует правила наследования
провенанса. Данный валидатор — гейт на вход НОВЫХ записей: он проверяет,
что внешнее/интерпретационное знание попадает в систему только с честной
маркировкой, и НИКОГДА не может быть заявлено как AUTHOR_CANON вне
первичных канонических файлов.

Правила контракта (без изменения существующих данных):
1. «Сырьё» внешних источников живет ТОЛЬКО в core/KNOWLEDGE/*.
2. «Связь с книгой» — отдельное поле book_link_status (VERIFIED | UNVERIFIED
   | REJECTS), не склеенное с самим фактом.
3. «Системная интерпретация» — только со статусом SYSTEM_INTERPRETATION и
   явной ссылкой на сырьё (source: <id in KNOWLEDGE>), никогда не CANON.
4. origin_layer ∈ {EXTERNAL_FACT, BOOK_LINK, SYSTEM_INTERPRETATION}.
5. Если origin_layer=BOOK_LINK → обязателен book_link_status (не null).

Это гейт «на вход» (validator), а не постфактум-проверка. Контракт вступает
в силу для НОВЫХ записей; существующие данные не классифицируются «в массе».
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from narrative_engine.provenance.knowledge_classification import is_canon_file
from narrative_engine.source_levels import (
    ProvenanceCategory,
    normalize_provenance_category,
)


class OriginLayer(str, Enum):
    """Слой происхождения записи (контракт Этапа 2)."""

    EXTERNAL_FACT = "EXTERNAL_FACT"
    """Внешний факт (археология, академика, традиции)."""

    BOOK_LINK = "BOOK_LINK"
    """Связь с книгой (отдельное поле со своим статусом)."""

    SYSTEM_INTERPRETATION = "SYSTEM_INTERPRETATION"
    """Интерпретация системы (нужна явная ссылка на сырьё)."""


# Допустимые значения статуса связи с книгой.
BOOK_LINK_STATUSES = frozenset({"VERIFIED", "UNVERIFIED", "REJECTS"})


@dataclass(frozen=True)
class GateIssue:
    """Одна проблема, найденная гейтом."""

    rule: str
    severity: str  # "error" | "warning"
    detail: str


@dataclass
class GateResult:
    """Результат проверки записи."""

    valid: bool
    issues: list[GateIssue] = field(default_factory=list)

    def errors(self) -> list[str]:
        return [i.detail for i in self.issues if i.severity == "error"]

    def warnings(self) -> list[str]:
        return [i.detail for i in self.issues if i.severity == "warning"]


# ── Правила гейта ───────────────────────────────────────────────────────────


def _missing_source(record: dict) -> Optional[str]:
    """source обязан быть реальной ссылкой или 'UNKNOWN', но не null/пустым."""
    source = record.get("source")
    if source is None or (isinstance(source, str) and not source.strip()):
        return "поле 'source' обязательно: реальная ссылка (напр. 'ESOTERIC_CONNECTIONS.json#traditions[0]') или 'UNKNOWN', но не null/пустое"
    return None


def _bad_origin_layer(record: dict) -> Optional[str]:
    """origin_layer должен быть одним из трёх допустимых значений."""
    raw = record.get("origin_layer")
    if raw is None:
        return "поле 'origin_layer' обязательно: EXTERNAL_FACT | BOOK_LINK | SYSTEM_INTERPRETATION"
    try:
        OriginLayer(str(raw).strip().upper())
        return None
    except ValueError:
        return f"поле 'origin_layer' имеет недопустимое значение '{raw}': допустимы EXTERNAL_FACT | BOOK_LINK | SYSTEM_INTERPRETATION"


def _book_link_status_required(record: dict) -> Optional[str]:
    """Если origin_layer=BOOK_LINK → book_link_status обязателен (не null)."""
    raw = record.get("origin_layer")
    if raw is None:
        return None
    try:
        layer = OriginLayer(str(raw).strip().upper())
    except ValueError:
        return None
    if layer != OriginLayer.BOOK_LINK:
        return None
    status = record.get("book_link_status")
    if status is None or (isinstance(status, str) and not status.strip()):
        return "запись с origin_layer=BOOK_LINK обязана иметь поле 'book_link_status' (VERIFIED | UNVERIFIED | REJECTS), не null"
    if str(status).strip().upper() not in BOOK_LINK_STATUSES:
        return (
            f"поле 'book_link_status' имеет недопустимое значение '{status}': "
            f"допустимы {', '.join(sorted(BOOK_LINK_STATUSES))}"
        )
    return None


def _rejects_false_canon(record: dict, target_file: str) -> Optional[str]:
    """Факт-чек гейт (закрывает дефект типа B16): запись НЕ из первичного
    канонического файла не может претендовать на AUTHOR_CANON.

    «Непервоначальная Традиция (Элиаде)» с key_text, указывающим на тексты
    Генона, а не Элиаде, — пример: это производная/внешняя запись, заявка
    на канон внутри нес-канонического файла должна быть отклонена гейтом.
    """
    raw = record.get("provenance_category")
    if raw is None:
        # Нет явной категории — не «претендует» на канон, но и не подтверждено.
        return None
    category = normalize_provenance_category(raw)
    claims_canon = category in (ProvenanceCategory.AUTHOR_CANON,)
    if not claims_canon:
        return None
    # Запись претендует на канон → она обязана жить в первичном каноническом файле.
    if is_canon_file(target_file):
        return None
    return (
        f"запись претендует на AUTHOR_CANON, но файл '{target_file}' не является "
        "первичным каноническим (BOOK_DOCUMENT/SYNOPSIS_DOCUMENT/AUTHOR_INTENT) — "
        "заявка на канон отклонена (факт-чек гейт, тип B16)"
    )


def _unknown_canon_mask(record: dict) -> Optional[str]:
    """Предупреждение: поле provenance_category='UNKNOWN' маскирует происхождение.
    Не блокирует, но требует внимания (честный UNKNOWN лучше, чем молчание)."""
    raw = record.get("provenance_category")
    if raw is None:
        return None
    category = normalize_provenance_category(raw)
    if category == ProvenanceCategory.UNKNOWN:
        return "поле 'provenance_category' = UNKNOWN: честно помечено, но происхождение не определено — желательно указать источник"
    return None


# ── Публичный API ───────────────────────────────────────────────────────────


def validate_external_record(
    record: dict,
    target_file: str = "",
) -> GateResult:
    """Проверить НОВУЮ внешнюю/интерпретационную запись на входе.

    Args:
        record: запись, которую собираются добавить (dict полей).
        target_file: имя файла KNOWLEDGE, в который запись добавляется
            ('' если неизвестно — тогда канон-проверка считается
            «по умолчанию непрошедшей» для AUTHOR_CANON-заявок, т.к. канон
            возможен только в первичных файлах).

    Returns:
        GateResult: valid=True — запись допустима; issues — найденные проблемы.
    """
    issues: list[GateIssue] = []

    if target_file and not isinstance(target_file, str):
        raise TypeError("target_file должен быть строкой (имя файла KNOWLEDGE)")

    for check in (_missing_source, _bad_origin_layer, _book_link_status_required):
        problem = check(record)
        if problem:
            issues.append(
                GateIssue(
                    rule=check.__name__,
                    severity="error",
                    detail=problem,
                )
            )

    canonical_problem = _rejects_false_canon(record, target_file)
    if canonical_problem:
        issues.append(
            GateIssue(
                rule="_rejects_false_canon",
                severity="error",
                detail=canonical_problem,
            )
        )

    unknown_warning = _unknown_canon_mask(record)
    if unknown_warning:
        issues.append(
            GateIssue(
                rule="_unknown_canon_mask",
                severity="warning",
                detail=unknown_warning,
            )
        )

    valid = not any(i.severity == "error" for i in issues)
    return GateResult(valid=valid, issues=issues)


def check_external_record(
    record: dict,
    target_file: str = "",
) -> bool:
    """Удобный bool-интерфейс: True — запись прошла гейт."""
    return validate_external_record(record, target_file).valid
