"""M15 — Holistic Entity View: read-only агрегат доступных сведений о сущности.

Собирает книжные и сценарные claims (раздельно), явные связи книга↔сценарий,
конфликты, Evidence, типизированные мировую и временную́ ссылки — без потери
происхождения и с явным отображением отсутствия данных.

Честное ограничение: представление называется ENTITY_AGGREGATE, а не «событие»,
поскольку существующая схема не гарантирует идентификацию отдельного события
по entity_id. M17 добавил claim-level temporal linking: подтверждённые связи
claim→temporal-узел из claim_temporal_links.json отображаются отдельно от
entity-level temporal_reference и не заменяют его.

M22: event-aware holistic — канонические события, обоснованно связанные с
найденными claims сущности (валидная цепочка claim → event → epoch →
temporal node, механизм M21 gather_canonical_event_views), отдельной секцией
canonical_events. Основание — только проверенные связи claim→event; эвристики
запрещены. Пустой список — честное отсутствие подтверждённых событий.
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("hermes.holistic_view")

_VIEW_TYPE = "ENTITY_AGGREGATE"


def _availability(components: dict[str, Any]) -> dict[str, bool]:
    """Какие компоненты реально присутствуют в проекции."""
    return {
        "book_claims": bool(components.get("book_claims")),
        "screenplay_claims": bool(components.get("screenplay_claims")),
        "screenplay_links": bool(components.get("screenplay_links")),
        "contradictions": bool(components.get("contradictions")),
        "evidence": bool(components.get("evidence")),
        "world_reference_resolved": components.get("world_reference", {}).get("status") == "RESOLVED",
        "temporal_reference_resolved": components.get("temporal_reference", {}).get("status") == "RESOLVED",
        "claim_temporal_links": any(entry.get("status") != "NO_LINK" for entry in (components.get("claim_temporal_references") or [])),
        "claim_temporal_resolved": any(entry.get("status") == "RESOLVED" for entry in (components.get("claim_temporal_references") or [])),
        "canonical_events": bool(components.get("canonical_events")),
    }


def _limitations(components: dict[str, Any]) -> list[str]:
    """Явные ограничения: что отсутствует или не установлено."""
    limits: list[str] = []

    if not components.get("book_claims"):
        limits.append("Нет книжных утверждений для этой сущности")
    if not components.get("screenplay_claims"):
        limits.append("Нет сценарных утверждений для этой сущности")
    if not components.get("screenplay_links"):
        limits.append("Связи книга↔сценарий не подтверждены (screenplay_links.json пуст или связей нет)")
    if not components.get("evidence"):
        limits.append("Evidence-ссылки не разрешены или отсутствуют")

    claim_temporal = [entry for entry in (components.get("claim_temporal_references") or []) if entry.get("status") != "NO_LINK"]
    if not claim_temporal:
        limits.append(
            "Claim-level temporal linking: подтверждённых связей claims↔temporal-узлы для этой сущности нет (claim_temporal_links.json пуст или связи не установлены)"
        )
    else:
        chain_invalid = [entry for entry in claim_temporal if entry.get("status") == "CHAIN_INVALID"]
        if chain_invalid:
            reasons = sorted({str(entry.get("chain_reason", "")) for entry in chain_invalid if entry.get("chain_reason")})
            limits.append(
                f"Claim-level temporal linking: цепочка claim→event→epoch→temporal у {len(chain_invalid)} связей невалидна (CHAIN_INVALID); событие/эпоха не подтверждены WORLD_MODEL или temporal-узел не соответствует epoch (reasons={reasons})"
            )
        if not any(entry.get("status") == "RESOLVED" for entry in claim_temporal):
            statuses = sorted({str(entry.get("status", "")) for entry in claim_temporal})
            limits.append(f"Claim-level temporal linking: связи указаны, но ни одна не разрешилась в существующий temporal-узел (statuses={statuses})")

    world_status = components.get("world_reference", {}).get("status", "UNRESOLVED")
    if world_status == "AMBIGUOUS":
        limits.append("Мировая ссылка неоднозначна (AMBIGUOUS): несколько кандидатов, выбор не произведён")
    elif world_status != "RESOLVED":
        limits.append(f"Мировая ссылка не разрешена (status={world_status})")

    temporal_status = components.get("temporal_reference", {}).get("status", "UNKNOWN")
    if temporal_status != "RESOLVED":
        limits.append(
            f"Временная привязка не установлена (status={temporal_status}); temporal-узел по id сущности не является доказанной привязкой утверждения"
        )

    limits.append("Представление — агрегат сущности (ENTITY_AGGREGATE), а не доказанно идентифицированное событие")
    return limits


def build_holistic_view(entity_id: str, entity_name: str = "") -> dict[str, Any]:
    """Собрать holistic view для одной сущности.

    Read-only: не создаёт записей, не мутирует WorldModel/Temporal.
    При сбое любого компонента остальные данные сохраняются.
    """
    from core.services.knowledge_core_context import gather_knowledge_core_context

    components: dict[str, Any] = {
        "entity_id": entity_id,
        "entity_name": entity_name,
        "book_claims": [],
        "screenplay_claims": [],
        "genome_claims": [],
        "world_claims": [],
        "archaeology_claims": [],
        "contradictions": [],
        "screenplay_links": [],
        "claim_temporal_references": [],
        "evidence": [],
        "world_reference": {},
        "temporal_reference": {},
        "primary_entity": None,
    }

    # Основные материалы Knowledge Core (M14-сервис)
    contexts: list[dict[str, Any]] = []
    try:
        contexts = gather_knowledge_core_context([{"entity_id": entity_id, "name": entity_name}])
        if contexts:
            ctx = contexts[0]
            for key in (
                "book_claims",
                "screenplay_claims",
                "genome_claims",
                "world_claims",
                "archaeology_claims",
                "contradictions",
                "screenplay_links",
                "claim_temporal_references",
                "world_reference",
                "temporal_reference",
                "primary_entity",
            ):
                if ctx.get(key) is not None:
                    components[key] = ctx[key]
    except Exception as exc:
        log.warning("holistic_view_core_failed entity=%s error=%s", entity_id, exc)

    # M22: канонические события по валидным claim→event связям (механизм M21).
    # Ошибка одного события или всего сбора не ломает остальные части view.
    try:
        from core.services.knowledge_core_context import gather_canonical_event_views

        components["canonical_events"] = gather_canonical_event_views(contexts)
    except Exception as exc:
        log.warning("holistic_view_canonical_events_failed entity=%s error=%s", entity_id, exc)

    # Evidence: переиспользуем существующий M2-механизм из knowledge_cards
    try:
        from core.routes.knowledge_cards import _evidence_projection

        card_payload = {"sources": []}
        for source_name, claims_key in (
            ("book", "book_claims"),
            ("screenplay", "screenplay_claims"),
            ("genome", "genome_claims"),
            ("world_model", "world_claims"),
            ("archaeology", "archaeology_claims"),
        ):
            claims = components.get(claims_key) or []
            if claims:
                card_payload["sources"].append({"source_name": source_name, "claims": claims})
        if card_payload["sources"]:
            components["evidence"] = _evidence_projection(card_payload)
    except Exception as exc:
        log.warning("holistic_view_evidence_failed entity=%s error=%s", entity_id, exc)

    availability = _availability(components)
    limitations = _limitations(components)

    return {
        "view_type": _VIEW_TYPE,
        "entity_id": entity_id,
        "entity_name": entity_name or (components.get("primary_entity") or {}).get("name", ""),
        "primary_entity": components.get("primary_entity"),
        "book_claims": components.get("book_claims", []),
        "screenplay_claims": components.get("screenplay_claims", []),
        "genome_claims": components.get("genome_claims", []),
        "world_claims": components.get("world_claims", []),
        "archaeology_claims": components.get("archaeology_claims", []),
        "screenplay_links": components.get("screenplay_links", []),
        "claim_temporal_references": components.get("claim_temporal_references", []),
        "canonical_events": components.get("canonical_events", []),
        "contradictions": components.get("contradictions", []),
        "evidence": components.get("evidence", []),
        "world_reference": components.get("world_reference", {}),
        "temporal_reference": components.get("temporal_reference", {}),
        "availability": availability,
        "limitations": limitations,
    }


__all__ = ["build_holistic_view"]
