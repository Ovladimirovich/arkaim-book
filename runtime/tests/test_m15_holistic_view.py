"""M15 — Holistic Entity View tests.

Покрывает 10 сценариев приёмки: только книга, только сценарий, связь/
отсутствие связи, конфликт, статусы world/temporal, частичные данные,
сохранение идентификаторов/provenance, обратная совместимость.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

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


# ── Helpers ────────────────────────────────────────────────────────────


def _make_card_dict(
    *,
    book_claims: list[dict] | None = None,
    screenplay_claims: list[dict] | None = None,
    contradictions: list[dict] | None = None,
    screenplay_links: list[dict] | None = None,
    primary_entity: dict | None = None,
) -> dict:
    sources = []
    if book_claims is not None:
        sources.append({"source_name": "book", "claims": book_claims})
    if screenplay_claims is not None:
        sources.append({"source_name": "screenplay", "claims": screenplay_claims})
    return {
        "metadata": {"entity_id": "test", "entity_name": "Тест"},
        "primary_entity": primary_entity,
        "sources": sources,
        "contradictions": contradictions or [],
        "screenplay_links": screenplay_links or [],
    }


def _claim(text: str, source_ref: str, chunk_id: str | None = None) -> dict:
    c = {
        "text": text,
        "source_ref": source_ref,
        "provenance": {"category": "AUTHOR_CANON", "confidence": 1.0},
    }
    if chunk_id:
        c["chunk_id"] = chunk_id
    return c


def _world_ref(status: WorldReferenceStatus = WorldReferenceStatus.RESOLVED, query: str = "arkaim") -> WorldEntityReference:
    if status is WorldReferenceStatus.RESOLVED:
        return WorldEntityReference(
            query=query,
            canonical_id=f"canon_{query}",
            name="Канонический",
            status=status,
            resolution_method="canonical_id",
        )
    return WorldEntityReference(query=query, status=status, resolution_method="none")


def _temporal_ref(status: TemporalReferenceStatus = TemporalReferenceStatus.RESOLVED) -> TemporalReference:
    if status is TemporalReferenceStatus.RESOLVED:
        return TemporalReference(
            claim_id="c1",
            time_basis=TemporalTimeBasis.WORLD,
            status=status,
            temporal_node_id="node_1",
            precision="YEAR",
            resolution_method="temporal_engine",
        )
    return TemporalReference(
        claim_id="c1",
        time_basis=TemporalTimeBasis.WORLD,
        status=status,
        reason="not found",
        resolution_method="temporal_engine",
    )


def _patched_components(
    card_dict: dict,
    world_ref: WorldEntityReference | None = None,
    temporal_ref: TemporalReference | None = None,
    evidence_rows: list[dict] | None = None,
):
    """Context manager: патчит все зависимости build_holistic_view."""
    from contextlib import contextmanager

    @contextmanager
    def _cm():
        mock_card = MagicMock()
        mock_card.to_dict.return_value = card_dict
        mock_builder = MagicMock()
        mock_builder.build.return_value = mock_card

        with patch("knowledge_card.get_card_builder", return_value=mock_builder):
            with patch("knowledge.world_resolver.WorldKnowledgeResolver") as mock_wr:
                mock_wr.return_value.resolve.return_value = world_ref or _world_ref(WorldReferenceStatus.UNRESOLVED)
                with patch("knowledge.temporal_resolver.KnowledgeTemporalResolver") as mock_tr:
                    mock_tr.return_value.resolve.return_value = temporal_ref or _temporal_ref(TemporalReferenceStatus.UNKNOWN)
                    with patch(
                        "core.routes.knowledge_cards._evidence_projection",
                        return_value=evidence_rows or [],
                    ):
                        yield

    return _cm()


# ── build_holistic_view — unit ────────────────────────────────────────


class TestHolisticViewContent:
    """Сценарии 1–5: содержимое проекции."""

    def test_book_only_entity(self):
        """Сценарий 1: только книжные claims."""
        from core.services.holistic_view import build_holistic_view

        card = _make_card_dict(
            book_claims=[_claim("Аркаим — городище", "book:chunk_p_0001", "chunk_p_0001")],
        )
        with _patched_components(card):
            view = build_holistic_view("arkaim", "Аркаим")

        assert view["view_type"] == "ENTITY_AGGREGATE"
        assert len(view["book_claims"]) == 1
        assert view["book_claims"][0]["source_ref"] == "book:chunk_p_0001"
        assert view["book_claims"][0]["provenance"]["category"] == "AUTHOR_CANON"
        assert view["screenplay_claims"] == []
        assert view["availability"]["book_claims"] is True
        assert view["availability"]["screenplay_claims"] is False

    def test_screenplay_only_entity(self):
        """Сценарий 2: только сценарные claims."""
        from core.services.holistic_view import build_holistic_view

        card = _make_card_dict(
            screenplay_claims=[_claim("Визуальная деталь", "screenplay:scene:scene_003")],
        )
        with _patched_components(card):
            view = build_holistic_view("scene_entity", "Сцена")

        assert len(view["screenplay_claims"]) == 1
        assert view["screenplay_claims"][0]["source_ref"] == "screenplay:scene:scene_003"
        assert view["book_claims"] == []
        assert view["availability"]["screenplay_claims"] is True
        assert view["availability"]["book_claims"] is False

    def test_book_and_screenplay_with_explicit_link(self):
        """Сценарий 3: книга + сценарий + явная связь."""
        from core.services.holistic_view import build_holistic_view

        links = [{"book_chunk_id": "chunk_p_0001", "screenplay_scene_id": "scene_000", "confidence": 1.0}]
        card = _make_card_dict(
            book_claims=[_claim("текст", "book:chunk_p_0001", "chunk_p_0001")],
            screenplay_claims=[_claim("сцена", "screenplay:scene:scene_000")],
            screenplay_links=links,
        )
        with _patched_components(card):
            view = build_holistic_view("linked", "Связанный")

        assert len(view["book_claims"]) == 1
        assert len(view["screenplay_claims"]) == 1
        assert len(view["screenplay_links"]) == 1
        assert view["screenplay_links"][0]["screenplay_scene_id"] == "scene_000"
        assert view["availability"]["screenplay_links"] is True

    def test_book_and_screenplay_without_link(self):
        """Сценарий 4: книга + сценарий без связи — эвристика не добавляется."""
        from core.services.holistic_view import build_holistic_view

        card = _make_card_dict(
            book_claims=[_claim("текст", "book:chunk_a", "chunk_a")],
            screenplay_claims=[_claim("сцена", "screenplay:scene:scene_001")],
            screenplay_links=[],
        )
        with _patched_components(card):
            view = build_holistic_view("unlinked", "Не связанный")

        assert len(view["book_claims"]) == 1
        assert len(view["screenplay_claims"]) == 1
        assert view["screenplay_links"] == []
        assert view["availability"]["screenplay_links"] is False
        # В limitations явно указано об отсутствии связи
        assert any("связь" in lim.lower() or "screenplay_links" in lim for lim in view["limitations"])

    def test_conflict_preserved(self):
        """Сценарий 5: конфликт источников сохраняется."""
        from core.services.holistic_view import build_holistic_view

        contradictions = [
            {
                "description": "Книга vs археология",
                "source_1_claim": "AUTHOR_CANON: X",
                "source_2_claim": "EXTERNAL_SOURCE: нет данных",
                "resolution": "UNRESOLVED",
            }
        ]
        card = _make_card_dict(
            book_claims=[_claim("текст", "book:chunk_d", "chunk_d")],
            contradictions=contradictions,
        )
        with _patched_components(card):
            view = build_holistic_view("conflicted", "Конфликтный")

        assert len(view["contradictions"]) == 1
        assert view["contradictions"][0]["resolution"] == "UNRESOLVED"
        assert view["availability"]["contradictions"] is True


# ── Статусы world/temporal ────────────────────────────────────────────


class TestHolisticViewStatuses:
    """Сценарии 6–7: статусы world и temporal references."""

    def test_world_resolved(self):
        from core.services.holistic_view import build_holistic_view

        card = _make_card_dict(book_claims=[_claim("x", "book:c1", "c1")])
        with _patched_components(card, world_ref=_world_ref(WorldReferenceStatus.RESOLVED)):
            view = build_holistic_view("arkaim")

        assert view["world_reference"]["status"] == "RESOLVED"
        assert view["world_reference"]["canonical_id"] == "canon_arkaim"
        assert view["availability"]["world_reference_resolved"] is True

    def test_world_unresolved(self):
        from core.services.holistic_view import build_holistic_view

        card = _make_card_dict(book_claims=[_claim("x", "book:c1", "c1")])
        with _patched_components(card, world_ref=_world_ref(WorldReferenceStatus.UNRESOLVED)):
            view = build_holistic_view("ghost")

        assert view["world_reference"]["status"] == "UNRESOLVED"
        assert view["world_reference"].get("canonical_id") is None
        assert view["availability"]["world_reference_resolved"] is False

    def test_world_ambiguous_not_resolved(self):
        from core.services.holistic_view import build_holistic_view

        card = _make_card_dict(book_claims=[_claim("x", "book:c1", "c1")])
        with _patched_components(card, world_ref=_world_ref(WorldReferenceStatus.AMBIGUOUS)):
            view = build_holistic_view("mirror")

        assert view["world_reference"]["status"] == "AMBIGUOUS"
        assert view["world_reference"].get("canonical_id") is None
        assert any("AMBIGUOUS" in lim or "неоднозначн" in lim.lower() for lim in view["limitations"])

    def test_temporal_resolved(self):
        from core.services.holistic_view import build_holistic_view

        card = _make_card_dict(book_claims=[_claim("x", "book:c1", "c1")])
        with _patched_components(card, temporal_ref=_temporal_ref(TemporalReferenceStatus.RESOLVED)):
            view = build_holistic_view("arkaim")

        assert view["temporal_reference"]["status"] == "RESOLVED"
        assert view["temporal_reference"]["temporal_node_id"] == "node_1"
        assert view["availability"]["temporal_reference_resolved"] is True

    def test_temporal_unknown(self):
        from core.services.holistic_view import build_holistic_view

        card = _make_card_dict(book_claims=[_claim("x", "book:c1", "c1")])
        with _patched_components(card, temporal_ref=_temporal_ref(TemporalReferenceStatus.UNKNOWN)):
            view = build_holistic_view("unknown_time")

        assert view["temporal_reference"]["status"] == "UNKNOWN"
        assert view["availability"]["temporal_reference_resolved"] is False
        assert any("temporal" in lim.lower() or "временн" in lim.lower() for lim in view["limitations"])


# ── Частичные данные и сбои ───────────────────────────────────────────


class TestHolisticViewPartialData:
    """Сценарий 8: частично отсутствующие данные, сбой компонента."""

    def test_evidence_failure_keeps_other_components(self):
        from core.services.holistic_view import build_holistic_view

        card = _make_card_dict(book_claims=[_claim("x", "book:c1", "c1")])

        from contextlib import contextmanager

        @contextmanager
        def _cm_with_evidence_error():
            mock_card = MagicMock()
            mock_card.to_dict.return_value = card
            mock_builder = MagicMock()
            mock_builder.build.return_value = mock_card
            with patch("knowledge_card.get_card_builder", return_value=mock_builder):
                with patch("knowledge.world_resolver.WorldKnowledgeResolver") as mock_wr:
                    mock_wr.return_value.resolve.return_value = _world_ref(WorldReferenceStatus.RESOLVED)
                    with patch("knowledge.temporal_resolver.KnowledgeTemporalResolver") as mock_tr:
                        mock_tr.return_value.resolve.return_value = _temporal_ref(TemporalReferenceStatus.RESOLVED)
                        with patch(
                            "core.routes.knowledge_cards._evidence_projection",
                            side_effect=RuntimeError("evidence down"),
                        ):
                            yield

        with _cm_with_evidence_error():
            view = build_holistic_view("partial")

        # Основные компоненты сохранились
        assert len(view["book_claims"]) == 1
        assert view["world_reference"]["status"] == "RESOLVED"
        assert view["temporal_reference"]["status"] == "RESOLVED"
        # Evidence — пустой, но не уронил ответ
        assert view["evidence"] == []
        assert view["availability"]["evidence"] is False

    def test_empty_entity_returns_view_with_limitations(self):
        from core.services.holistic_view import build_holistic_view

        card = _make_card_dict(book_claims=[], primary_entity=None)
        with _patched_components(card):
            view = build_holistic_view("nobody")

        assert view["view_type"] == "ENTITY_AGGREGATE"
        assert view["book_claims"] == []
        assert view["screenplay_claims"] == []
        assert len(view["limitations"]) > 0
        assert view["availability"]["book_claims"] is False


# ── Идентификаторы и provenance ───────────────────────────────────────


class TestHolisticViewIdentity:
    """Сценарий 9: сохранение идентификаторов, source_ref, provenance."""

    def test_source_refs_and_provenance_preserved(self):
        from core.services.holistic_view import build_holistic_view

        card = _make_card_dict(
            book_claims=[_claim("Книжный факт", "book:chunk_p_0042", "chunk_p_0042")],
            screenplay_claims=[_claim("Сценарная деталь", "screenplay:scene:scene_007")],
        )
        with _patched_components(card):
            view = build_holistic_view("identity_check")

        book = view["book_claims"][0]
        assert book["source_ref"] == "book:chunk_p_0042"
        assert book["provenance"]["category"] == "AUTHOR_CANON"

        scr = view["screenplay_claims"][0]
        assert scr["source_ref"] == "screenplay:scene:scene_007"
        # Сценарий не выдаётся за книгу: префикс сохраняется
        assert scr["source_ref"].startswith("screenplay:")

    def test_no_duplicate_independent_confirmations(self):
        """Один источник не размножается на несколько независимых подтверждений."""
        from core.services.holistic_view import build_holistic_view

        card = _make_card_dict(
            book_claims=[_claim("Один факт", "book:chunk_x", "chunk_x")],
        )
        with _patched_components(card):
            view = build_holistic_view("dedup")

        refs = [c["source_ref"] for c in view["book_claims"]]
        assert len(refs) == len(set(refs)), "дублирующиеся source_ref"


# ── Endpoint интеграция ───────────────────────────────────────────────


class TestHolisticEndpoint:
    """Сценарий 10: endpoint + обратная совместимость."""

    def _client(self) -> TestClient:
        from fastapi import FastAPI
        from core.routes import knowledge_cards as kc

        app = FastAPI()
        app.include_router(kc.router)
        checker = kc.router.dependencies[0].dependency
        app.dependency_overrides[checker] = lambda: {
            "user_id": "m15",
            "role": "reader",
            "provider": "test",
            "username": "m15",
            "display_name": "M15",
        }
        return TestClient(app)

    def test_holistic_endpoint_returns_view(self):
        client = self._client()
        response = client.get("/knowledge/cards/holistic/arkaim")

        assert response.status_code == 200
        data = response.json()
        assert data["view_type"] == "ENTITY_AGGREGATE"
        assert "book_claims" in data
        assert "screenplay_claims" in data
        assert "world_reference" in data
        assert "temporal_reference" in data
        assert "availability" in data
        assert "limitations" in data

    def test_holistic_endpoint_unknown_entity_no_404(self):
        client = self._client()
        response = client.get("/knowledge/cards/holistic/__no_such_entity_m15__")

        assert response.status_code == 200
        data = response.json()
        assert data["view_type"] == "ENTITY_AGGREGATE"
        assert len(data["limitations"]) > 0

    def test_trace_backward_compat_after_holistic_addition(self):
        """Добавление holistic не сломало trace."""
        client = self._client()
        response = client.get("/knowledge/cards/trace/arkaim")

        assert response.status_code == 200
        data = response.json()
        for key in ("entity_id", "status", "claims", "evidence", "world", "temporal"):
            assert key in data

    def test_card_backward_compat_after_holistic_addition(self):
        """Добавление holistic не сломало карточку."""
        client = self._client()
        response = client.get("/knowledge/cards/arkaim")

        # Может быть 200 или 404 в зависимости от данных, но не 500
        assert response.status_code in (200, 404)
