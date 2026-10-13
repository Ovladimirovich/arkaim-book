"""M14 — сбор материалов Knowledge Core для обогащения контекста Ask/RAG.

Сервис читает Knowledge Card builder, typed world/temporal resolvers и
screenplay_links, не создавая записей. Используется маршрутом /book/ask
после keeper.act() и resolve_related_entities, чтобы ответ сохранял
provenance и не выдумывал факты при отсутствии данных.

M16.2: одобренные связи книга↔сценарий (screenplay_links.json) дополнительно
разрешаются по реальным book_chunk_id книжных claims сущности — только при
точном совпадении идентификатора, без эвристик.

M17: claim-level temporal linking — для книжных claims со стабильным claim_id
(CanonClaim.make_id) разрешаются подтверждённые связи claim→temporal-узел из
claim_temporal_links.json. Статусы честные: NO_LINK / RESOLVED / UNRESOLVED /
AMBIGUOUS. Entity-level temporal_reference остаётся отдельным полем и не
заменяет claim-level привязку.

M21: event-aware Ask/RAG — для валидных claim→event связей (RESOLVED,
chain_valid=True) найденных книжных claims строятся представления
канонических событий через canonical_event_view.build_canonical_event_view.
Основание — только проверенная связь claim→event; эвристики (название,
персонаж, тема) запрещены. События без валидной цепочки не включаются.
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("hermes.knowledge_core_context")


def _extract_claims(card_dict: dict[str, Any], source_name: str) -> list[dict[str, Any]]:
    """Достать claims из одного source Knowledge Card."""
    claims: list[dict[str, Any]] = []
    for source in card_dict.get("sources", []):
        if source.get("source_name") != source_name:
            continue
        for claim in source.get("claims", []):
            claims.append(
                {
                    "text": claim.get("text", ""),
                    "source_ref": claim.get("source_ref", ""),
                    "provenance": claim.get("provenance", {}),
                }
            )
    return claims


def _extract_contradictions(card_dict: dict[str, Any]) -> list[dict[str, Any]]:
    """Достать contradictions без сглаживания."""
    contradictions: list[dict[str, Any]] = []
    for note in card_dict.get("contradictions", []):
        contradictions.append(
            {
                "description": note.get("description", ""),
                "source_1_claim": note.get("source_1_claim", ""),
                "source_2_claim": note.get("source_2_claim", ""),
                "resolution": note.get("resolution", "UNRESOLVED"),
            }
        )
    return contradictions


def _book_chunk_ids_from_card(card_dict: dict[str, Any]) -> list[str]:
    """Реальные book_chunk_id из книжных claims карточки (M16.2).

    Извлекает chunk_id поле claim; при его отсутствии — разбирает
    source_ref вида "book:chunk_p_...". Fallback "chunk" без реального
    идентификатора отбрасывается. Порядок детерминирован (порядок claims).
    """
    ids: list[str] = []
    for source in card_dict.get("sources", []):
        if source.get("source_name") != "book":
            continue
        for claim in source.get("claims", []):
            chunk_id = str(claim.get("chunk_id") or "").strip()
            if not chunk_id:
                source_ref = str(claim.get("source_ref") or "")
                if source_ref.startswith("book:"):
                    chunk_id = source_ref.removeprefix("book:").strip()
            if chunk_id and chunk_id != "chunk":
                ids.append(chunk_id)
    return list(dict.fromkeys(ids))


def _augment_screenplay_links(
    card_dict: dict[str, Any],
    card_links: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """M16.2: добавить одобренные связи по реальным book_chunk_id из claims.

    Сопоставление только по точному совпадению book_chunk_id с записями
    screenplay_links.json (M16.1). Эвристики (текст, имя, персонажи,
    номера сцен, время) запрещены и не используются. Существующие связи
    карточки сохраняются; дубли пар (scene, chunk) отбрасываются.
    """
    from knowledge.screenplay_linker import ScreenplayBookLinker

    try:
        linker = ScreenplayBookLinker.from_json()
    except Exception as exc:
        log.warning("knowledge_core_screenplay_linker_failed error=%s", exc)
        return card_links

    augmented = list(card_links)
    seen = {(str(link.get("screenplay_scene_id", "")), str(link.get("book_chunk_id", ""))) for link in augmented}
    for chunk_id in _book_chunk_ids_from_card(card_dict):
        for link in linker.get_links_for_chunk(chunk_id):
            key = (link.screenplay_scene_id, link.book_chunk_id)
            if key in seen:
                continue
            seen.add(key)
            augmented.append(
                {
                    "screenplay_scene_id": link.screenplay_scene_id,
                    "book_chunk_id": link.book_chunk_id,
                    "confidence": link.confidence,
                    "notes": link.notes,
                }
            )
    return augmented


def _claim_temporal_references(card_dict: dict[str, Any]) -> list[dict[str, Any]]:
    """M17/M18: claim-level temporal references из явного реестра.

    Для каждого книжного claim со стабильным claim_id (CanonClaim.make_id,
    тот же контракт, что в knowledge_cards._card_claim_id) ищет подтверждённую
    связь в claim_temporal_links.json. Одна связь → KnowledgeTemporalResolver
    (typed TemporalReference). Несколько связей → AMBIGUOUS без автовыбора.
    Нет связей → честный NO_LINK. Эвристики (текст, порядок, имя, время)
    запрещены и не используются.

    M18: цепочка claim_id → event_id → epoch_id → temporal_node_id валидируется
    против WORLD_MODEL. event_id и доступные сведения о каноническом событии
    передаются в проекцию. Невалидная цепочка не выбрасывается и не подменяется —
    она помечается CHAIN_INVALID и передаётся дальше с явным статусом.
    """
    from knowledge.claim_temporal_linker import ClaimTemporalLinker
    from narrative_engine.provenance.claim import CanonClaim

    try:
        linker = ClaimTemporalLinker.from_json()
    except Exception as exc:
        log.warning("knowledge_core_claim_temporal_linker_failed error=%s", exc)
        return []

    entries: list[dict[str, Any]] = []
    for source in card_dict.get("sources", []):
        if source.get("source_name") != "book":
            continue
        for claim in source.get("claims", []):
            text = str(claim.get("text") or "")
            chunk_id = str(claim.get("chunk_id") or "")
            source_ref = str(claim.get("source_ref") or "")
            if not text or not source_ref.startswith("book:") or not chunk_id or chunk_id == "chunk":
                continue

            claim_id = CanonClaim.make_id(text, source_id="book", location=f"chunk:{chunk_id}")
            links = linker.get_links_for_claim(claim_id)

            if not links:
                entries.append(
                    {
                        "claim_id": claim_id,
                        "source_ref": source_ref,
                        "status": "NO_LINK",
                        "temporal_reference": None,
                    }
                )
            elif len(links) == 1:
                from knowledge.temporal_resolver import KnowledgeTemporalResolver
                from schemas.temporal_reference import TemporalTimeBasis

                link = links[0]
                # M18: валидация цепочки claim → event → epoch → temporal_node.
                # event_id опционален по схеме M17; если указан — цепочка
                # проверяется строго, невалидная помечается CHAIN_INVALID.
                # Если event_id нет — валидация цепочки пропускается (обратная
                # совместимость с M17-связями без события).
                chain = ClaimTemporalLinker.validate_chain(link) if link.event_id else None
                event_info: dict[str, Any] = {
                    "event_id": link.event_id,
                    "epoch_id": chain.epoch_id if chain else None,
                    "chain_valid": chain.valid if chain else None,
                }
                if chain is not None and not chain.valid:
                    # Невалидная цепочка: не подменяем, помечаем явно
                    log.warning(
                        "knowledge_core_claim_chain_invalid claim=%s event=%s reason=%s",
                        claim_id,
                        link.event_id,
                        chain.reason,
                    )
                    entries.append(
                        {
                            "claim_id": claim_id,
                            "source_ref": source_ref,
                            "status": "CHAIN_INVALID",
                            "temporal_reference": None,
                            "notes": link.notes,
                            "event": event_info,
                            "chain_reason": chain.reason,
                        }
                    )
                    continue

                try:
                    ref = KnowledgeTemporalResolver().resolve(
                        claim_id=claim_id,
                        temporal_node_id=link.temporal_node_id,
                        time_basis=TemporalTimeBasis.WORLD,
                    )
                    entries.append(
                        {
                            "claim_id": claim_id,
                            "source_ref": source_ref,
                            "status": ref.status.value,
                            "temporal_reference": ref.model_dump(mode="json"),
                            "notes": link.notes,
                            "event": event_info,
                        }
                    )
                except Exception as exc:
                    log.warning("knowledge_core_claim_temporal_resolve_failed claim=%s error=%s", claim_id, exc)
                    entries.append(
                        {
                            "claim_id": claim_id,
                            "source_ref": source_ref,
                            "status": "UNRESOLVED",
                            "temporal_reference": None,
                            "notes": link.notes,
                            "event": event_info,
                        }
                    )
            else:
                entries.append(
                    {
                        "claim_id": claim_id,
                        "source_ref": source_ref,
                        "status": "AMBIGUOUS",
                        "temporal_reference": None,
                        "candidate_node_ids": [link.temporal_node_id for link in links],
                    }
                )
    return entries


def _entity_context(entity_id: str, entity_name: str) -> dict[str, Any] | None:
    """Собрать контекст одной сущности. Вернуть None, если данных нет."""
    from knowledge_card import get_card_builder

    builder = get_card_builder()
    card = builder.build(entity_id)
    card_dict = card.to_dict()

    book_claims = _extract_claims(card_dict, "book")
    screenplay_claims = _extract_claims(card_dict, "screenplay")
    genome_claims = _extract_claims(card_dict, "genome")
    world_claims = _extract_claims(card_dict, "world_model")
    archaeology_claims = _extract_claims(card_dict, "archaeology")
    contradictions = _extract_contradictions(card_dict)
    screenplay_links = _augment_screenplay_links(card_dict, card_dict.get("screenplay_links", []) or [])
    claim_temporal_references = _claim_temporal_references(card_dict)

    world_reference: dict[str, Any] = {}
    temporal_reference: dict[str, Any] = {}
    try:
        from knowledge.world_resolver import WorldKnowledgeResolver

        world_ref = WorldKnowledgeResolver().resolve(entity_id)
        world_reference = world_ref.model_dump(mode="json")
    except Exception as exc:
        log.warning("knowledge_core_world_resolver_failed entity=%s error=%s", entity_id, exc)
        world_reference = {
            "query": entity_id,
            "status": "UNRESOLVED",
            "reason": "world resolver unavailable",
            "resolution_method": "none",
        }

    try:
        from knowledge.temporal_resolver import KnowledgeTemporalResolver
        from schemas.temporal_reference import TemporalTimeBasis

        temporal_ref = KnowledgeTemporalResolver().resolve(
            claim_id=entity_id,
            temporal_node_id=entity_id,
            time_basis=TemporalTimeBasis.WORLD,
        )
        temporal_reference = temporal_ref.model_dump(mode="json")
    except Exception as exc:
        log.warning("knowledge_core_temporal_resolver_failed entity=%s error=%s", entity_id, exc)
        temporal_reference = {
            "claim_id": entity_id,
            "time_basis": "WORLD_TIME",
            "status": "UNKNOWN",
            "reason": "temporal resolver unavailable",
            "resolution_method": "none",
        }

    has_any_claims = any((book_claims, screenplay_claims, genome_claims, world_claims, archaeology_claims))
    has_world_resolved = world_reference.get("status") == "RESOLVED"

    if not has_any_claims and not has_world_resolved and not card_dict.get("primary_entity"):
        return None

    return {
        "entity_id": entity_id,
        "entity_name": entity_name,
        "world_reference": world_reference,
        "temporal_reference": temporal_reference,
        "book_claims": book_claims,
        "screenplay_claims": screenplay_claims,
        "genome_claims": genome_claims,
        "world_claims": world_claims,
        "archaeology_claims": archaeology_claims,
        "contradictions": contradictions,
        "screenplay_links": screenplay_links,
        "claim_temporal_references": claim_temporal_references,
        "primary_entity": card_dict.get("primary_entity"),
    }


def _collect_event_ids(contexts: list[dict[str, Any]]) -> list[str]:
    """Уникальные event_id из валидных claim-связей контекстов (M21).

    Только claim_temporal_references со status=RESOLVED и подтверждённой
    валидной цепочкой (chain_valid=True) и непустым event_id. События
    CHAIN_INVALID / NO_LINK / UNRESOLVED / AMBIGUOUS не включаются.
    Порядок детерминирован (сортировка по event_id), дубли исключены.
    """
    event_ids: set[str] = set()
    for context in contexts:
        for entry in context.get("claim_temporal_references") or []:
            if entry.get("status") != "RESOLVED":
                continue
            event_info = entry.get("event") or {}
            if event_info.get("chain_valid") is not True:
                continue
            event_id = str(event_info.get("event_id") or "").strip()
            if event_id:
                event_ids.add(event_id)
    return sorted(event_ids)


def gather_canonical_event_views(contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """M21: представления канонических событий для контекста Ask/RAG.

    Для каждого уникального event_id, подтверждённого валидной claim-связью
    найденных книжных claims (M17/M18), читается
    canonical_event_view.build_canonical_event_view. Read-only: не создаёт
    записей, не мутирует WorldModel/Temporal. Сбой одного события не
    отменяет остальные; ненайденные события не включаются.
    """
    from core.services.canonical_event_view import build_canonical_event_view

    views: list[dict[str, Any]] = []
    for event_id in _collect_event_ids(contexts):
        try:
            view = build_canonical_event_view(event_id)
        except Exception as exc:
            log.warning("knowledge_core_canonical_event_failed event=%s error=%s", event_id, exc)
            continue
        if view.get("found"):
            views.append(view)
        else:
            log.warning("knowledge_core_canonical_event_not_found event=%s", event_id)
    return views


def gather_knowledge_core_context(
    related_entities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Собрать материалы Knowledge Core для связанных сущностей.

    Возвращает пустой список, если данные недоступны или сущностей нет.
    Не создаёт записей, не мутирует WorldModel/Temporal.
    """
    if not related_entities:
        return []

    contexts: list[dict[str, Any]] = []
    for entity in related_entities[:3]:
        entity_id = str(entity.get("entity_id", "")).strip()
        entity_name = str(entity.get("name", ""))
        if not entity_id:
            continue
        try:
            context = _entity_context(entity_id, entity_name)
            if context is not None:
                contexts.append(context)
        except Exception as exc:
            log.warning("knowledge_core_context_failed entity=%s error=%s", entity_id, exc)
    return contexts


__all__ = ["gather_knowledge_core_context", "gather_canonical_event_views"]
