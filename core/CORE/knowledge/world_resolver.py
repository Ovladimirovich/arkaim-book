"""M3 — Knowledge World reference resolver.

Read-only adapter between Knowledge and the existing World Engine/canonical
identity flow. This resolver does not mutate WorldModel, does not extend the
approved crosswalk, and does not infer identity from fuzzy names.
"""

from __future__ import annotations

from typing import Any, Protocol

from narrative_engine.world_model import WorldModel, _load_approved_crosswalk
from schemas.world_reference import WorldEntityReference, WorldReferenceStatus


class WorldEntityReader(Protocol):
    def get_entity(self, entity_id: str) -> dict[str, Any] | None: ...

    def search(self, query: str) -> Any: ...


class WorldKnowledgeResolver:
    """Resolve Knowledge queries to existing World Engine canonical entities."""

    def __init__(
        self,
        world_engine: WorldEntityReader | None = None,
        world_model: WorldModel | None = None,
    ):
        self._world_engine = world_engine
        self._world_model = world_model
        self._approved = _load_approved_crosswalk()

    def _engine(self) -> WorldEntityReader:
        if self._world_engine is None:
            from narrative_engine.world_engine import get_world_engine

            self._world_engine = get_world_engine()
            self._world_engine.initialize()
        return self._world_engine

    def _canonical_entity(self, entity_id: str) -> dict[str, Any] | None:
        entity = self._engine().get_entity(entity_id)
        return entity if isinstance(entity, dict) else None

    def resolve(self, query: str) -> WorldEntityReference:
        """Resolve a query without fuzzy name matching or identity creation."""
        raw_query = str(query or "").strip()
        if not raw_query:
            raise ValueError("World knowledge reference query must not be empty")

        direct = self._canonical_entity(raw_query)
        if direct is not None:
            return WorldEntityReference(
                query=raw_query,
                canonical_id=str(direct.get("id") or raw_query),
                name=direct.get("name"),
                status=WorldReferenceStatus.RESOLVED,
                resolution_method="canonical_id",
                world_provenance=direct.get("provenance"),
            )

        # Crosswalk keys are casefolded at load time, so lookups must be too.
        approved_ids = self._approved.get(raw_query.casefold(), [])
        if len(approved_ids) == 1:
            entity = self._canonical_entity(approved_ids[0])
            if entity is not None:
                return WorldEntityReference(
                    query=raw_query,
                    canonical_id=str(entity.get("id") or approved_ids[0]),
                    name=entity.get("name"),
                    status=WorldReferenceStatus.RESOLVED,
                    resolution_method="approved_crosswalk",
                    world_provenance=entity.get("provenance"),
                )

        if len(approved_ids) > 1:
            return WorldEntityReference(
                query=raw_query,
                status=WorldReferenceStatus.AMBIGUOUS,
                reason=f"approved crosswalk has multiple candidates: {approved_ids}",
                resolution_method="approved_crosswalk",
            )

        if self._is_unapproved_candidate(raw_query):
            return WorldEntityReference(
                query=raw_query,
                status=WorldReferenceStatus.CROSSWALK_UNAPPROVED,
                reason="entity exists, but crosswalk mapping is not owner-approved",
                resolution_method="unapproved_candidate",
            )

        return WorldEntityReference(
            query=raw_query,
            status=WorldReferenceStatus.UNRESOLVED,
            reason="no canonical World Engine entity or approved crosswalk mapping",
            resolution_method="none",
        )

    def _is_unapproved_candidate(self, query: str) -> bool:
        """Recognize only exact known entities; never infer from fuzzy names."""
        try:
            matches = self._engine().search(query)
        except Exception:
            return False
        candidates = matches.get("world_model", []) if isinstance(matches, dict) else []
        if not isinstance(candidates, list):
            return False
        normalized = query.casefold().strip()
        return any(
            isinstance(item, dict)
            and normalized
            in {
                str(item.get("id", "")).casefold(),
                str(item.get("name", "")).casefold(),
            }
            for item in candidates
        )


__all__ = ["WorldEntityReader", "WorldKnowledgeResolver"]
