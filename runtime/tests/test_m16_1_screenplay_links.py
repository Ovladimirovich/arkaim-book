"""M16.1 — Initial verified screenplay links.

Проверяет четырнадцать одобренных OWNER связей (M16.1 + M20.1), их
разрешение во всех потребителях (Knowledge Card, Holistic View, Knowledge
Core контекст), отсутствие неодобренных пар и сохранение раздельных
source_ref/provenance.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from unittest.mock import MagicMock, patch

_CORE = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from knowledge.screenplay_linker import ScreenplayBookLinker

# Четырнадцать одобренных пар (OWNER-GO M16.1 + M20.1)
APPROVED_PAIRS: set[tuple[str, str]] = {
    ("scene_003", "chunk_p_0006_104f39f72f26"),
    ("scene_004", "chunk_p_0007_b812dfae0ff4"),
    ("scene_006", "chunk_p_0010_77326a31efd2"),
    ("scene_009", "chunk_p_0018_89a09e6d3d55"),
    ("scene_014", "chunk_p_0027_4c6873e98b66"),
    ("scene_019", "chunk_p_0043_a5a83219bbd8"),
    ("scene_020", "chunk_p_0045_bc4a72fed70b"),
    ("scene_020", "chunk_p_0046_407df13f675f"),
    ("scene_021", "chunk_p_0047_387817db08e3"),
    ("scene_022", "chunk_p_0048_bbe88490fb62"),
    ("scene_027", "chunk_p_0049_9d39268ad94c"),
    ("scene_047", "chunk_p_0102_1d2e617e135e"),
    ("scene_086", "chunk_p_0570_e94101594d2f"),
    ("scene_117", "chunk_p_0799_57e67fec2309"),
}

# Средние пары и смежные чанки из M16 — не должны появиться в файле
NOT_APPROVED_PAIRS: set[tuple[str, str]] = {
    ("scene_000", "chunk_p_0006_104f39f72f26"),
    ("scene_046", "chunk_p_0099_112db5fa05bb"),
    ("scene_091", "chunk_p_0600_600ddcaafccd"),
    ("scene_065", "chunk_p_0381_98c1b23f000e"),
    ("scene_106", "chunk_p_0664_a90db57346ae"),
    ("scene_052", "chunk_p_0155_cf45bf4c6fd3"),
    ("scene_055", "chunk_p_0268_9513def4ea78"),
    ("scene_074", "chunk_p_0440_fd68ae90d4dc"),
    ("scene_075", "chunk_p_0447_9db3b67dac42"),
    ("scene_113", "chunk_p_0760_d90a20222d30"),
    ("scene_047", "chunk_p_0101_fd403ea3a5ef"),
    ("scene_047", "chunk_p_0103_4344cb854696"),
    ("scene_014", "chunk_p_0028_2cf93350c161"),
    ("scene_014", "chunk_p_0026_d96af76a18f5"),
}


def _book_result(text="Книжный фрагмент", chunk_id="chunk_p_0010_77326a31efd2"):
    return {
        "text": text,
        "source": "book",
        "chunk_id": chunk_id,
        "metadata": {"chunk_id": chunk_id, "source": "book"},
        "chapter_title": "Пролог",
    }


def _screenplay_result(scene_id="scene_006"):
    return {
        "text": "Сценарная сцена",
        "source": "screenplay",
        "chunk_id": f"{scene_id}_abc123",
        "metadata": {
            "chunk_id": f"{scene_id}_abc123",
            "source": "screenplay",
            "scene_id": scene_id,
            "scene_title": "7. INT. ПЕЩЕРА",
            "location": "ПЕЩЕРА",
            "scene_type": "INT",
        },
    }


def _make_builder(book_results=None, screenplay_results=None):
    from knowledge_card import KnowledgeCardBuilder

    retriever = MagicMock()
    all_results = []
    all_results.extend(book_results or [])
    all_results.extend(screenplay_results or [])
    retriever.search = MagicMock(return_value=all_results)
    builder = KnowledgeCardBuilder()
    builder._retriever_or_none = MagicMock(return_value=retriever)
    return builder


# ── Загрузка одобренных связей ─────────────────────────────────────────


class TestApprovedLinksLoad:
    """Все четырнадцать одобренных связей загружаются и разрешаются."""

    def test_all_fourteen_links_load_and_resolve(self):
        linker = ScreenplayBookLinker.from_json()

        assert len(linker.links) == 14
        for scene_id, chunk_id in APPROVED_PAIRS:
            scene_links = linker.get_links_for_scene(scene_id)
            matching = [link for link in scene_links if link.book_chunk_id == chunk_id]
            assert len(matching) == 1, f"{scene_id}→{chunk_id}: ожидалась ровно 1 связь"
            assert matching[0].confidence == 1.0
            assert matching[0].notes, f"{scene_id}: обоснование отсутствует"
            chunk_links = linker.get_links_for_chunk(chunk_id)
            assert any(link.screenplay_scene_id == scene_id for link in chunk_links)

    def test_exact_pair_set_no_extras(self):
        """В файле ровно четырнадцать одобренных пар, без лишних."""
        linker = ScreenplayBookLinker.from_json()
        actual = {(link.screenplay_scene_id, link.book_chunk_id) for link in linker.links}
        assert actual == APPROVED_PAIRS

    def test_non_approved_pairs_absent(self):
        """Средние пары и смежные чанки из M16 не появились автоматически."""
        linker = ScreenplayBookLinker.from_json()
        actual = {(link.screenplay_scene_id, link.book_chunk_id) for link in linker.links}
        for pair in NOT_APPROVED_PAIRS:
            assert pair not in actual, f"неодобренная пара попала в файл: {pair}"

    def test_no_duplicate_pairs(self):
        linker = ScreenplayBookLinker.from_json()
        pairs = [(link.screenplay_scene_id, link.book_chunk_id) for link in linker.links]
        assert len(pairs) == len(set(pairs)), "дублирующиеся пары"

    def test_scene_ids_stable_not_visible_numbers(self):
        """Идентификаторы — стабильные scene_id/chunk_id, не видимые номера."""
        linker = ScreenplayBookLinker.from_json()
        for link in linker.links:
            assert re.fullmatch(r"scene_\d{3}", link.screenplay_scene_id)
            assert re.fullmatch(r"chunk_p_\d{4}_[0-9a-f]{12}", link.book_chunk_id)

    def test_notes_state_text_match_not_event_identity(self):
        """Обоснование отличает текстовое соответствие от идентичности событий."""
        linker = ScreenplayBookLinker.from_json()
        for link in linker.links:
            assert "Дословная цитата" in link.notes
            assert "не утверждение о полной идентичности" in link.notes


# ── Безопасность загрузчика ────────────────────────────────────────────


class TestLoaderSafety:
    """Несуществующие идентификаторы и дубли обрабатываются безопасно."""

    def test_nonexistent_identifiers_safe(self):
        linker = ScreenplayBookLinker.from_json()

        assert linker.get_links_for_scene("scene_999") == []
        assert linker.get_links_for_chunk("chunk_p_9999_deadbeefdead") == []
        assert linker.get_links_for_entity("nonexistent_entity") == []

    def test_shared_chunk_mechanism_separate_justifications(self):
        """Несколько сцен на один чанк — только при отдельном обосновании каждой."""
        links_data = [
            {
                "screenplay_scene_id": "scene_a",
                "book_chunk_id": "chunk_shared",
                "confidence": 1.0,
                "notes": "Основание A",
            },
            {
                "screenplay_scene_id": "scene_b",
                "book_chunk_id": "chunk_shared",
                "confidence": 1.0,
                "notes": "Основание B",
            },
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(links_data, f)
            temp_path = Path(f.name)

        linker = ScreenplayBookLinker.from_json(temp_path)
        chunk_links = linker.get_links_for_chunk("chunk_shared")

        assert len(chunk_links) == 2
        assert chunk_links[0].notes != chunk_links[1].notes
        temp_path.unlink()

    def test_real_file_shared_chunks_have_notes(self):
        """В реальном файле: если чанк разделяется — notes у каждой записи."""
        linker = ScreenplayBookLinker.from_json()
        by_chunk: dict[str, list] = defaultdict(list)
        for link in linker.links:
            by_chunk[link.book_chunk_id].append(link)
        for chunk_id, links in by_chunk.items():
            if len(links) > 1:
                assert all(link.notes for link in links), f"чанк {chunk_id} разделяется без обоснования у каждой связи"


# ── Интеграция: Knowledge Card ─────────────────────────────────────────


class TestCardIntegration:
    """Knowledge Card показывает одобренные связи с раздельными source_ref."""

    def test_card_builder_resolves_approved_link(self):
        builder = _make_builder()
        links = type(builder)._screenplay_links("chunk_p_0010_77326a31efd2")

        assert len(links) == 1
        assert links[0]["screenplay_scene_id"] == "scene_006"
        assert links[0]["book_chunk_id"] == "chunk_p_0010_77326a31efd2"
        assert links[0]["confidence"] == 1.0

    def test_card_shows_link_with_separate_source_refs(self):
        builder = _make_builder(
            book_results=[_book_result()],
            screenplay_results=[_screenplay_result("scene_006")],
        )
        card = builder.build("chunk_p_0010_77326a31efd2")

        assert len(card.screenplay_links) == 1
        assert card.screenplay_links[0]["screenplay_scene_id"] == "scene_006"

        book_source = next(s for s in card.sources if s.source_name == "book")
        screenplay_source = next(s for s in card.sources if s.source_name == "screenplay")
        assert all(c.source_ref.startswith("book:") for c in book_source.claims)
        assert all(c.source_ref.startswith("screenplay:scene:") for c in screenplay_source.claims)

    def test_screenplay_not_presented_as_book_confirmation(self):
        """Сценарий не представляется независимым подтверждением книги."""
        from narrative_engine.source_levels import ProvenanceCategory

        builder = _make_builder(
            book_results=[_book_result()],
            screenplay_results=[_screenplay_result("scene_006")],
        )
        card = builder.build("chunk_p_0010_77326a31efd2")

        screenplay_source = next(s for s in card.sources if s.source_name == "screenplay")
        for claim in screenplay_source.claims:
            assert claim.source_ref.startswith("screenplay:")
            assert claim.provenance.category == ProvenanceCategory.AUTHOR_CANON
            # Сценарный claim не маскируется под книжный
            assert not claim.source_ref.startswith("book:")

    def test_unlinked_entity_gets_no_links(self):
        builder = _make_builder()
        links = type(builder)._screenplay_links("chunk_p_9999_deadbeefdead")
        assert links == []


# ── Интеграция: Holistic View ──────────────────────────────────────────


class TestHolisticViewIntegration:
    """Holistic View показывает одобренные связи."""

    def _view_for(self, entity_id: str, book_chunk_id: str = "chunk_p_0010_77326a31efd2"):
        from contextlib import contextmanager

        from core.services.holistic_view import build_holistic_view

        @contextmanager
        def _cm():
            builder = _make_builder(
                book_results=[_book_result(chunk_id=book_chunk_id)],
                screenplay_results=[_screenplay_result("scene_006")],
            )
            mock_card = MagicMock()
            mock_card.to_dict.return_value = builder.build(entity_id).to_dict()
            mock_builder = MagicMock()
            mock_builder.build.return_value = mock_card
            with patch("knowledge_card.get_card_builder", return_value=mock_builder):
                with patch("knowledge.world_resolver.WorldKnowledgeResolver") as mock_wr:
                    from schemas.world_reference import WorldReferenceStatus

                    mock_wr.return_value.resolve.return_value = MagicMock(
                        model_dump=lambda mode="json": {
                            "query": entity_id,
                            "status": WorldReferenceStatus.UNRESOLVED.value,
                            "resolution_method": "none",
                        }
                    )
                    with patch("knowledge.temporal_resolver.KnowledgeTemporalResolver") as mock_tr:
                        from schemas.temporal_reference import TemporalReferenceStatus

                        mock_tr.return_value.resolve.return_value = MagicMock(
                            model_dump=lambda mode="json": {
                                "claim_id": entity_id,
                                "time_basis": "WORLD_TIME",
                                "status": TemporalReferenceStatus.UNKNOWN.value,
                                "resolution_method": "none",
                            }
                        )
                        with patch(
                            "core.routes.knowledge_cards._evidence_projection",
                            return_value=[],
                        ):
                            yield

        with _cm():
            return build_holistic_view(entity_id, "Проверка")

    def test_holistic_view_shows_approved_link(self):
        view = self._view_for("chunk_p_0010_77326a31efd2")

        assert len(view["screenplay_links"]) == 1
        assert view["screenplay_links"][0]["screenplay_scene_id"] == "scene_006"
        assert view["availability"]["screenplay_links"] is True

    def test_holistic_view_keeps_source_refs_separate(self):
        view = self._view_for("chunk_p_0010_77326a31efd2")

        for claim in view["book_claims"]:
            assert claim["source_ref"].startswith("book:")
        for claim in view["screenplay_claims"]:
            assert claim["source_ref"].startswith("screenplay:")

    def test_holistic_view_unlinked_entity_no_fabrication(self):
        # M16.2: книжный claim с неодобренным chunk_id не даёт связи
        view = self._view_for(
            "chunk_p_9999_deadbeefdead",
            book_chunk_id="chunk_p_9999_deadbeefdead",
        )

        assert view["screenplay_links"] == []
        assert view["availability"]["screenplay_links"] is False


# ── Интеграция: Knowledge Core контекст (Ask/RAG) ──────────────────────


class TestKnowledgeCoreContextIntegration:
    """Knowledge Core контекст (Ask/RAG) показывает одобренные связи."""

    def _context_for(self, entity_id: str, book_chunk_id: str = "chunk_p_0010_77326a31efd2"):
        from contextlib import contextmanager

        from core.services.knowledge_core_context import gather_knowledge_core_context

        @contextmanager
        def _cm():
            builder = _make_builder(
                book_results=[_book_result(chunk_id=book_chunk_id)],
                screenplay_results=[_screenplay_result("scene_006")],
            )
            mock_card = MagicMock()
            mock_card.to_dict.return_value = builder.build(entity_id).to_dict()
            mock_builder = MagicMock()
            mock_builder.build.return_value = mock_card
            with patch("knowledge_card.get_card_builder", return_value=mock_builder):
                with patch("knowledge.world_resolver.WorldKnowledgeResolver") as mock_wr:
                    from schemas.world_reference import WorldReferenceStatus

                    mock_wr.return_value.resolve.return_value = MagicMock(
                        model_dump=lambda mode="json": {
                            "query": entity_id,
                            "status": WorldReferenceStatus.UNRESOLVED.value,
                            "resolution_method": "none",
                        }
                    )
                    with patch("knowledge.temporal_resolver.KnowledgeTemporalResolver") as mock_tr:
                        from schemas.temporal_reference import TemporalReferenceStatus

                        mock_tr.return_value.resolve.return_value = MagicMock(
                            model_dump=lambda mode="json": {
                                "claim_id": entity_id,
                                "time_basis": "WORLD_TIME",
                                "status": TemporalReferenceStatus.UNKNOWN.value,
                                "resolution_method": "none",
                            }
                        )
                        yield

        with _cm():
            return gather_knowledge_core_context([{"entity_id": entity_id, "name": "Проверка"}])

    def test_context_shows_approved_link(self):
        contexts = self._context_for("chunk_p_0010_77326a31efd2")

        assert len(contexts) == 1
        ctx = contexts[0]
        assert len(ctx["screenplay_links"]) == 1
        assert ctx["screenplay_links"][0]["screenplay_scene_id"] == "scene_006"

    def test_context_keeps_source_refs_separate(self):
        contexts = self._context_for("chunk_p_0010_77326a31efd2")
        ctx = contexts[0]

        for claim in ctx["book_claims"]:
            assert claim["source_ref"].startswith("book:")
        for claim in ctx["screenplay_claims"]:
            assert claim["source_ref"].startswith("screenplay:")

    def test_context_unlinked_entity_no_fabrication(self):
        """Сущность без одобренной связи не получает выдуманных screenplay_links."""
        # M16.2: книжный claim с неодобренным chunk_id не даёт связи
        contexts = self._context_for(
            "chunk_p_9999_deadbeefdead",
            book_chunk_id="chunk_p_9999_deadbeefdead",
        )

        assert len(contexts) == 1
        assert contexts[0]["screenplay_links"] == []
