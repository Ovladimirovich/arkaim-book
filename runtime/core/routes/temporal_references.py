"""M4 — Public API for Knowledge ↔ Temporal references.

Endpoint resolves a claim's temporal reference to an existing temporal
node through the existing KnowledgeTemporalResolver.
Does not create temporal nodes, fill gaps, or mutate Temporal state.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException

from auth.rbac import require_role
from knowledge.temporal_resolver import KnowledgeTemporalResolver
from schemas.temporal_reference import (
    TemporalReference,
    TemporalTimeBasis,
)

router = APIRouter(prefix="/knowledge/temporal", tags=["Temporal References"])


def get_temporal_resolver() -> KnowledgeTemporalResolver:
    """Factory for the existing KnowledgeTemporalResolver (no new resolution logic)."""
    return KnowledgeTemporalResolver()


@router.post(
    "/resolve",
    summary="Разрешить временную ссылку на узел мира",
    response_model=TemporalReference,
)
async def resolve_temporal_reference(
    claim_id: str = Body(..., min_length=1, max_length=200),
    temporal_node_id: str = Body(..., min_length=1, max_length=200),
    time_basis: TemporalTimeBasis = Body(TemporalTimeBasis.WORLD),
    resolver: KnowledgeTemporalResolver = Depends(get_temporal_resolver),
    _: None = Depends(require_role("reader")),
) -> TemporalReference:
    """Разрешить временную ссылку претензии к существующему временному узлу.

    Использует существующий ``KnowledgeTemporalResolver``. Не создаёт
    новых временных узлов, не заполняет неизвестные периоды, не мутирует
    WorldModel / Temporal состояние.
    """
    try:
        return resolver.resolve(claim_id=claim_id, temporal_node_id=temporal_node_id, time_basis=time_basis)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
