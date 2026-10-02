"""M4 — Knowledge Temporal reference resolver.

Read-only adapter over the existing Temporal reconstruction engine. It resolves
references to existing nodes only; it does not create temporal nodes, fill gaps,
choose an anchor, or mutate WorldModel/Temporal state.
"""

from __future__ import annotations

from typing import Any, Protocol

from narrative_engine.temporal.node import TemporalNode
from schemas.temporal_reference import (
    TemporalReference,
    TemporalReferenceStatus,
    TemporalTimeBasis,
)


class TemporalNodeReader(Protocol):
    def get_node(self, node_id: str) -> TemporalNode | None: ...


class KnowledgeTemporalResolver:
    """Resolve a claim's temporal reference without changing Temporal state."""

    def __init__(self, temporal_engine: TemporalNodeReader | None = None):
        self._temporal_engine = temporal_engine

    def _engine(self) -> TemporalNodeReader:
        if self._temporal_engine is None:
            from narrative_engine.world_engine import get_world_engine

            self._temporal_engine = get_world_engine().enable_temporal()
        return self._temporal_engine

    @staticmethod
    def _bounds(node: TemporalNode) -> dict | None:
        bounds = node.bounds
        if bounds is None or (bounds.start is None and bounds.end is None and bounds.uncertainty is None):
            return None
        return {
            "start": bounds.start,
            "end": bounds.end,
            "uncertainty": bounds.uncertainty,
        }

    def resolve(
        self,
        claim_id: str,
        temporal_node_id: str,
        *,
        time_basis: TemporalTimeBasis = TemporalTimeBasis.WORLD,
    ) -> TemporalReference:
        """Resolve one existing temporal node; an absent node stays unresolved."""
        claim = str(claim_id or "").strip()
        node_id = str(temporal_node_id or "").strip()
        if not claim:
            raise ValueError("claim_id must not be empty")

        if not node_id:
            return TemporalReference(
                claim_id=claim,
                time_basis=time_basis,
                status=TemporalReferenceStatus.UNKNOWN,
                reason="temporal node ID was not supplied",
                resolution_method="none",
            )

        node = self._engine().get_node(node_id)
        if node is None:
            return TemporalReference(
                claim_id=claim,
                time_basis=time_basis,
                status=TemporalReferenceStatus.UNRESOLVED,
                reason=f"temporal node not found: {node_id}",
                resolution_method="temporal_engine",
            )

        return TemporalReference(
            claim_id=claim,
            time_basis=time_basis,
            status=TemporalReferenceStatus.RESOLVED,
            temporal_node_id=node.id,
            event_id=node.event_ids[0] if node.event_ids else None,
            era_id=node.era_id or None,
            precision=node.precision,
            bounds=self._bounds(node),
            temporal_provenance=[p.to_dict() for p in node.provenance],
            resolution_method="temporal_engine",
        )


__all__ = ["TemporalNodeReader", "KnowledgeTemporalResolver"]