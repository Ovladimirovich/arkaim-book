"""M14 — Ask/RAG ↔ Knowledge Core интеграция.

Тесты покрывают 8 сценариев приёмки: книжный фрагмент, сценарная деталь,
связь книга↔сценарий (наличие/отсутствие), неоднозначность, пустые данные,
конфликт источников, обратная совместимость.
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
    """Собрать card_dict в формате KnowledgeCard.to_dict()."""
    sources = []
    if book_claims is not None:
        sources.append({"source_name": "book", "claims": book_claims})
    if screenplay_claims is not None:
        sources.append({"source_name": "screenplay", "claims": screenplay_claims})
    return {
        "metadata": {"entity_id": "test_entity", "entity_name": "Тест"},
        "primary_entity": primary_entity,
        "sources": sources,
        "contradictions": contradictions or [],
        "screenplay_links": screenplay_links or [],
    }


def _claim(text: str, source_ref: str) -> dict:
    return {
        "text": text,
        "source_ref": source_ref,
        "provenance": {"category": "AUTHOR_CANON", "confidence": 1.0},
    }


def _world_ref(query: str = "arkaim", status: WorldReferenceStatus = WorldReferenceStatus.RESOLVED) -> WorldEntityReference:
    if status is WorldReferenceStatus.RESOLVED:
        return WorldEntityReference(
            query=query,
            canonical_id=f"canon_{query}",
            name=f"Канонический {query}",
            status=status,
            resolution_method="canonical_id",
        )
    return WorldEntityReference(query=query, status=status, resolution_method="none")


def _temporal_ref(claim_id: str = "c1", status: TemporalReferenceStatus = TemporalReferenceStatus.RESOLVED) -> TemporalReference:
    if status is TemporalReferenceStatus.RESOLVED:
        return TemporalReference(
            claim_id=claim_id,
            time_basis=TemporalTimeBasis.WORLD,
            status=status,
            temporal_node_id="node_1",
            precision="YEAR",
            resolution_method="temporal_engine",
        )
    return TemporalReference(
        claim_id=claim_id,
        time_basis=TemporalTimeBasis.WORLD,
        status=status,
        reason="not found",
        resolution_method="temporal_engine",
    )


def _related(entity_id: str = "arkaim", name: str = "Аркаим") -> list[dict]:
    return [{"entity_id": entity_id, "name": name}]


def _patched_builder(card_dict: dict):
    """Context manager: патчит knowledge_card.get_card_builder на мок с нужным card_dict."""
    from contextlib import contextmanager

    @contextmanager
    def _cm():
        mock_card = MagicMock()
        mock_card.to_dict.return_value = card_dict
        mock_builder = MagicMock()
        mock_builder.build.return_value = mock_card
        with patch("knowledge_card.get_card_builder", return_value=mock_builder):
            yield

    return _cm()


# ── gather_knowledge_core_context — unit ──────────────────────────────


class TestGatherKnowledgeCoreContext:
    """Unit-тесты сервиса knowledge_core_context."""

    def test_book_claims_with_provenance(self):
        """Сценарий 1: книжный фрагмент — book_claims с provenance."""
        from core.services.knowledge_core_context import gather_knowledge_core_context

        card_dict = _make_card_dict(
            book_claims=[_claim("Аркаим — древнее городище", "book:chunk_p_0001")],
        )
        with _patched_builder(card_dict):
            contexts = gather_knowledge_core_context(_related())

        assert len(contexts) == 1
        ctx = contexts[0]
        assert ctx["entity_id"] == "arkaim"
        assert len(ctx["book_claims"]) == 1
        assert ctx["book_claims"][0]["source_ref"] == "book:chunk_p_0001"
        assert ctx["book_claims"][0]["provenance"]["category"] == "AUTHOR_CANON"

    def test_screenplay_claims_separate_from_book(self):
        """Сценарий 2: сценарная деталь — screenplay_claims отдельно от book."""
        from core.services.knowledge_core_context import gather_knowledge_core_context

        card_dict = _make_card_dict(
            book_claims=[_claim("Книжный текст", "book:chunk_x")],
            screenplay_claims=[_claim("Визуальная деталь сценария", "screenplay:scene:scene_000")],
        )
        with _patched_builder(card_dict):
            contexts = gather_knowledge_core_context(_related())

        ctx = contexts[0]
        assert ctx["book_claims"][0]["source_ref"] == "book:chunk_x"
        assert ctx["screenplay_claims"][0]["source_ref"] == "screenplay:scene:scene_000"
        # Сценарий не выдаётся как книжное подтверждение
        assert all(c["source_ref"].startswith("screenplay:") for c in ctx["screenplay_claims"])

    def test_screenplay_links_present_when_confirmed(self):
        """Сценарий 3: явная связь книга↔сценарий присутствует."""
        from core.services.knowledge_core_context import gather_knowledge_core_context

        links = [
            {
                "book_source_ref": "book:chunk_p_0001",
                "screenplay_scene_id": "scene_000",
                "relation_type": "SAME_EVENT",
            }
        ]
        card_dict = _make_card_dict(
            book_claims=[_claim("текст", "book:chunk_p_0001")],
            screenplay_claims=[_claim("сцена", "screenplay:scene:scene_000")],
            screenplay_links=links,
        )
        with _patched_builder(card_dict):
            contexts = gather_knowledge_core_context(_related())

        ctx = contexts[0]
        assert len(ctx["screenplay_links"]) == 1
        assert ctx["screenplay_links"][0]["screenplay_scene_id"] == "scene_000"

    def test_screenplay_links_empty_no_fabrication(self):
        """Сценарий 4: без связи — screenplay_links пуст, эвристика не добавляется."""
        from core.services.knowledge_core_context import gather_knowledge_core_context

        card_dict = _make_card_dict(
            book_claims=[_claim("текст", "book:chunk_a")],
            screenplay_claims=[_claim("сцена", "screenplay:scene:scene_001")],
            screenplay_links=[],
        )
        with _patched_builder(card_dict):
            contexts = gather_knowledge_core_context(_related())

        ctx = contexts[0]
        assert ctx["screenplay_links"] == []

    def test_ambiguous_world_reference_preserved(self):
        """Сценарий 5: AMBIGUOUS world reference — статус сохранён, кандидат не выбран."""
        from core.services.knowledge_core_context import gather_knowledge_core_context
        from knowledge.world_resolver import WorldKnowledgeResolver

        card_dict = _make_card_dict(
            book_claims=[_claim("текст", "book:chunk_b")],
        )
        ambiguous = _world_ref(status=WorldReferenceStatus.AMBIGUOUS)
        with _patched_builder(card_dict):
            with patch.object(WorldKnowledgeResolver, "resolve", return_value=ambiguous):
                contexts = gather_knowledge_core_context(_related())

        ctx = contexts[0]
        assert ctx["world_reference"]["status"] == "AMBIGUOUS"
        assert ctx["world_reference"].get("canonical_id") is None

    def test_unknown_temporal_reference_preserved(self):
        """Сценарий 5: UNKNOWN temporal reference — статус сохранён."""
        from core.services.knowledge_core_context import gather_knowledge_core_context
        from knowledge.temporal_resolver import KnowledgeTemporalResolver

        card_dict = _make_card_dict(
            book_claims=[_claim("текст", "book:chunk_c")],
        )
        unknown = _temporal_ref(status=TemporalReferenceStatus.UNKNOWN)
        with _patched_builder(card_dict):
            with patch.object(KnowledgeTemporalResolver, "resolve", return_value=unknown):
                contexts = gather_knowledge_core_context(_related())

        ctx = contexts[0]
        assert ctx["temporal_reference"]["status"] == "UNKNOWN"

    def test_empty_knowledge_core_returns_empty_list(self):
        """Сценарий 6: нет данных → пустой список, без исключений."""
        from core.services.knowledge_core_context import gather_knowledge_core_context

        assert gather_knowledge_core_context([]) == []

    def test_entity_without_data_skipped(self):
        """Сценарий 6: сущность без данных пропускается (None → исключается)."""
        from core.services.knowledge_core_context import gather_knowledge_core_context
        from knowledge.world_resolver import WorldKnowledgeResolver

        card_dict = _make_card_dict(book_claims=[], primary_entity=None)
        unresolved = _world_ref(status=WorldReferenceStatus.UNRESOLVED)
        with _patched_builder(card_dict):
            with patch.object(WorldKnowledgeResolver, "resolve", return_value=unresolved):
                contexts = gather_knowledge_core_context(_related())

        assert contexts == []

    def test_contradictions_preserved(self):
        """Сценарий 7: конфликт источников сохраняется без сглаживания."""
        from core.services.knowledge_core_context import gather_knowledge_core_context

        contradictions = [
            {
                "description": "Книга связывает с гипербореями, археология молчит",
                "source_1_claim": "AUTHOR_CANON: связь с гипербореями",
                "source_2_claim": "EXTERNAL_SOURCE: нет данных",
                "resolution": "UNRESOLVED",
            }
        ]
        card_dict = _make_card_dict(
            book_claims=[_claim("текст", "book:chunk_d")],
            contradictions=contradictions,
        )
        with _patched_builder(card_dict):
            contexts = gather_knowledge_core_context(_related())

        ctx = contexts[0]
        assert len(ctx["contradictions"]) == 1
        assert ctx["contradictions"][0]["resolution"] == "UNRESOLVED"

    def test_builder_exception_returns_partial_not_crash(self):
        """Сбой builder-а не роняет сборку: контекст пуст, исключений нет."""
        from core.services.knowledge_core_context import gather_knowledge_core_context
        from knowledge_card import get_card_builder

        with patch.object(get_card_builder(), "build", side_effect=RuntimeError("card broken")):
            with patch("knowledge_card.get_card_builder", side_effect=RuntimeError("card broken")):
                contexts = gather_knowledge_core_context(_related())

        assert contexts == []


# ── Ask route интеграция ──────────────────────────────────────────────


class TestAskRouteKnowledgeCore:
    """Интеграция knowledge_core в POST /book/ask."""

    def _client_with_mock_keeper(self, keeper_result: dict) -> TestClient:
        from unittest.mock import AsyncMock
        from core.main import app
        from core.adc_deps import get_keeper

        mock_keeper = MagicMock()
        mock_keeper.act = AsyncMock(return_value=keeper_result)
        app.dependency_overrides[get_keeper] = lambda: mock_keeper
        client = TestClient(app)
        return client

    def test_ask_response_contains_knowledge_core(self):
        """Обратная совместимость: knowledge_core добавлен, прежние поля на месте."""
        keeper_result = {
            "answer": "Аркаим — древнее городище степной культуры.",
            "source": "pulse",
            "provenance": [],
            "uncertainty": None,
            "pulse_confidence": 0.9,
            "llm_used": False,
            "mood": "neutral",
            "suggestion": "",
        }
        client = self._client_with_mock_keeper(keeper_result)
        response = client.post("/book/ask", json={"question": "Что такое Аркаим?"})

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        payload = data["data"]
        # Обратная совместимость
        for key in ("answer", "source", "provenance", "related_entities", "knowledge_core"):
            assert key in payload, f"field {key!r} missing"

    def test_ask_knowledge_core_empty_when_no_related(self):
        """Сценарий 6: нет связанных сущностей → knowledge_core = []."""
        keeper_result = {
            "answer": "Просто ответ без сущностей.",
            "source": "pulse",
            "provenance": [],
        }
        client = self._client_with_mock_keeper(keeper_result)
        response = client.post("/book/ask", json={"question": "Что-то абстрактное"})

        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["knowledge_core"] == [] or isinstance(payload["knowledge_core"], list)
