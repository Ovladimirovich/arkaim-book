"""M10 — Screenplay Representation & Source Disambiguation tests."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock


_CORE = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from narrative_engine.source_levels import ProvenanceCategory
from knowledge_card import KnowledgeCardBuilder
from evidence.resolver import (
    EvidenceResolver,
    ScreenplaySceneSource,
    BookChunkSource,
    ResolutionStatus,
    locator_for_screenplay_scene,
)


def _make_retriever_mock(book_results=None, screenplay_results=None, genome_results=None):
    """Создаёт мок retriever'а с результатами для разных источников."""
    retriever = MagicMock()
    all_results = []
    all_results.extend(book_results or [])
    all_results.extend(screenplay_results or [])
    all_results.extend(genome_results or [])
    retriever.search = MagicMock(return_value=all_results)
    return retriever


def _book_result(text="Аркаим — древнее городище", chunk_id="chunk_001"):
    return {
        "text": text,
        "source": "book",
        "chunk_id": chunk_id,
        "metadata": {"chunk_id": chunk_id, "source": "book"},
        "chapter_title": "Часть 1",
    }


def _screenplay_result(
    text="Сцена прибытия в Аркаим",
    scene_id="scene_000",
    scene_title="1. INT. АЭРОПОРТ - ДЕНЬ",
    chunk_id="scene_000_abc123",
):
    return {
        "text": text,
        "source": "screenplay",
        "chunk_id": chunk_id,
        "metadata": {
            "chunk_id": chunk_id,
            "source": "screenplay",
            "scene_id": scene_id,
            "scene_title": scene_title,
            "location": "АЭРОПОРТ",
            "scene_type": "INT",
        },
    }


def _genome_result(text="Тема: Аркаим — древнее городище", chunk_id="genome_theme_theme_129"):
    return {
        "text": text,
        "source": "genome",
        "chunk_id": chunk_id,
        "metadata": {"chunk_id": chunk_id, "source": "genome"},
    }


