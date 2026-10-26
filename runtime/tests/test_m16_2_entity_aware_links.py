"""M16.2 — Entity-Aware Screenplay Links in Ask/RAG.

Проверяет, что одобренные M16.1 связи книга↔сценарий разрешаются в контексте
сущности по реальным book_chunk_id книжных claims — только при точном
совпадении идентификатора, без эвристик.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
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

# Одобренные M16.1 пары (реальные идентификаторы)
APPROVED_CHUNK_1 = "chunk_p_0010_77326a31efd2"  # -> scene_006
APPROVED_CHUNK_2 = "chunk_p_0047_387817db08e3"  # -> scene_021
APPROVED_CHUNK_3 = "chunk_p_0006_104f39f72f26"  # -> scene_003
NOT_APPROVED_CHUNK = "chunk_p_9999_deadbeefdead"


# ── Helpers ────────────────────────────────────────────────────────────


def _book_claim(chunk_id: str, text: str = "Книжный фрагмент") -> dict:
    return {
        "text": text,
        "source_ref": f"book:{chunk_id}",
        "chunk_id": chunk_id,
        "provenance": {"category": "AUTHOR_CANON", "confidence": 1.0},
    }


def _screenplay_claim(scene_id: str, text: str = "Сценарная деталь") -> dict:
    return {
        "text": text,
        "source_ref": f"screenplay:scene:{scene_id}",
        "provenance": {"category": "AUTHOR_CANON", "confidence": 1.0},
    }


def _card_dict(
    *,
    book_claims: list[dict] | None = None,
    screenplay_claims: list[dict] | None = None,
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
        "contradictions": [],
        "screenplay_links": screenplay_links or [],
    }


def _world_ref(status: WorldReferenceStatus = WorldReferenceStatus.UNRESOLVED):
    if status is WorldReferenceStatus.RESOLVED:
        return WorldEntityReference(
            query="q",
            canonical_id="canon_q",
            name="Канон",
            status=status,
            resolution_method="canonical_id",
        )
    return WorldEntityReference(query="q", status=status, resolution_method="none")


def _temporal_ref(status: TemporalReferenceStatus = TemporalReferenceStatus.UNKNOWN):
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


@contextmanager
def _patched_context(card_dict: dict):
    """Патчит builder и резолверы для gather_knowledge_core_context."""
    mock_card = MagicMock()
    mock_card.to_dict.return_value = card_dict
    mock_builder = MagicMock()
    mock_builder.build.return_value = mock_card
    with patch("knowledge_card.get_card_builder", return_value=mock_builder):
        with patch("knowledge.world_resolver.WorldKnowledgeResolver") as mock_wr:
            mock_wr.return_value.resolve.return_value = _world_ref()
            with patch("knowledge.temporal_resolver.KnowledgeTemporalResolver") as mock_tr:
                mock_tr.return_value.resolve.return_value = _temporal_ref()
                yield


def _context(card_dict: dict, entity_id: str = "test_entity"):
    from core.services.knowledge_core_context import gather_knowledge_core_context

    with _patched_context(card_dict):
        return gather_knowledge_core_context([{"entity_id": entity_id, "name": "Тест"}])


# ── Извлечение book_chunk_id ───────────────────────────────────────────


class TestBookChunkIdExtraction:
    """Извлечение реальных book_chunk_id из карточки."""

    def test_chunk_id_field_used(self):
        from core.services.knowledge_core_context import _book_chunk_ids_from_card

        card = _card_dict(book_claims=[_book_claim(APPROVED_CHUNK_1)])
        assert _book_chunk_ids_from_card(card) == [APPROVED_CHUNK_1]

    def test_source_ref_fallback(self):
        from core.services.knowledge_core_context import _book_chunk_ids_from_card

        claim = {
            "text": "x",
            "source_ref": f"book:{APPROVED_CHUNK_2}",
            "provenance": {"category": "AUTHOR_CANON", "confidence": 1.0},
        }
        card = _card_dict(book_claims=[claim])
        assert _book_chunk_ids_from_card(card) == [APPROVED_CHUNK_2]

    def test_placeholder_chunk_excluded(self):
        """Fallback 'chunk' без реального id отбрасывается."""
        from core.services.knowledge_core_context import _book_chunk_ids_from_card

        claim = {
            "text": "x",
            "source_ref": "book:chunk",
            "provenance": {"category": "AUTHOR_CANON", "confidence": 1.0},
        }
        card = _card_dict(book_claims=[claim])
        assert _book_chunk_ids_from_card(card) == []

    def test_non_book_sources_ignored(self):
        """Claims из genome/screenplay не считаются книжными."""
        from core.services.knowledge_core_context import _book_chunk_ids_from_card

        card = {
            "sources": [
                {
                    "source_name": "genome",
                    "claims": [_book_claim(APPROVED_CHUNK_1)],
                },
                {
                    "source_name": "screenplay",
                    "claims": [_book_claim(APPROVED_CHUNK_2)],
                },
            ]
        }
        assert _book_chunk_ids_from_card(card) == []

    def test_duplicate_chunk_ids_deduplicated(self):
        from core.services.knowledge_core_context import _book_chunk_ids_from_card

        card = _card_dict(
            book_claims=[
                _book_claim(APPROVED_CHUNK_1),
                _book_claim(APPROVED_CHUNK_1, text="другой текст"),
            ]
        )
        assert _book_chunk_ids_from_card(card) == [APPROVED_CHUNK_1]


# ── Разрешение связей в контексте сущности ─────────────────────────────


class TestEntityContextLinks:
    """Контекст сущности получает/не получает одобренные связи."""

    def test_link_resolved_via_book_claim_chunk_id(self):
        """Книжный claim с одобренным chunk_id → связь в контексте."""
        contexts = _context(
            _card_dict(
                book_claims=[_book_claim(APPROVED_CHUNK_1)],
                screenplay_claims=[_screenplay_claim("scene_006")],
            )
        )

        assert len(contexts) == 1
        links = contexts[0]["screenplay_links"]
        assert len(links) == 1
        assert links[0]["screenplay_scene_id"] == "scene_006"
        assert links[0]["book_chunk_id"] == APPROVED_CHUNK_1
        assert links[0]["confidence"] == 1.0
        assert links[0]["notes"]

    def test_no_link_for_unapproved_chunk(self):
        """Книжный claim с неодобренным chunk_id → связи нет."""
        contexts = _context(
            _card_dict(
                book_claims=[_book_claim(NOT_APPROVED_CHUNK)],
                screenplay_claims=[_screenplay_claim("scene_000")],
            )
        )

        assert len(contexts) == 1
        assert contexts[0]["screenplay_links"] == []

    def test_no_link_without_book_claims(self):
        """Без книжных claims связь не создаётся."""
        contexts = _context(_card_dict(screenplay_claims=[_screenplay_claim("scene_006")]))

        assert len(contexts) == 1
        assert contexts[0]["screenplay_links"] == []

    def test_multiple_chunks_resolve_deterministically(self):
        """Несколько одобренных фрагментов → несколько связей, без дублей."""
        card = _card_dict(
            book_claims=[
                _book_claim(APPROVED_CHUNK_1),
                _book_claim(APPROVED_CHUNK_2),
                _book_claim(APPROVED_CHUNK_3),
            ]
        )

        contexts_first = _context(card)
        contexts_second = _context(card)

        links = contexts_first[0]["screenplay_links"]
        pairs = [(link["screenplay_scene_id"], link["book_chunk_id"]) for link in links]
        assert pairs == [
            ("scene_006", APPROVED_CHUNK_1),
            ("scene_021", APPROVED_CHUNK_2),
            ("scene_003", APPROVED_CHUNK_3),
        ]
        # Детерминизм: повторный сбор даёт тот же порядок
        pairs_second = [(link["screenplay_scene_id"], link["book_chunk_id"]) for link in contexts_second[0]["screenplay_links"]]
        assert pairs_second == pairs

    def test_entity_level_link_deduplicated_with_chunk_match(self):
        """Связь уровня entity_id и совпадение по chunk_id не дублируются."""
        entity_link = {
            "screenplay_scene_id": "scene_006",
            "book_chunk_id": APPROVED_CHUNK_1,
            "confidence": 1.0,
            "notes": "уровень entity",
        }
        contexts = _context(
            _card_dict(
                book_claims=[_book_claim(APPROVED_CHUNK_1)],
                screenplay_links=[entity_link],
            )
        )

        links = contexts[0]["screenplay_links"]
        pairs = [(link["screenplay_scene_id"], link["book_chunk_id"]) for link in links]
        assert pairs == [("scene_006", APPROVED_CHUNK_1)]
        assert len(pairs) == len(set(pairs))

    def test_unrelated_entity_gets_no_foreign_scene_materials(self):
        """Сущность без своих одобренных фрагментов не получает чужие сцены."""
        contexts = _context(
            _card_dict(
                book_claims=[_book_claim(NOT_APPROVED_CHUNK)],
                screenplay_claims=[],
            )
        )

        assert contexts[0]["screenplay_links"] == []

    def test_source_refs_and_provenance_preserved(self):
        """Книжный и сценарный claims сохраняют source_ref и provenance."""
        contexts = _context(
            _card_dict(
                book_claims=[_book_claim(APPROVED_CHUNK_1)],
                screenplay_claims=[_screenplay_claim("scene_006")],
            )
        )
        ctx = contexts[0]

        book = ctx["book_claims"][0]
        assert book["source_ref"] == f"book:{APPROVED_CHUNK_1}"
        assert book["provenance"]["category"] == "AUTHOR_CANON"

        scr = ctx["screenplay_claims"][0]
        assert scr["source_ref"] == "screenplay:scene:scene_006"
        assert scr["provenance"]["category"] == "AUTHOR_CANON"

    def test_screenplay_not_independent_book_confirmation(self):
        """Сценарный claim не маскируется под книжное подтверждение."""
        contexts = _context(
            _card_dict(
                book_claims=[_book_claim(APPROVED_CHUNK_1)],
                screenplay_claims=[_screenplay_claim("scene_006")],
            )
        )
        ctx = contexts[0]

        for claim in ctx["screenplay_claims"]:
            assert claim["source_ref"].startswith("screenplay:")
        for claim in ctx["book_claims"]:
            assert claim["source_ref"].startswith("book:")


# ── Ask route интеграция ───────────────────────────────────────────────


class TestAskRouteEntityAwareLinks:
    """POST /book/ask передаёт одобренные связи через knowledge_core."""

    def test_ask_knowledge_core_includes_link_via_book_chunk(self):
        """Ask: сущность с одобренным фрагментом → связь в knowledge_core."""
        from unittest.mock import AsyncMock

        from core.adc_deps import get_keeper, get_event_logger
        from core.main import app

        card_dict = _card_dict(
            book_claims=[_book_claim(APPROVED_CHUNK_1)],
            screenplay_claims=[_screenplay_claim("scene_006")],
        )
        mock_card = MagicMock()
        mock_card.to_dict.return_value = card_dict
        mock_builder = MagicMock()
        mock_builder.build.return_value = mock_card

        keeper_result = {
            "answer": "Ответ",
            "source": "pulse",
            "provenance": [],
            "related_entities": [{"entity_id": "entity_with_chunk", "name": "Сущ"}],
        }
        mock_keeper = MagicMock()
        mock_keeper.act = AsyncMock(return_value=keeper_result)
        app.dependency_overrides[get_keeper] = lambda: mock_keeper

        mock_logger = MagicMock()
        app.dependency_overrides[get_event_logger] = lambda: mock_logger

        with patch("knowledge_card.get_card_builder", return_value=mock_builder):
            with patch("knowledge.world_resolver.WorldKnowledgeResolver") as mock_wr:
                mock_wr.return_value.resolve.return_value = _world_ref()
                with patch("knowledge.temporal_resolver.KnowledgeTemporalResolver") as mock_tr:
                    mock_tr.return_value.resolve.return_value = _temporal_ref()
                    with patch(
                        "core.routes.book._resolve_related_entities",
                        return_value=([{"entity_id": "entity_with_chunk", "name": "Сущ"}], {}),
                    ):
                        client = TestClient(app)
                        response = client.post("/book/ask", json={"question": "Что такое Аркаим?"})

        assert response.status_code == 200
        payload = response.json()["data"]
        knowledge_core = payload["knowledge_core"]
        assert len(knowledge_core) == 1
        ctx = knowledge_core[0]
        assert len(ctx["screenplay_links"]) == 1
        assert ctx["screenplay_links"][0]["screenplay_scene_id"] == "scene_006"
        assert ctx["screenplay_links"][0]["book_chunk_id"] == APPROVED_CHUNK_1
        # Раздельные source_ref
        assert ctx["book_claims"][0]["source_ref"] == f"book:{APPROVED_CHUNK_1}"
        assert ctx["screenplay_claims"][0]["source_ref"] == "screenplay:scene:scene_006"

    def test_ask_knowledge_core_no_link_for_unapproved(self):
        """Ask: сущность без одобренного фрагмента → screenplay_links пуст."""
        from unittest.mock import AsyncMock

        from core.adc_deps import get_keeper, get_event_logger
        from core.main import app

        card_dict = _card_dict(
            book_claims=[_book_claim(NOT_APPROVED_CHUNK)],
            screenplay_claims=[_screenplay_claim("scene_000")],
        )
        mock_card = MagicMock()
        mock_card.to_dict.return_value = card_dict
        mock_builder = MagicMock()
        mock_builder.build.return_value = mock_card

        keeper_result = {
            "answer": "Ответ",
            "source": "pulse",
            "provenance": [],
            "related_entities": [{"entity_id": "entity_without_chunk", "name": "Сущ"}],
        }
        mock_keeper = MagicMock()
        mock_keeper.act = AsyncMock(return_value=keeper_result)
        app.dependency_overrides[get_keeper] = lambda: mock_keeper

        mock_logger = MagicMock()
        app.dependency_overrides[get_event_logger] = lambda: mock_logger

        with patch("knowledge_card.get_card_builder", return_value=mock_builder):
            with patch("knowledge.world_resolver.WorldKnowledgeResolver") as mock_wr:
                mock_wr.return_value.resolve.return_value = _world_ref()
                with patch("knowledge.temporal_resolver.KnowledgeTemporalResolver") as mock_tr:
                    mock_tr.return_value.resolve.return_value = _temporal_ref()
                    with patch(
                        "core.routes.book._resolve_related_entities",
                        return_value=([{"entity_id": "entity_without_chunk", "name": "Сущ"}], {}),
                    ):
                        client = TestClient(app)
                        response = client.post("/book/ask", json={"question": "Что-то"})

        assert response.status_code == 200
        payload = response.json()["data"]
        knowledge_core = payload["knowledge_core"]
        assert len(knowledge_core) == 1
        assert knowledge_core[0]["screenplay_links"] == []


# ── Holistic View интеграция ───────────────────────────────────────────


class TestHolisticViewEntityAwareLinks:
    """Holistic View (через тот же context-сервис) получает связи."""

    def test_holistic_view_resolves_link_via_book_chunk(self):
        from core.services.holistic_view import build_holistic_view

        card_dict = _card_dict(
            book_claims=[_book_claim(APPROVED_CHUNK_2)],
            screenplay_claims=[_screenplay_claim("scene_021")],
        )
        mock_card = MagicMock()
        mock_card.to_dict.return_value = card_dict
        mock_builder = MagicMock()
        mock_builder.build.return_value = mock_card

        with patch("knowledge_card.get_card_builder", return_value=mock_builder):
            with patch("knowledge.world_resolver.WorldKnowledgeResolver") as mock_wr:
                mock_wr.return_value.resolve.return_value = _world_ref()
                with patch("knowledge.temporal_resolver.KnowledgeTemporalResolver") as mock_tr:
                    mock_tr.return_value.resolve.return_value = _temporal_ref()
                    with patch(
                        "core.routes.knowledge_cards._evidence_projection",
                        return_value=[],
                    ):
                        view = build_holistic_view("entity_x", "Сущ")

        assert len(view["screenplay_links"]) == 1
        assert view["screenplay_links"][0]["screenplay_scene_id"] == "scene_021"
        assert view["screenplay_links"][0]["book_chunk_id"] == APPROVED_CHUNK_2
        assert view["availability"]["screenplay_links"] is True
