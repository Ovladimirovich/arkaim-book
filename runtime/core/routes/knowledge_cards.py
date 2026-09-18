"""
Knowledge Card API routes.

Endpoints:
- GET /knowledge/cards/{entity_id} — full knowledge card
- GET /knowledge/cards/search?q= — search entities
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional

from auth.rbac import require_role

log = logging.getLogger("routes.knowledge_cards")

router = APIRouter(
    prefix="/knowledge/cards",
    tags=["Knowledge Cards"],
    dependencies=[Depends(require_role("reader"))],
)


@router.get("/{entity_id}", summary="Знания о сущности")
async def get_knowledge_card(
    entity_id: str,
):
    """
    Получить Knowledge Card для сущности.

    Карточка агрегирует знания из:
    - книги (AUTHOR_CANON)
    - археологии (EXTERNAL_SOURCE)
    - кросс-культурных параллелей (DERIVED)
    - академических подтверждений (EXTERNAL_SOURCE)

    Provenance каждого утверждения сохраняется отдельно.
    """
    from knowledge_card import get_card_builder
    builder = get_card_builder()
    card = builder.build(entity_id)

    if not card.primary_entity and card.metadata.coverage_note == "Сущность не найдена":
        raise HTTPException(404, f"Entity '{entity_id}' not found in any knowledge source")

    return card.to_dict()


@router.get("/search", summary="Поиск сущностей для карточки")
async def search_entities(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(10, ge=1, le=50),
):
    """
    Поиск сущностей, по которым можно построить Knowledge Card.

    Ищет в WorldEngine и ARCHAEOLOGY.json.
    """
    from narrative_engine.world_engine import get_world_engine
    engine = get_world_engine()

    results = engine.search(q)

    # Deduplicate by name
    seen = set()
    unique = []
    for r in results:
        name = r.get("name", "")
        if name and name not in seen:
            seen.add(name)
            unique.append({
                "entity_id": r.get("id", ""),
                "name": name,
                "category": r.get("category", ""),
            })
            if len(unique) >= limit:
                break

    return {"query": q, "entities": unique, "total": len(unique)}
