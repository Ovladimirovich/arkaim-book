"""Production-производители M5/M6/M7 — H2-B (GO-4).

Детерминированные производители: одни и те же данные дают одни и те же
записи. Ничего не выдумывается, ничего не мутируется.

  * M5 — конфликты: одно и то же описываемое поле, разные источники,
    разные значения. Конфликт фиксируется как данные (UNRESOLVED),
    ни одна претензия не переписывается.
  * M6 — рассуждения: агрегация ≥2 претензий с evidence по одному полю.
    Категория результата — только DERIVED/RECONSTRUCTION (HYPOTHESIS
    остаётся HYPOTHESIS), статус выводится самим ``DeterministicReasoner``.
  * M7 — предложения исправления: из finding'а M10. Предложение всегда
    PENDING: решение принимает человек.

Единственная граница мутации WorldModel — менеджер подтверждения M10.
Эти производители WorldModel не трогают.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from knowledge.reasoning import DeterministicReasoner
from narrative_engine.source_levels import ProvenanceCategory
from schemas.conflict import ConflictRecord, ConflictType
from schemas.correction import CorrectionRecord
from schemas.reasoning import ReasoningInput

#: Категории, которые не могут быть повышены (M1 / M12).
NON_PROMOTABLE = {ProvenanceCategory.HYPOTHESIS}


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _stable_id(prefix: str, *parts: str) -> str:
    raw = "|".join(parts)
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:12]}"


def _normalize(text: str) -> str:
    return " ".join(str(text or "").casefold().split())


def topic_key(source_ref: str) -> str:
    """Ключ описываемого поля по ``source_ref``.

    ``world_model:<entity>:facts.type`` → ``facts.type``
    ``ARCHAEOLOGY.json:<site>:facts.type`` → ``facts.type``
    ``book:<chunk>`` → ``book:<chunk>``
    """
    ref = str(source_ref or "")
    if ":" not in ref:
        return ref
    parts = ref.split(":")
    if len(parts) >= 3 and parts[0] in {
        "world_model",
        "ARCHAEOLOGY.json",
        "ARCHAEOLOGY_DEEP.json",
    }:
        return ":".join(parts[2:])
    if len(parts) >= 3 and parts[0] == "screenplay":
        return ":".join(parts[2:])
    return ref


def _iter_card_claims(card: dict[str, Any]):
    """Все claim'ы карточки: (source_name, claim_dict, provenance_dict)."""
    for source in card.get("sources", []) or []:
        if not isinstance(source, dict):
            continue
        source_name = str(source.get("source_name", ""))
        for claim in source.get("claims", []) or []:
            if not isinstance(claim, dict):
                continue
            provenance = (
                claim.get("provenance")
                if isinstance(claim.get("provenance"), dict)
                else {}
            )
            yield source_name, claim, provenance


def _claim_identity(claim: dict[str, Any], provenance: dict[str, Any]) -> str:
    """Идентификатор претензии: из карточки либо детерминированный."""
    claim_id = str(claim.get("claim_id") or "").strip()
    if claim_id:
        return claim_id
    from narrative_engine.provenance.claim import CanonClaim

    source_ref = str(claim.get("source_ref") or "")
    text = str(claim.get("text") or "")
    if source_ref.startswith("book:") and claim.get("chunk_id"):
        return CanonClaim.make_id(
            text, source_id="book", location=f"chunk:{claim['chunk_id']}"
        )
    category = str(provenance.get("category") or "UNKNOWN")
    return CanonClaim.make_id(
        text, source_id=category.lower(), location=source_ref or "unknown"
    )


# ── M5: конфликты ────────────────────────────────────────────────────────


