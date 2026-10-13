"""M13 — typed World/Temporal resolvers в read API (Knowledge trace).

Тесты проверяют, что trace-маршрут вызывает WorldKnowledgeResolver и
KnowledgeTemporalResolver, ответы сохраняют типы/идентификаторы/provenance,
а семантика отсутствия данных и UNKNOWN корректна.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

_CORE = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from schemas.temporal_reference import (
    TemporalReference,
    TemporalReferenceStatus,
    TemporalTimeBasis,
)
from schemas.world_reference import WorldEntityReference, WorldReferenceStatus


# ── Фикстуры / helpers ────────────────────────────────────────────────


def _resolved_world_ref(query: str = "arkaim") -> WorldEntityReference:
    return WorldEntityReference(
        query=query,
        canonical_id=f"canon_{query}",
        name=f"Канонический {query}",
        status=WorldReferenceStatus.RESOLVED,
        resolution_method="canonical_id",
        world_provenance={"source": "world_model"},
    )


def _unresolved_world_ref(query: str = "ghost") -> WorldEntityReference:
    return WorldEntityReference(
        query=query,
        status=WorldReferenceStatus.UNRESOLVED,
        reason="no canonical World Engine entity or approved crosswalk mapping",
        resolution_method="none",
    )


def _ambiguous_world_ref(query: str = "mirror") -> WorldEntityReference:
    return WorldEntityReference(
        query=query,
        status=WorldReferenceStatus.AMBIGUOUS,
        reason="approved crosswalk has multiple candidates",
        resolution_method="approved_crosswalk",
    )


def _resolved_temporal_ref(claim_id: str = "c1") -> TemporalReference:
    return TemporalReference(
        claim_id=claim_id,
        time_basis=TemporalTimeBasis.WORLD,
        status=TemporalReferenceStatus.RESOLVED,
        temporal_node_id="node_1",
        event_id="evt_1",
        precision="YEAR",
        temporal_provenance=[{"source": "book"}],
        resolution_method="temporal_engine",
    )


def _unresolved_temporal_ref(claim_id: str = "c1") -> TemporalReference:
    return TemporalReference(
        claim_id=claim_id,
        time_basis=TemporalTimeBasis.WORLD,
        status=TemporalReferenceStatus.UNRESOLVED,
        reason="temporal node not found: node_missing",
        resolution_method="temporal_engine",
    )


# ── World resolver projection ─────────────────────────────────────────


class TestWorldReferenceProjection:
    """_world_reference_projection — вызов WorldKnowledgeResolver."""

    def test_resolved_world_reference_preserves_types(self):
        from core.routes.knowledge_cards import _world_reference_projection
        from knowledge.world_resolver import WorldKnowledgeResolver

        ref = _resolved_world_ref("arkaim")
        with patch.object(WorldKnowledgeResolver, "resolve", return_value=ref):
            result = _world_reference_projection("arkaim")

        assert result["status"] == "RESOLVED"
        assert result["canonical_id"] == "canon_arkaim"
        assert result["query"] == "arkaim"
        assert result["world_provenance"] == {"source": "world_model"}

    def test_unresolved_world_reference(self):
        from core.routes.knowledge_cards import _world_reference_projection
        from knowledge.world_resolver import WorldKnowledgeResolver

        with patch.object(WorldKnowledgeResolver, "resolve", return_value=_unresolved_world_ref()):
            result = _world_reference_projection("ghost")

        assert result["status"] == "UNRESOLVED"
        assert result.get("canonical_id") is None

    def test_ambiguous_world_reference(self):
        from core.routes.knowledge_cards import _world_reference_projection
        from knowledge.world_resolver import WorldKnowledgeResolver

        with patch.object(WorldKnowledgeResolver, "resolve", return_value=_ambiguous_world_ref()):
            result = _world_reference_projection("mirror")

        assert result["status"] == "AMBIGUOUS"
        assert result.get("canonical_id") is None

    def test_resolver_failure_returns_safe_fallback(self):
        from core.routes.knowledge_cards import _world_reference_projection
        from knowledge.world_resolver import WorldKnowledgeResolver

        with patch.object(WorldKnowledgeResolver, "resolve", side_effect=RuntimeError("engine down")):
            result = _world_reference_projection("broken")

        assert result["status"] == "UNRESOLVED"
        assert result["reason"] == "world resolver failed"
        assert result["resolution_method"] == "none"

    def test_empty_query_still_returns_fallback_not_crash(self):
        """Пустой query ловится resolver-ом через ValueError → fallback."""
        from core.routes.knowledge_cards import _world_reference_projection
        from knowledge.world_resolver import WorldKnowledgeResolver

        with patch.object(WorldKnowledgeResolver, "resolve", side_effect=ValueError("empty query")):
            result = _world_reference_projection("")

        assert result["status"] == "UNRESOLVED"


# ── Temporal resolver projection ──────────────────────────────────────


class TestTemporalReferenceProjection:
    """_temporal_reference_projection — вызов KnowledgeTemporalResolver."""

    def test_resolved_temporal_reference_preserves_types(self):
        from core.routes.knowledge_cards import _temporal_reference_projection
        from knowledge.temporal_resolver import KnowledgeTemporalResolver

        ref = _resolved_temporal_ref("entity_1")
        with patch.object(KnowledgeTemporalResolver, "resolve", return_value=ref):
            result = _temporal_reference_projection("entity_1")

        assert result["status"] == "RESOLVED"
        assert result["temporal_node_id"] == "node_1"
        assert result["event_id"] == "evt_1"
        assert result["time_basis"] == "WORLD_TIME"
        assert result["temporal_provenance"] == [{"source": "book"}]

    def test_unresolved_temporal_reference(self):
        from core.routes.knowledge_cards import _temporal_reference_projection
        from knowledge.temporal_resolver import KnowledgeTemporalResolver

        with patch.object(
            KnowledgeTemporalResolver,
            "resolve",
            return_value=_unresolved_temporal_ref("entity_1"),
        ):
            result = _temporal_reference_projection("entity_1")

        assert result["status"] == "UNRESOLVED"
        assert result.get("temporal_node_id") is None

    def test_resolver_failure_returns_unknown(self):
        from core.routes.knowledge_cards import _temporal_reference_projection
        from knowledge.temporal_resolver import KnowledgeTemporalResolver

        with patch.object(
            KnowledgeTemporalResolver,
            "resolve",
            side_effect=RuntimeError("temporal down"),
        ):
            result = _temporal_reference_projection("broken")

        assert result["status"] == "UNKNOWN"
        assert result["time_basis"] == "WORLD_TIME"
        assert result["resolution_method"] == "none"

    def test_unknown_precision_semantics_preserved(self):
        """UNKNOWN-статус ссылки не получает precision ≠ UNKNOWN."""
        from core.routes.knowledge_cards import _temporal_reference_projection
        from knowledge.temporal_resolver import KnowledgeTemporalResolver

        unknown_ref = TemporalReference(
            claim_id="c_x",
            time_basis=TemporalTimeBasis.WORLD,
            status=TemporalReferenceStatus.UNKNOWN,
            reason="temporal node ID was not supplied",
            resolution_method="none",
        )
        with patch.object(KnowledgeTemporalResolver, "resolve", return_value=unknown_ref):
            result = _temporal_reference_projection("c_x")

        assert result["status"] == "UNKNOWN"
        assert result["precision"] == "UNKNOWN"


# ── Trace endpoint интеграция ─────────────────────────────────────────


def _client() -> TestClient:
    """Standalone-клиент с knowledge_cards router + auth override (паттерн M8c)."""
    from fastapi import FastAPI
    from core.routes import knowledge_cards as kc

    app = FastAPI()
    app.include_router(kc.router)
    checker = kc.router.dependencies[0].dependency  # require_role("reader")
    app.dependency_overrides[checker] = lambda: {
        "user_id": "m13-tester",
        "role": "reader",
        "provider": "test",
        "username": "m13_tester",
        "display_name": "M13 Tester",
    }
    return TestClient(app)


class TestTraceEndpointResolvers:
    """Интеграция resolvers в GET /knowledge/cards/trace/{entity_id}."""

    def test_trace_response_contains_world_and_temporal_reference(self):
        client = _client()
        response = client.get("/knowledge/cards/trace/arkaim")

        assert response.status_code == 200
        data = response.json()
        assert "world_reference" in data
        assert "temporal_reference" in data
        assert "status" in data["world_reference"]
        assert "status" in data["temporal_reference"]

    def test_trace_backward_compat_sections_preserved(self):
        """Существующие секции ответа не регрессируют."""
        client = _client()
        response = client.get("/knowledge/cards/trace/arkaim")

        assert response.status_code == 200
        data = response.json()
        for key in (
            "entity_id",
            "status",
            "claims",
            "evidence",
            "world",
            "temporal",
            "conflicts",
            "reasoning",
            "corrections",
            "lineage",
            "uncertainty",
            "limitations",
            "totals",
        ):
            assert key in data, f"trace section {key!r} missing (regression)"

    def test_trace_for_unknown_entity_still_200_with_partial(self):
        """Несущность не найдена → 200 + PARTIAL + fallback-ссылки."""
        client = _client()
        response = client.get("/knowledge/cards/trace/__nonexistent_m13__")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "PARTIAL"
        assert data["world_reference"]["status"] in ("UNRESOLVED", "CROSSWALK_UNAPPROVED")

    def test_trace_with_resolved_world_reference(self):
        """Мок: мир разрешается → world_reference RESOLVED + canonical_id."""
        from knowledge.world_resolver import WorldKnowledgeResolver

        client = _client()
        with patch.object(WorldKnowledgeResolver, "resolve", return_value=_resolved_world_ref("arkaim")):
            response = client.get("/knowledge/cards/trace/arkaim")

        assert response.status_code == 200
        data = response.json()
        assert data["world_reference"]["status"] == "RESOLVED"
        assert data["world_reference"]["canonical_id"] == "canon_arkaim"

    def test_trace_with_resolved_temporal_reference(self):
        """Мок: temporal узел есть → temporal_reference RESOLVED."""
        from knowledge.temporal_resolver import KnowledgeTemporalResolver

        client = _client()
        with patch.object(
            KnowledgeTemporalResolver,
            "resolve",
            return_value=_resolved_temporal_ref("arkaim"),
        ):
            response = client.get("/knowledge/cards/trace/arkaim")

        assert response.status_code == 200
        data = response.json()
        assert data["temporal_reference"]["status"] == "RESOLVED"
        assert data["temporal_reference"]["temporal_node_id"] == "node_1"
