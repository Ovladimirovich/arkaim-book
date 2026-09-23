"""
Тесты для KnowledgeKernel, SemanticChunker и GenomeEnricher.
"""

from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".." / "ARKAIM_DIGITAL_CONSCIOUSNESS" / "CORE"))

from intelligence.chunker import SemanticChunker
from intelligence.enricher import GenomeEnricher
from intelligence.kernel import KnowledgeKernel
from intelligence.retriever import BookRetriever
from intelligence.nameresolver import NameResolver


BASE = Path(__file__).resolve().parents[1] / ".." / "ARKAIM_DIGITAL_CONSCIOUSNESS"


class TestSemanticChunker:
    def test_loads_document(self):
        chunker = SemanticChunker()
        stats = chunker.get_stats()
        assert stats["total_chapters"] >= 15
        assert stats["total_paragraphs"] >= 800
        assert stats["total_chars"] >= 100000

    def test_chunk_by_paragraph(self):
        chunker = SemanticChunker()
        chunks = chunker.chunk_by_paragraph()
        assert len(chunks) >= 800
        assert "chapter_id" in chunks[0]
        assert "chapter_title" in chunks[0]
        assert "paragraph_id" in chunks[0]
        assert chunks[0]["source"] == "book"

    def test_chunk_by_chapter(self):
        chunker = SemanticChunker()
        chunks = chunker.chunk_by_chapter()
        assert len(chunks) >= 15
        assert chunks[0]["paragraph_id"] == "all"

    def test_chunk_hybrid(self):
        chunker = SemanticChunker()
        chunks = chunker.chunk_hybrid()
        assert len(chunks) > 800


class TestGenomeEnricher:
    def test_loads_genome(self):
        enricher = GenomeEnricher()
        stats = enricher.get_genome_stats()
        assert stats["themes_count"] >= 100
        assert stats["characters_count"] >= 10
        assert stats["symbols_count"] >= 10
        assert stats["status"] == "loaded"

    def test_enrich_chunk_finds_content(self):
        enricher = GenomeEnricher()
        text = "Гиперборея была древней северной цивилизацией, хранительницей высших знаний. Велик отправился в путешествие к Аркаиму."
        result = enricher.enrich_chunk(text)
        names = [t["name"] for t in result["themes"]]
        assert len(result["themes"]) > 0
        assert any("гиперборе" in n.lower() for n in names) or any("гиперборе" in str(result) for _ in [1])

    def test_enrich_chunks_batch(self):
        enricher = GenomeEnricher()
        chunks = [
            {"id": "test_1", "text": "Велик направлялся к Капитолию через заснеженные перевалы."},
            {"id": "test_2", "text": "Архат — высшее существо, завершившее человеческую эволюцию."},
        ]
        enriched = enricher.enrich_chunks(chunks)
        assert len(enriched) == 2
        assert "enriched_themes" in enriched[0]
        assert "enriched_characters" in enriched[0]
        assert "enrichment_count" in enriched[0]

    def test_empty_text(self):
        enricher = GenomeEnricher()
        result = enricher.enrich_chunk("")
        assert result["themes"] == []
        assert result["characters"] == []


class TestKnowledgeKernel:
    def test_init(self):
        kernel = KnowledgeKernel()
        stats = kernel.get_stats()
        assert "chunker" in stats
        assert "enricher" in stats
        assert "chroma" in stats

    def test_search_returns_results(self):
        kernel = KnowledgeKernel()
        results = kernel.search("Гиперборея", n_results=2)
        assert isinstance(results, list)

    def test_index_and_search(self):
        kernel = KnowledgeKernel()
        # Clear and reindex
        kernel.retriever.clear_collection()
        result = kernel.index_book(mode="paragraph")
        assert result["status"] == "ok"
        assert result["chunks_total"] > 0
        assert result["chunks_indexed"] > 0

        # Search after index
        results = kernel.search("Архат", n_results=3)
        assert len(results) > 0
        assert "text" in results[0]
        assert "score" in results[0]

    def test_search_enriched_fields(self):
        kernel = KnowledgeKernel()
        results = kernel.search("Велик", n_results=3)
        if results:
            r = results[0]
            assert "themes" in r
            assert "characters" in r
            assert "symbols" in r


class TestNameResolver:
    def test_resolve_velik(self):
        nr = NameResolver()
        assert nr.resolve("Велик") == "Велик"
        assert nr.resolve("Велиусмус") == "Велик"
        assert nr.resolve("Великосвет") == "Велик"
        assert nr.resolve("Велом") == "Велик"

    def test_resolve_slavny(self):
        nr = NameResolver()
        assert nr.resolve("Славный") == "Славный"
        assert nr.resolve("Мирослав") == "Славный"
        assert nr.resolve("Слава") == "Славный"

    def test_resolve_svetovit(self):
        nr = NameResolver()
        assert nr.resolve("Световит") == "Световит"

    def test_resolve_unknown(self):
        nr = NameResolver()
        assert nr.resolve("НеизвестноеИмя") == "НеизвестноеИмя"

    def test_expand_query(self):
        nr = NameResolver()
        expanded = nr.expand_query("Великосвет")
        assert "Велик" in expanded
        assert "Велиусмус" in expanded or "Велом" in expanded

    def test_get_stats(self):
        nr = NameResolver()
        stats = nr.get_stats()
        assert stats["canonical_names"] >= 10
        assert stats["total_aliases"] >= 20

    def test_kernel_uses_nameresolver(self):
        kernel = KnowledgeKernel()
        assert kernel.resolve_name("Велиусмус") == "Велик"
        assert kernel.resolve_name("Славик") == "Славный"
        stats = kernel.get_stats()
        assert "nameresolver" in stats
        assert stats["nameresolver"]["canonical_names"] >= 10

    def test_enricher_deduplicates_with_nameresolver(self):
        enricher = GenomeEnricher(nameresolver=NameResolver())
        # Текст с разными алиасами одного персонажа
        text = "Велик встретил Великосвета. Велиусмус шел к Велему."
        result = enricher.enrich_chunk(text)
        names = [c["name"] for c in result["characters"]]
        # "Велик" должен быть только один раз (без дубликатов)
        assert names.count("Велик") <= 1


class TestBookRetriever:
    def test_init(self):
        retriever = BookRetriever()
        assert retriever is not None

    def test_get_collection_stats(self):
        retriever = BookRetriever()
        stats = retriever.get_collection_stats()
        assert "count" in stats
        assert "status" in stats