def detect_conflicts(entity_id: str, card: dict[str, Any]) -> list[ConflictRecord]:
    """Найти конкурирующие утверждения об одной сущности.

    Два сигнала, оба — на реальных данных:

    1. **Разное поле, разные значения.** Одно и то же описываемое поле
       заявлено разными значениями из разных источников — прямое
       противоречие.
    2. **Разный авторитет.** Сущность описана и каноном (книга), и
       неподтверждённой внешней заметкой. Формально это не противоречие,
       но читатель может принять одно за другое — поэтому такое
       расхождение фиксируется как ``SOURCE_PERSPECTIVE`` и может быть
       закрыто как «разные перспективы», а не как победа одной стороны.

    Ни одна претензия не переписывается: конфликт — это запись о факте
    расхождения.
    """
    records: list[ConflictRecord] = []

    # ── сигнал 1: одно поле — разные значения ──
    groups: dict[str, list[tuple[str, dict, dict]]] = {}
    for source_name, claim, provenance in _iter_card_claims(card):
        key = topic_key(str(claim.get("source_ref") or ""))
        if not key:
            continue
        groups.setdefault(key, []).append((source_name, claim, provenance))

    for key, items in sorted(groups.items()):
        if len(items) < 2:
            continue
        distinct = {}
        for source_name, claim, provenance in items:
            text = _normalize(str(claim.get("text") or ""))
            category = str(provenance.get("category") or "UNKNOWN")
            distinct.setdefault((text, category), (source_name, claim, provenance))
        if len(distinct) < 2:
            continue

        variants = list(distinct.values())
        claim_ids = [
            _claim_identity(claim, provenance) for _, claim, provenance in variants
        ]
        evidence_ids: list[str] = []
        for _, claim, _ in variants:
            for evidence_id in claim.get("evidence_ids", []) or []:
                if evidence_id and evidence_id not in evidence_ids:
                    evidence_ids.append(str(evidence_id))

        explanation = f"Поле «{key}» описывается разными значениями: " + "; ".join(
            f"{provenance.get('category', 'UNKNOWN')}: {str(claim.get('text') or '')[:90]}"
            for _, claim, provenance in variants
        )
        records.append(
            ConflictRecord(
                id=_stable_id("conflict", entity_id, key, *sorted(claim_ids)),
                conflict_type=ConflictType.DIRECT_CONTRADICTION,
                subject_id=entity_id,
                claim_ids=claim_ids,
                evidence_ids=evidence_ids,
                world_entity_ids=[entity_id] if entity_id else [],
                explanation=explanation[:1000],
                created_at=_now(),
            )
        )

    # ── сигнал 2: разный авторитет описания одной сущности ──
    by_category: dict[str, list[tuple[str, dict, dict]]] = {}
    for source_name, claim, provenance in _iter_card_claims(card):
        category = str(provenance.get("category") or "UNKNOWN")
        by_category.setdefault(category, []).append((source_name, claim, provenance))

    non_canonical = {
        c: items for c, items in by_category.items() if c != "AUTHOR_CANON"
    }
    if "AUTHOR_CANON" in by_category and non_canonical:
        canonical_items = by_category["AUTHOR_CANON"]
        others = [item for items in non_canonical.values() for item in items]
        claim_ids = [
            _claim_identity(claim, provenance)
            for _, claim, provenance in (canonical_items + others)[:12]
        ]
        evidence_ids = []
        for _, claim, _ in canonical_items + others:
            for evidence_id in claim.get("evidence_ids", []) or []:
                if evidence_id and evidence_id not in evidence_ids:
                    evidence_ids.append(str(evidence_id))
        breakdown = ", ".join(
            f"{category} — {len(items)}"
            for category, items in sorted(by_category.items())
        )
        records.append(
            ConflictRecord(
                id=_stable_id("conflict", entity_id, "authority", *sorted(by_category)),
                conflict_type=ConflictType.SOURCE_PERSPECTIVE,
                subject_id=entity_id,
                claim_ids=claim_ids,
                evidence_ids=evidence_ids[:20],
                world_entity_ids=[entity_id] if entity_id else [],
                explanation=(
                    f"Описание сущности опирается на источники разного авторитета ({breakdown}). "
                    "Требуется сверка: неподтверждённые утверждения не должны читаться как канон."
                )[:1000],
                created_at=_now(),
            )
        )

    return records


