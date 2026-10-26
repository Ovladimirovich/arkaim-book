# -*- coding: utf-8 -*-
"""
AskGapDetector - определение статуса знания для вопроса.

Stage 2: Gap Detection для /book/ask.

Правило: отсутствие structuredClaim в Knowledge Core не означает отсутствие факта.
Gap = подтверждённого структурированного знания сейчас недостаточно.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from core.services.related_entities import resolve_related_entities
from core.services.knowledge_core_context import gather_knowledge_core_context


@dataclass
class GapReport:
    """Результат обнаружения gap для вопроса."""

    question: str
    status: str = "UNKNOWN"
    missing_knowledge_area: str = ""
    relevant_entities: list[str] = field(default_factory=list)
    relevant_claims: list[dict[str, Any]] = field(default_factory=list)
    evidence_available: int = 0
    source_search_required: bool = False
    confidence: float = 0.0
    detection_method: list[str] = field(default_factory=list)
    context_snippet: str = ""


def classify_status(
    question: str, entity_names: list[str], knowledge_contexts: list[dict[str, Any]], constraints: Optional[list[dict[str, Any]]] = None
) -> str:
    """Определить статус знания для вопроса."""
    if constraints:
        for c in constraints:
            if c.get("status") == "CONFLICT":
                return "CONFLICTING"
    if not knowledge_contexts and not entity_names:
        return "MISSING"
    if knowledge_contexts:
        fact_count = _count_facts(knowledge_contexts)
        if fact_count >= 3:
            return "KNOWN"
        if fact_count >= 1:
            return "PARTIALLY_KNOWN"
    return "MISSING"


def _count_facts(contexts: list[dict[str, Any]]) -> int:
    """Считать структурированные claims по всем релевантным группам."""
    groups = (
        "book_claims",
        "genome_claims",
        "world_claims",
        "archaeology_claims",
    )
    return sum(sum(len(c.get(g, []) or []) for g in groups) for c in contexts)


def detect_gap(
    question: str,
    existing_dialogue_context: Optional[dict[str, Any]] = None,
    existing_knowledge_core: Optional[list[dict[str, Any]]] = None,
    related_entities: Optional[list[dict[str, Any]]] = None,
    constraints: Optional[list[dict[str, Any]]] = None,
) -> GapReport:
    """Обнаружить gap для вопроса на основе существующего знания.

    Инъекция (опционально):
    - related_entities — уже посчитанные /book/ask (Stage 1);
    - existing_knowledge_core — уже собранные t1-контексты Knowledge Core.
    Без инъекции — самостоятельный расчёт (детектор самодостаточен).
    """
    report = GapReport(question=question)
    if related_entities is not None:
        entities = related_entities
        report.detection_method.append("entity_injection")
    else:
        entities, _rationale = resolve_related_entities(
            {
                "question": question,
                "answer": str((existing_dialogue_context or {}).get("answer") or ""),
            }
        )
        report.detection_method.append("entity_resolution")
    entity_names = [e.get("name", "") for e in entities]
    report.relevant_entities = entity_names
    contexts = existing_knowledge_core or []
    if not contexts:
        contexts = gather_knowledge_core_context(entities)
    report.context_snippet = str(contexts)[:300]
    report.status = classify_status(
        question=question,
        entity_names=entity_names,
        knowledge_contexts=contexts,
        constraints=constraints,
    )
    if contexts:
        report.evidence_available = _count_facts(contexts)
    if report.status in ("MISSING", "CONFLICTING"):
        report.source_search_required = True
    elif report.status == "PARTIALLY_KNOWN":
        report.source_search_required = True
    if report.status in ("MISSING", "CONFLICTING", "PARTIALLY_KNOWN"):
        report.missing_knowledge_area = _identify_gap_area(question, entity_names, contexts)
        report.relevant_claims = _collect_relevant_claims(contexts)[:5]
    if report.evidence_available == 0:
        report.confidence = 0.0
    elif report.status == "KNOWN":
        report.confidence = min(0.95, 0.5 + report.evidence_available * 0.05)
    elif report.status == "PARTIALLY_KNOWN":
        report.confidence = 0.6
    elif report.status == "MISSING":
        report.confidence = 0.3
    elif report.status == "CONFLICTING":
        report.confidence = 0.4
    return report


def _collect_relevant_claims(
    contexts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Собрать репрезентативные claims из контекстов (по одному из каждой группы)."""
    claims: list[dict[str, Any]] = []
    groups = (
        "book_claims",
        "genome_claims",
        "world_claims",
        "archaeology_claims",
    )
    for context in contexts:
        for group in groups:
            items = context.get(group, []) or []
            if items:
                claims.append(
                    {
                        "entity_id": context.get("entity_id", ""),
                        "entity_name": context.get("entity_name", ""),
                        "group": group,
                        "claim": items[0],
                    }
                )
    return claims


def _identify_gap_area(
    question: str,
    entity_names: list[str],
    contexts: list[dict[str, Any]],
) -> str:
    """Определить, какая область знаний недостаточно."""
    if entity_names:
        return "Дополнительная информация о: " + entity_names[0]
    return "Дополнительные знания о предмете вопроса"


if __name__ == "__main__":
    sample = detect_gap(
        question="Кто убил Арема?",
        existing_dialogue_context={},
    )
    print("GAP DETECTED")
    print("  status: " + sample.status)
    print("  evidence: " + str(sample.evidence_available))
    print("  search_required: " + str(sample.source_search_required))