class TestScreenplayDisambiguation:
    """Тесты на разделение книги и сценария в Knowledge Card."""

    def test_screenplay_not_in_book_claims(self):
        """Screenplay-записи не попадают в book claims."""
        retriever = _make_retriever_mock(
            book_results=[_book_result()],
            screenplay_results=[_screenplay_result()],
        )
        builder = KnowledgeCardBuilder()
        builder._retriever_or_none = MagicMock(return_value=retriever)

        card = builder.build("Аркаим")

        book_source = next(s for s in card.sources if s.source_name == "book")
        screenplay_refs = [claim.source_ref for claim in book_source.claims if claim.source_ref.startswith("screenplay:")]
        assert len(screenplay_refs) == 0, "Screenplay-записи не должны попадать в book claims"

    def test_screenplay_in_separate_source(self):
        """Сценарные claims попадают в отдельный раздел screenplay."""
        retriever = _make_retriever_mock(
            book_results=[_book_result()],
            screenplay_results=[_screenplay_result()],
        )
        builder = KnowledgeCardBuilder()
        builder._retriever_or_none = MagicMock(return_value=retriever)

        card = builder.build("Аркаим")

        screenplay_source = next((s for s in card.sources if s.source_name == "screenplay"), None)
        assert screenplay_source is not None, "Source 'screenplay' должен существовать"
        assert len(screenplay_source.claims) == 1
        assert screenplay_source.claims[0].source_ref == "screenplay:scene:scene_000"
        assert screenplay_source.provenance_category == ProvenanceCategory.AUTHOR_CANON, "Screenplay сохраняет AUTHOR_CANON"

    def test_book_claims_preserved(self):
        """Существующие книжные claims не теряются."""
        retriever = _make_retriever_mock(
            book_results=[
                _book_result(text="Аркаим построен потомками гипербореев", chunk_id="chunk_001"),
                _book_result(text="Аркаим — древнее городище", chunk_id="chunk_002"),
            ],
            screenplay_results=[_screenplay_result()],
        )
        builder = KnowledgeCardBuilder()
        builder._retriever_or_none = MagicMock(return_value=retriever)

        card = builder.build("Аркаим")

        book_source = next(s for s in card.sources if s.source_name == "book")
        assert len(book_source.claims) == 2
        book_refs = [claim.source_ref for claim in book_source.claims]
        assert "book:chunk_001" in book_refs
        assert "book:chunk_002" in book_refs

    def test_screenplay_visual_details_preserved(self):
        """Визуальные детали сценария сохраняются."""
        retriever = _make_retriever_mock(
            book_results=[_book_result()],
            screenplay_results=[
                _screenplay_result(
                    text="Камера медленно приближается к древним стенам Аркаима",
                    scene_id="scene_042",
                    scene_title="42. EXT. АРКАИМ - ЗАКАТ",
                ),
            ],
        )
        builder = KnowledgeCardBuilder()
        builder._retriever_or_none = MagicMock(return_value=retriever)

        card = builder.build("Аркаим")

        screenplay_source = next((s for s in card.sources if s.source_name == "screenplay"), None)
        assert screenplay_source is not None
        assert len(screenplay_source.claims) == 1
        claim = screenplay_source.claims[0]
        assert "камера" in claim.text.lower() or "стен" in claim.text.lower()
        assert claim.notes == "42. EXT. АРКАИМ - ЗАКАТ"

    def test_scene_id_uniqueness(self):
        """Идентификаторы разных сцен уникальны, включая повторяющиеся номера."""
        retriever = _make_retriever_mock(
            book_results=[_book_result()],
            screenplay_results=[
                _screenplay_result(
                    text="Первая сцена с номером 1",
                    scene_id="scene_000",
                    scene_title="1. INT. ДОМ - ДЕНЬ",
                ),
                _screenplay_result(
                    text="Вторая сцена с номером 1",
                    scene_id="scene_042",
                    scene_title="1. EXT. УЛИЦА - ДЕНЬ",
                ),
            ],
        )
        builder = KnowledgeCardBuilder()
        builder._retriever_or_none = MagicMock(return_value=retriever)

        card = builder.build("Аркаим")

        screenplay_source = next((s for s in card.sources if s.source_name == "screenplay"), None)
        assert screenplay_source is not None
        refs = [claim.source_ref for claim in screenplay_source.claims]
        assert "screenplay:scene:scene_000" in refs
        assert "screenplay:scene:scene_042" in refs
        assert len(refs) == len(set(refs)), "scene_id должны быть уникальными"

    def test_genome_fallback_not_in_book_claims(self):
        """Genome fallback не попадает в книжные claims."""
        retriever = _make_retriever_mock(
            book_results=[_book_result()],
            genome_results=[_genome_result()],
        )
        builder = KnowledgeCardBuilder()
        builder._retriever_or_none = MagicMock(return_value=retriever)

        card = builder.build("Аркаим")

        book_source = next(s for s in card.sources if s.source_name == "book")
        genome_refs = [claim.source_ref for claim in book_source.claims if claim.source_ref.startswith("genome:") or claim.source_ref.startswith("book:genome")]
        assert len(genome_refs) == 0, "Genome fallback не должен попадать в book claims"

    def test_screenplay_not_independent_confirmation(self):
        """Сценарий не учитывается как независимое подтверждение книги.

        Screenplay и книга хранятся раздельно, с разными source_ref.
        """
        retriever = _make_retriever_mock(
            book_results=[_book_result(text="Аркаим — городище", chunk_id="chunk_001")],
            screenplay_results=[_screenplay_result(text="Прибытие в Аркаим", scene_id="scene_000")],
        )
        builder = KnowledgeCardBuilder()
        builder._retriever_or_none = MagicMock(return_value=retriever)

        card = builder.build("Аркаим")

        book_source = next(s for s in card.sources if s.source_name == "book")
        screenplay_source = next(s for s in card.sources if s.source_name == "screenplay")

        assert book_source.claims[0].source_ref == "book:chunk_001"
        assert screenplay_source.claims[0].source_ref == "screenplay:scene:scene_000"

        book_texts = [claim.text for claim in book_source.claims]
        screenplay_texts = [claim.text for claim in screenplay_source.claims]
        assert "Прибытие в Аркаим" not in book_texts
        assert "Аркаим — городище" not in screenplay_texts


