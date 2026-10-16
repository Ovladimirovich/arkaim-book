"""M3 — Public API for Knowledge ↔ World references.

Endpoint resolves a query to an existing canonical World entity
through the existing WorldKnowledgeResolver and approved crosswalk.
Does not create identities, does not extend crosswalk.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException

from auth.rbac import require_role
from knowledge.world_resolver import WorldKnowledgeResolver
from schemas.world_reference import WorldEntityReference

router = APIRouter(prefix="/knowledge/world", tags=["World References"])


def get_world_resolver() -> WorldKnowledgeResolver:
    """Factory for the existing WorldKnowledgeResolver (no new resolution logic)."""
    return WorldKnowledgeResolver()


@router.post(
    "/resolve",
    summary="Разрешить ссылку на сущность мира",
    response_model=WorldEntityReference,
)
async def resolve_world_reference(
    query: str = Body(..., min_length=1, max_length=200),
    resolver: WorldKnowledgeResolver = Depends(get_world_resolver),
    _: None = Depends(require_role("reader")),
) -> WorldEntityReference:
    """Разрешить запрос к существующей канонической сущности мира.

    Использует существующий ``WorldKnowledgeResolver`` и утверждённый
    crosswalk. Не создаёт новых канонических ID, не расширяет crosswalk.
    """
    try:
        return resolver.resolve(query)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
