"""Book Intelligence Pipeline tests: chunking, retrieval, provenance flow."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Add CORE to path for imports
CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from narrative_engine.source_levels import ProvenanceCategory, ProvenanceTag

_BASE = Path(__file__).resolve().parent.parent.parent / "core"
BOOK_PATH = _BASE / "SOURCE_OF_TRUTH" / "BOOK" / "КНИГА.md"
BOOK_DOC_PATH = _BASE / "KNOWLEDGE" / "BOOK_DOCUMENT.json"
CHROMA_DIR = _BASE / "CHROMA_DB"
ENRICHED_CHUNKS_PATH = _BASE / "KNOWLEDGE" / "enriched_chunks.json"
ENRICHED_CATALOG_PATH = _BASE / "KNOWLEDGE" / "enriched_catalog.json"


def _get_retriever():
    try:
        from intelligence.retriever import BookRetriever

        return BookRetriever()
    except ImportError, ModuleNotFoundError:
        pytest.skip("intelligence.retriever not importable (needs PYTHONPATH=core/CORE)")


class TestBookSource:
    def test_book_file_exists(self):
        assert BOOK_PATH.exists()

    def test_book_is_utf8(self):
        text = BOOK_PATH.read_text(encoding="utf-8")
        assert len(text) > 10000

    def test_book_has_chapters(self):
        text = BOOK_PATH.read_text(encoding="utf-8")
        assert any(w in text for w in ["Пролог", "Глава", "Часть"])

    def test_book_document_json_exists(self):
        assert BOOK_DOC_PATH.exists()

    def test_book_document_has_chapters_and_paragraphs(self):
        data = json.loads(BOOK_DOC_PATH.read_text(encoding="utf-8"))
        content = data.get("content", {})
        assert len(content.get("chapters", [])) >= 10
        assert len(content.get("paragraphs", [])) >= 100


class TestChunking:
    def test_chunker_loads_document(self):
        from intelligence.chunker import SemanticChunker

        assert len(SemanticChunker().get_chapters()) >= 10

    def test_paragraph_chunks_count(self):
        from intelligence.chunker import SemanticChunker

        assert len(SemanticChunker().chunk_by_paragraph()) >= 800

    def test_chunk_ids_stable(self):
        from intelligence.chunker import SemanticChunker

        c1 = SemanticChunker().chunk_by_paragraph()
        c2 = SemanticChunker().chunk_by_paragraph()
        assert [c["id"] for c in c1] == [c["id"] for c in c2]

    def test_chunk_has_metadata(self):
        from intelligence.chunker import SemanticChunker

        for c in SemanticChunker().chunk_by_paragraph()[:10]:
            assert all(k in c for k in ("id", "text", "chapter_id", "source"))
            assert c["source"] == "book"

    def test_chunk_has_chapter_info(self):
        from intelligence.chunker import SemanticChunker

        assert any(c.get("chapter_title") for c in SemanticChunker().chunk_by_paragraph())

    def test_no_empty_chunks(self):
        from intelligence.chunker import SemanticChunker

        empty = [c for c in SemanticChunker().chunk_by_paragraph() if not c.get("text", "").strip()]
        assert len(empty) == 0

    def test_no_text_loss(self):
        from intelligence.chunker import SemanticChunker

        total = sum(len(c["text"]) for c in SemanticChunker().chunk_by_paragraph())
        assert total > 80000


class TestVectorStore:
    def test_chroma_dir_exists(self):
        assert CHROMA_DIR.exists()

    def test_chroma_has_sqlite(self):
        assert (CHROMA_DIR / "chroma.sqlite3").exists()

    def test_chroma_has_hnsw_indexes(self):
        hnsw = [d for d in CHROMA_DIR.iterdir() if d.is_dir() and (d / "header.bin").exists()]
        assert len(hnsw) >= 1

    def test_enriched_chunks_exist(self):
        assert ENRICHED_CHUNKS_PATH.exists()

    def test_enriched_catalog_exist(self):
        assert ENRICHED_CATALOG_PATH.exists()


class TestRetrieval:
    def test_retriever_has_provenance_category(self):
        r = _get_retriever()
        results = r.search("Аркаим", n_results=3)
        if results:
            assert "provenance_category" in results[0]

    def test_retriever_has_chunk_id(self):
        r = _get_retriever()
        results = r.search("Аркаим", n_results=3)
        if results:
            assert "chunk_id" in results[0]

    def test_retriever_has_score(self):
        r = _get_retriever()
        results = r.search("Аркаим", n_results=3)
        if results:
            assert isinstance(results[0]["score"], (int, float))

    def test_retriever_has_source(self):
        r = _get_retriever()
        results = r.search("Аркаим", n_results=3)
        if results:
            assert "source" in results[0]

    def test_retriever_book_text_is_canon(self):
        r = _get_retriever()
        results = r.search("Велик", n_results=3)
        if results:
            for res in results:
                if res.get("source") in ("book", "catalog", "genome"):
                    assert res.get("provenance_category") == "AUTHOR_CANON"


class TestEndToEndProvenanceFlow:
    def test_catalog_text_is_canon(self):
        from pulse.layers import _canon_tag

        tag = _canon_tag("catalog", "book text")
        assert tag.category == ProvenanceCategory.AUTHOR_CANON

    def test_provenance_survives_to_api_dict(self):
        from pulse.layers import PulseResponse, _canon_tag

        resp = PulseResponse(
            text="test",
            source="knowledge:rag",
            confidence=0.85,
            provenance=[_canon_tag("rag", "RAG from book")],
        )
        api = resp.get_provenance_dicts()
        assert api[0]["category"] == "AUTHOR_CANON"
        assert api[0]["confidence"] == 1.0

    def test_weak_retrieval_has_uncertainty(self):
        from pulse.layers import PulseResponse, _canon_tag, UncertaintyFlag

        resp = PulseResponse(
            text="weak",
            source="knowledge:rag",
            confidence=0.5,
            provenance=[_canon_tag("rag", "weak")],
            uncertainty=UncertaintyFlag(has_unknowns=True, unknown_aspects=["low score"]),
        )
        assert resp.uncertainty.has_unknowns is True


class TestEmbeddingConfig:
    def test_embedding_model_configured(self):
        from config import config

        assert config.EMBEDDING_MODEL

    def test_embedding_model_is_multilingual(self):
        from config import config

        m = config.EMBEDDING_MODEL
        assert any(k in m for k in ("multilingual", "e5", "MiniLM"))

    def test_chroma_dir_configured(self):
        from config import config

        assert config.CHROMA_DIR.exists() or config.CHROMA_DIR.parent.exists()