class TestScreenplayResolver:
    """Тесты на разрешение screenplay-локаторов в Evidence Resolver."""

    def test_resolve_screenplay_scene_resolved(self):
        """Существующая сцена разрешается в RESOLVED."""
        scenes = {
            "scene_000": {
                "text": "Прибытие в Аркаим",
                "scene_id": "scene_000",
                "scene_title": "1. INT. АЭРОПОРТ - ДЕНЬ",
            }
        }
        screenplay_source = ScreenplaySceneSource(scenes=scenes)
        resolver = EvidenceResolver(screenplay_source=screenplay_source)

        result = resolver.resolve_locator("screenplay:scene:scene_000")

        assert result.status == ResolutionStatus.RESOLVED
        assert result.evidence is not None
        assert result.evidence.source_id == "screenplay"
        assert result.evidence.locator == "screenplay:scene:scene_000"

    def test_resolve_screenplay_scene_unavailable(self):
        """Отсутствующая сцена даёт UNAVAILABLE."""
        screenplay_source = ScreenplaySceneSource(scenes={})
        resolver = EvidenceResolver(screenplay_source=screenplay_source)

        result = resolver.resolve_locator("screenplay:scene:scene_999")

        assert result.status == ResolutionStatus.UNAVAILABLE
        assert result.evidence is None
        assert "scene_999" in result.reason

    def test_resolve_screenplay_scene_unknown_empty(self):
        """Пустой scene_id даёт UNKNOWN."""
        resolver = EvidenceResolver()

        result = resolver.resolve_locator("screenplay:scene:")

        assert result.status == ResolutionStatus.UNKNOWN

    def test_book_locator_does_not_resolve_as_screenplay(self):
        """Книжный локатор не разрешается как screenplay."""
        chunk_source = BookChunkSource(
            chunks={
                "chunk_001": {
                    "text": "Аркаим — городище",
                    "chunk_id": "chunk_001",
                    "source": "book",
                }
            }
        )
        resolver = EvidenceResolver(chunk_source=chunk_source)

        result = resolver.resolve_locator("book:chunk:chunk_001")

        assert result.status == ResolutionStatus.RESOLVED
        assert result.evidence is not None
        assert result.evidence.source_id == "book"
        assert not result.evidence.locator.startswith("screenplay:")

    def test_screenplay_source_from_chunks(self):
        """ScreenplaySceneSource.from_screenplay_chunks строит индекс по scene_id."""
        chunks = [
            {"scene_id": "scene_000", "text": "Сцена 1"},
            {"scene_id": "scene_001", "text": "Сцена 2"},
            {"scene_id": "scene_042", "text": "Сцена 3"},
        ]
        source = ScreenplaySceneSource.from_screenplay_chunks(chunks)

        assert source.get_scene("scene_000") is not None
        assert source.get_scene("scene_001") is not None
        assert source.get_scene("scene_042") is not None
        assert source.get_scene("scene_999") is None

    def test_locator_for_screenplay_scene(self):
        """Функция locator_for_screenplay_scene возвращает корректный локатор."""
        locator = locator_for_screenplay_scene("scene_000")
        assert locator == "screenplay:scene:scene_000"


class TestScreenplayNotBookEvidence:
    """Тесты на то, что сценарный локатор не считается книжным evidence."""

    def test_screenplay_locator_not_in_book_claims(self):
        """Локатор screenplay:scene:* не должен появляться в book claims."""
        retriever = _make_retriever_mock(
            book_results=[_book_result()],
            screenplay_results=[
                _screenplay_result(
                    text="Сцена прибытия",
                    scene_id="scene_000",
                    scene_title="1. EXT. ГОРОД - ДЕНЬ",
                ),
                _screenplay_result(
                    text="Сцена разговора",
                    scene_id="scene_001",
                    scene_title="2. INT. ДОМ - ДЕНЬ",
                ),
            ],
        )
        builder = KnowledgeCardBuilder()
        builder._retriever_or_none = MagicMock(return_value=retriever)

        card = builder.build("Аркаим")

        book_source = next(s for s in card.sources if s.source_name == "book")
        for claim in book_source.claims:
            assert not claim.source_ref.startswith("screenplay:"), f"Claim {claim.source_ref} не должен быть в book claims"

    def test_screenplay_claims_have_correct_provenance(self):
        """Сценарные claims имеют AUTHOR_CANON и source_title='Сценарий'."""
        retriever = _make_retriever_mock(
            screenplay_results=[_screenplay_result()],
        )
        builder = KnowledgeCardBuilder()
        builder._retriever_or_none = MagicMock(return_value=retriever)

        card = builder.build("Аркаим")

        screenplay_source = next((s for s in card.sources if s.source_name == "screenplay"), None)
        assert screenplay_source is not None
        claim = screenplay_source.claims[0]
        assert claim.provenance.category == ProvenanceCategory.AUTHOR_CANON
        assert claim.provenance.source_title == "Сценарий"

    def test_mixed_sources_no_cross_contamination(self):
        """Смешанные результаты не создают перекрёстного загрязнения."""
        retriever = _make_retriever_mock(
            book_results=[_book_result(text="Книжное описание", chunk_id="chunk_001")],
            screenplay_results=[
                _screenplay_result(
                    text="Сценарное описание",
                    scene_id="scene_000",
                    scene_title="1. INT. ДОМ - ДЕНЬ",
                ),
            ],
            genome_results=[_genome_result(text="Genome тема")],
        )
        builder = KnowledgeCardBuilder()
        builder._retriever_or_none = MagicMock(return_value=retriever)

        card = builder.build("Аркаим")

        book_source = next(s for s in card.sources if s.source_name == "book")
        screenplay_source = next(s for s in card.sources if s.source_name == "screenplay")
        genome_source = next(s for s in card.sources if s.source_name == "genome")

        assert len(book_source.claims) == 1
        assert book_source.claims[0].source_ref == "book:chunk_001"

        assert len(screenplay_source.claims) == 1
        assert screenplay_source.claims[0].source_ref == "screenplay:scene:scene_000"

        assert len(genome_source.claims) == 1
        assert genome_source.claims[0].source_ref == "genome:theme:theme_129"