# ── M6: рассуждения ──────────────────────────────────────────────────────


def build_reasoning(entity_id: str, card: dict[str, Any]) -> list[Any]:
    """Детерминированная агрегация утверждений одной сущности из разных источников.

    Это и есть «cross-source reasoning»: берутся утверждения, пришедшие из
    разных источников, и сводятся в один производный результат с явным
    перечнем входов и причин неопределённости.
    """
    by_source: dict[str, list[tuple[str, dict, dict]]] = {}
    for source_name, claim, provenance in _iter_card_claims(card):
        if not str(claim.get("text") or "").strip():
            continue
        by_source.setdefault(source_name or "unknown", []).append(
            (source_name, claim, provenance)
        )

    if len(by_source) < 2:
        return []

    reasoner = DeterministicReasoner()
    inputs: list[ReasoningInput] = []
    texts: list[str] = []
    categories: set[str] = set()
    for source_name in sorted(by_source):
        for _, claim, provenance in by_source[source_name][:3]:
            claim_id = _claim_identity(claim, provenance)
            if not claim_id:
                continue
            evidence_ids = [
                str(eid) for eid in (claim.get("evidence_ids", []) or []) if eid
            ]
            inputs.append(ReasoningInput(claim_id=claim_id, evidence_ids=evidence_ids))
            texts.append(f"[{source_name}] {str(claim.get('text') or '')[:160]}")
            categories.add(str(provenance.get("category") or "UNKNOWN"))

    unique = {item.claim_id: item for item in inputs}
    if len(unique) < 2:
        return []

    category = ProvenanceCategory.DERIVED
    if categories & {c.value for c in NON_PROMOTABLE}:
        category = ProvenanceCategory.HYPOTHESIS

    confidence = 0.5
    uncertainty = [
        "Сведение детерминированное: утверждения объединены по принадлежности "
        "к одной сущности, семантическая согласованность не проверялась.",
    ]
    if category is ProvenanceCategory.HYPOTHESIS:
        uncertainty.append(
            "В составе есть HYPOTHESIS-утверждения — результат остаётся гипотезой."
        )

    output_text = (
        f"Сведено утверждений из источников: {', '.join(sorted(by_source))}. "
        + " | ".join(texts[:6])
    )[:1000]

    try:
        result = reasoner.aggregate(
            output_claim_id=_stable_id("agg", entity_id, *sorted(by_source)),
            output_text=output_text,
            inputs=list(unique.values()),
            confidence=confidence,
            uncertainty_reasons=uncertainty,
            category=category,
            metadata={"subjects": [entity_id], "sources": sorted(by_source)},
        )
    except ValueError:
        return []
    result.subject_id = entity_id
    return [result]


# ── M7: предложения исправления из M10 ───────────────────────────────────


def propose_correction(
    *,
    finding_id: str,
    subject_id: str,
    superseded_claim_ids: list[str] | None = None,
    evidence_ids: list[str] | None = None,
    temporal_reference_ids: list[str] | None = None,
    reason: str = "",
) -> CorrectionRecord:
    """Собрать предложение исправления (всегда PENDING).

    Решение по предложению принимает человек (M7 confirm/reject);
    мутация WorldModel остаётся за M10.
    """
    return CorrectionRecord(
        id=_stable_id("correction", finding_id, subject_id),
        finding_id=finding_id,
        status="PENDING",
        subject_id=subject_id,
        superseded_claim_ids=sorted(
            {str(c) for c in (superseded_claim_ids or []) if c}
        ),
        evidence_ids=sorted({str(e) for e in (evidence_ids or []) if e}),
        temporal_reference_ids=sorted(
            {str(t) for t in (temporal_reference_ids or []) if t}
        ),
        reason=reason or "Предложение по finding'у темпорального обновления (M10).",
        created_at=_now(),
    )


__all__ = [
    "detect_conflicts",
    "build_reasoning",
    "propose_correction",
    "topic_key",
]
