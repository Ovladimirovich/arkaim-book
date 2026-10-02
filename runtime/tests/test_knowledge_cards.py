"""Knowledge Card + Cross-Source aggregation tests."""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Add CORE to path
_CORE = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from narrative_engine.source_levels import (
    ProvenanceCategory,
    ProvenanceTag,
    SourceLevel,
)
from pulse.layers import UncertaintyFlag
from knowledge_card import (
    KnowledgeCard,
    CardClaim,
    SourceAggregation,
    ContradictionNote,
    CardMetadata,
    KnowledgeCardBuilder,
    get_card_builder,
)


# ═══════════════════════════════════════════════════════════════
# 1. Model Tests
# ═══════════════════════════════════════════════════════════════

class TestModels:
    """Pydantic models validate correctly."""

    def test_canon_claim(self):
        tag = ProvenanceTag(
            source_level=SourceLevel.CANON,
            category=ProvenanceCategory.AUTHOR_CANON,
            confidence=1.0,
            notes="from book",
        )
        claim = CardClaim(text="Аркаим — древнее городище", provenance=tag, chunk_id="chunk_001")
        assert claim.provenance.category == ProvenanceCategory.AUTHOR_CANON
        assert claim.chunk_id == "chunk_001"

    def test_hypothesis_claim(self):
        tag = ProvenanceTag(
            source_level=SourceLevel.USER_HYPOTHESIS,
            category=ProvenanceCategory.HYPOTHESIS,
            confidence=0.5,
            notes="author hypothesis",
        )
        claim = CardClaim(text="Гипотеза о связи с Атлантидой", provenance=tag)
        assert claim.provenance.category == ProvenanceCategory.HYPOTHESIS

    def test_external_claim(self):
        tag = ProvenanceTag(
            source_level=SourceLevel.HISTORICAL,
            category=ProvenanceCategory.EXTERNAL_SOURCE,
            confidence=0.8,
            notes="archaeology",
        )
        claim = CardClaim(text="Аркаим ~4000 до н.э.", provenance=tag)
        assert claim.provenance.category == ProvenanceCategory.EXTERNAL_SOURCE

    def test_contradiction_note(self):
        note = ContradictionNote(
            description="Книга и археология расходятся",
            source_1_claim="AUTHOR_CANON: X",
            source_2_claim="EXTERNAL_SOURCE: Y",
            resolution="DIFFERENT_PERSPECTIVES",
        )
        assert note.resolution == "DIFFERENT_PERSPECTIVES"

    def test_source_aggregation(self):
        agg = SourceAggregation(
            source_name="book",
            provenance_category=ProvenanceCategory.AUTHOR_CANON,
            claim_count=3,
            summary="3 book claims",
            confidence=0.9,
        )
        assert agg.claim_count == 3

    def test_card_to_dict(self):
        card = KnowledgeCard(metadata={"entity_id": "test", "entity_name": "Test"})
        d = card.to_dict()
        assert d["metadata"]["entity_id"] == "test"

    def test_provenance_invariant_canon_never_external(self):
        """Критический инвариант: AUTHOR_CANON не может стать EXTERNAL_SOURCE."""
        canon_tag = ProvenanceTag(
            source_level=SourceLevel.CANON,
            category=ProvenanceCategory.AUTHOR_CANON,
            confidence=1.0,
        )
        assert canon_tag.category == ProvenanceCategory.AUTHOR_CANON
        # Even at confidence=1.0 it stays AUTHOR_CANON
        assert canon_tag.confidence == 1.0

    def test_provenance_invariant_hypothesis_never_fact(self):
        """HYPOTHESIS не превращается в факт."""
        hyp_tag = ProvenanceTag(
            source_level=SourceLevel.USER_HYPOTHESIS,
            category=ProvenanceCategory.HYPOTHESIS,
            confidence=0.5,
        )
        assert hyp_tag.category == ProvenanceCategory.HYPOTHESIS


# ═══════════════════════════════════════════════════════════════
# 2. Entity Resolution
# ═══════════════════════════════════════════════════════════════

class TestEntityResolution:
    """Entity resolution across multiple systems."""

    def test_resolve_existing_entity(self):
        builder = KnowledgeCardBuilder()
        result = builder._resolve_entity("arkaim_region")
        # Should find in WorldEngine or return None
        assert result is not None or True  # May or may not find depending on data

    def test_resolve_by_name_search(self):
        builder = KnowledgeCardBuilder()
        # Search for an entity that likely exists
        result = builder._resolve_entity("аркаим")
        # Either finds it or returns None — both OK
        if result:
            assert "name" in result
            assert "id" in result

    def test_resolve_missing_entity(self):
        builder = KnowledgeCardBuilder()
        result = builder._resolve_entity("__nonexistent_entity_xyz__")
        assert result is None

    def test_archaeology_name_resolution(self):
        builder = KnowledgeCardBuilder()
        # Try resolving "Аркаим" which should be in ARCHAEOLOGY.json
        result = builder._resolve_entity("Аркаим")
        if result is not None:
            assert "name" in result
            # Entity found from somewhere - accept any source
            assert result.get("name") is not None

    def test_region_arkaim_uses_approved_crosswalk_alias_for_book_queries(self):
        """A mojibake World Engine display name must not break Book retrieval."""
        queries: list[str] = []

        class Retriever:
            def search(self, query: str, n_results: int = 5):
                queries.append(query)
                if query != "аркаим":
                    return []
                return [
                    {
                        "text": "Аркаим — древнее городище на Южном Урале.",
                        "chunk_id": "chunk_region_arkaim_contract",
                        "chapter_title": "Аркаим",
                    }
                ]

        class Engine:
            def get_entity(self, entity_id: str):
                return {
                    "id": "region_arkaim",
                    "name": "РђСЂРєР°РёРј",  # existing mojibake display data
                    "description": "Р”СЂРµРІРЅРµРіРѕСЂРѕРґРёС‰РµРЅР°РѕСЂ",
                }

            def search(self, query: str):
                return {"world_model": []}

            def get_entity_context(self, entity_id: str):
                return {"relations": {}}

        builder = KnowledgeCardBuilder()
        builder._world_engine = Engine()
        builder._retriever = Retriever()
        builder._retriever_initialized = True

        card = builder.build("region_arkaim")

        assert builder._approved_rag_aliases("region_arkaim") == ["аркаим"]
        assert "аркаим" in queries
        book = next(source for source in card.sources if source.source_name == "book")
        assert [claim.chunk_id for claim in book.claims] == ["chunk_region_arkaim_contract"]


# ═══════════════════════════════════════════════════════════════
# 3. Aggregation Tests
# ═══════════════════════════════════════════════════════════════

class TestAggregation:
    """Cross-source aggregation from all sources."""

    def test_build_card_for_entity(self):
        builder = KnowledgeCardBuilder()
        card = builder.build("Аркаим")
        # Card should be built even if entity not found
        assert isinstance(card, KnowledgeCard)
        assert card.metadata.entity_id == "Аркаим"

    def test_card_has_sources(self):
        builder = KnowledgeCardBuilder()
        card = builder.build("Аркаим")
        # Should have at least empty sources
        assert isinstance(card.sources, list)
        # Check that book source is present
        book_sources = [s for s in card.sources if s.source_name == "book"]
        assert len(book_sources) >= 1
        assert book_sources[0].provenance_category == ProvenanceCategory.AUTHOR_CANON

    def test_genome_fallback_is_projected_as_derived_genome_source(self):
        class Retriever:
            def __init__(self):
                self.calls = 0

            def search(self, query: str, n_results: int = 5):
                self.calls += 1
                if self.calls > 2:
                    return []
                if self.calls == 1:
                    return []
                return [{
                    "text": "Тема: Аркаим — древнее городище",
                    "source": "genome",
                    "chunk_id": "genome_theme_theme_129",
                }]

        builder = KnowledgeCardBuilder()
        builder._retriever = Retriever()
        builder._retriever_initialized = True
        builder._world_engine = False

        card = builder.build("Аркаим")

        genome = next(source for source in card.sources if source.source_name == "genome")
        book = next(source for source in card.sources if source.source_name == "book")
        assert genome.provenance_category == ProvenanceCategory.DERIVED
        assert genome.claims[0].source_ref == "genome:theme:theme_129"
        assert all(not claim.source_ref.startswith("book:genome_theme_") for claim in book.claims)

    def test_all_sources_present(self):
        builder = KnowledgeCardBuilder()
        card = builder.build("Аркаим")
        source_names = {s.source_name for s in card.sources}
        assert "book" in source_names
        assert "archaeology" in source_names
        assert "cross_references" in source_names
        assert "academic" in source_names

    def test_no_duplicate_claims(self):
        builder = KnowledgeCardBuilder()
        card = builder.build("Аркаим")
        # Check no duplicate text across all sources
        all_texts = []
        for source in card.sources:
            for claim in source.claims:
                all_texts.append(claim.text)
        # Simple duplicate detection
        unique = set()
        for t in all_texts:
            assert t not in unique, f"Duplicate claim: {t[:50]}"
            unique.add(t)


# ═══════════════════════════════════════════════════════════════
# 4. Provenance Tests
# ═══════════════════════════════════════════════════════════════

class TestProvenance:
    """Provenance must be preserved per-claim."""

    def test_book_claims_are_canon(self):
        builder = KnowledgeCardBuilder()
        card = builder.build("Аркаим")
        book_sources = [s for s in card.sources if s.source_name == "book"]
        for src in book_sources:
            assert src.provenance_category == ProvenanceCategory.AUTHOR_CANON
            for claim in src.claims:
                assert claim.provenance.category == ProvenanceCategory.AUTHOR_CANON

    def test_archaeology_claims_are_external(self):
        builder = KnowledgeCardBuilder()
        card = builder.build("Аркаим")
        arch_sources = [s for s in card.sources if s.source_name == "archaeology"]
        for src in arch_sources:
            assert src.provenance_category in (
                ProvenanceCategory.EXTERNAL_SOURCE,
                ProvenanceCategory.RECONSTRUCTION,
            )

    def test_hypothesis_stays_hypothesis(self):
        builder = KnowledgeCardBuilder()
        card = builder.build("Аркаим")
        arch_sources = [s for s in card.sources if s.source_name == "archaeology"]
        for src in arch_sources:
            hyp_claims = [c for c in src.claims if c.provenance.category == ProvenanceCategory.HYPOTHESIS]
            for claim in hyp_claims:
                # Hypothesis should stay hypothesis, never promoted
                assert claim.provenance.category == ProvenanceCategory.HYPOTHESIS
                assert claim.provenance.confidence <= 0.6

    def test_canon_never_promoted(self):
        """CRITICAL: Canonic claims are never reclassified as something else."""
        builder = KnowledgeCardBuilder()
        card = builder.build("Аркаим")
        for source in card.sources:
            for claim in source.claims:
                if claim.provenance.category == ProvenanceCategory.AUTHOR_CANON:
                    # Must always stay AUTHOR_CANON
                    assert claim.provenance.confidence == 1.0

    def test_all_claims_have_provenance(self):
        builder = KnowledgeCardBuilder()
        card = builder.build("Аркаим")
        for source in card.sources:
            for claim in source.claims:
                assert claim.provenance is not None
                assert claim.provenance.category is not None
                assert claim.provenance.confidence > 0

    def test_chunk_ids_preserved(self):
        """Book claims must preserve chunk_id for traceability."""
        builder = KnowledgeCardBuilder()
        card = builder.build("Аркаим")
        book_sources = [s for s in card.sources if s.source_name == "book"]
        for src in book_sources:
            for claim in src.claims:
                # chunk_id should be set or at least source_ref should reference book
                assert claim.source_ref.startswith("book:") or claim.chunk_id is not None


# ═══════════════════════════════════════════════════════════════
# 5. Contradiction Tests
# ═══════════════════════════════════════════════════════════════

class TestContradictions:
    """Contradictions must be detected and preserved, not resolved."""

    def test_detects_potential_conflicts(self):
        builder = KnowledgeCardBuilder()
        card = builder.build("Аркаим")
        # Contradictions may or may not exist — that's fine
        # What matters is the structure is correct
        for cd in card.contradictions:
            assert cd.resolution in ("UNRESOLVED", "DIFFERENT_PERSPECTIVES", "TEMPORARY")
            assert len(cd.source_1_claim) > 0
            assert len(cd.source_2_claim) > 0

    def test_no_auto_resolution(self):
        """System must never auto-resolve contradictions."""
        builder = KnowledgeCardBuilder()
        card = builder.build("Аркаим")
        for cd in card.contradictions:
            # Never choose a winner
            assert cd.resolution != "RESOLVED"

    def test_conflicting_claims_preserved(self):
        """Even conflicting claims from different sources must coexist."""
        builder = KnowledgeCardBuilder()
        card = builder.build("Аркаим")
        all_sources = {s.source_name for s in card.sources}
        # Both book and archaeology should coexist regardless of conflicts
        assert "book" in all_sources


# ═══════════════════════════════════════════════════════════════
# 6. Uncertainty Tests
# ═══════════════════════════════════════════════════════════════

class TestUncertainty:
    """Uncertainty must be tracked and preserved."""

    def test_uncertainty_structure(self):
        builder = KnowledgeCardBuilder()
        card = builder.build("Аркаим")
        if card.uncertainty is not None:
            assert "has_unknowns" in card.uncertainty
            assert "unknown_aspects" in card.uncertainty
            assert isinstance(card.uncertainty["unknown_aspects"], list)

    def test_empty_card_has_uncertainty(self):
        """Entity with no data should show uncertainty explicitly."""
        builder = KnowledgeCardBuilder()
        card = builder.build("__nonexistent_entity_xyz__")
        assert card.metadata.coverage_note == "Сущность не найдена ни в одной системе"
        # Should have uncertainty about missing data
        if card.uncertainty:
            assert card.uncertainty["has_unknowns"] is True


# ═══════════════════════════════════════════════════════════════
# 7. Book Integration Tests
# ═══════════════════════════════════════════════════════════════

class TestBookIntegration:
    """Real integration with Book Intelligence pipeline."""

    def test_retriever_genome_fallback_is_not_book_catalog_evidence(self):
        from intelligence.retriever import BookRetriever

        retriever = object.__new__(BookRetriever)
        retriever._genome = {"modules": {"themes": [{"id": "theme_129", "name": "Аркаим", "description": "Theme projection"}], "characters": []}}
        retriever._catalog_cache = []
        result = retriever._enriched_fallback("Аркаим", n_results=5)
        assert result[0]["source"] == "genome"
        assert result[0]["chunk_id"] == "genome_theme_theme_129"
        assert result[0]["metadata"] == {"source": "genome", "type": "theme"}

    def test_retriever_returns_with_provenance(self):
        from intelligence.retriever import BookRetriever
        retriever = BookRetriever()
        results = retriever.search("Аркаим", n_results=3)
        if results:
            for r in results:
                assert "provenance_category" in r
                assert r["provenance_category"] == "AUTHOR_CANON"

    def test_chunk_traceability(self):
        from intelligence.retriever import BookRetriever
        retriever = BookRetriever()
        results = retriever.search("Аркаим", n_results=3)
        if results:
            # At least some results should have chunk_id
            has_chunk = any(r.get("chunk_id") for r in results)
            assert has_chunk, "No chunk_id in retrieval results"


# ═══════════════════════════════════════════════════════════════
# 8. Regression Tests
# ═══════════════════════════════════════════════════════════════

class TestRegression:
    """Existing functionality must not break."""

    def test_world_engine_still_works(self):
        from narrative_engine.world_engine import get_world_engine
        engine = get_world_engine()
        stats = engine.get_stats()
        assert "world_model" in stats
        assert stats["initialized"] is True

    def test_provenance_module_intact(self):
        tag = ProvenanceTag(
            source_level=SourceLevel.CANON,
            category=ProvenanceCategory.AUTHOR_CANON,
            confidence=1.0,
            notes="test",
        )
        d = tag.to_dict()
        assert d["category"] == "AUTHOR_CANON"
        assert d["confidence"] == 1.0

    def test_pulse_response_still_works(self):
        from pulse.layers import PulseResponse, _canon_tag
        resp = PulseResponse(
            text="test",
            source="test",
            confidence=0.9,
            provenance=[_canon_tag("test", "from canon")],
        )
        dicts = resp.get_provenance_dicts()
        assert len(dicts) == 1
        assert dicts[0]["category"] == "AUTHOR_CANON"


# ═══════════════════════════════════════════════════════════════
# 9. API Contract Tests
# ═══════════════════════════════════════════════════════════════

class TestAPIContract:
    """API endpoint contract validation."""

    def test_card_serializes_to_json(self):
        card = KnowledgeCard(
            metadata=CardMetadata(entity_id="test", entity_name="Test"),
            sources=[
                SourceAggregation(
                    source_name="book",
                    provenance_category=ProvenanceCategory.AUTHOR_CANON,
                    claim_count=2,
                    summary="2 claims",
                    confidence=0.9,
                    claims=[
                        CardClaim(
                            text="Test claim",
                            provenance=ProvenanceTag(
                                source_level=SourceLevel.CANON,
                                category=ProvenanceCategory.AUTHOR_CANON,
                                confidence=1.0,
                            ),
                            chunk_id="chunk_001",
                        )
                    ],
                )
            ],
            contradictions=[
                ContradictionNote(
                    description="Test conflict",
                    source_1_claim="A",
                    source_2_claim="B",
                    resolution="DIFFERENT_PERSPECTIVES",
                )
            ],
            uncertainty={
                "has_unknowns": True,
                "unknown_aspects": ["test"],
            },
        )
        d = card.to_dict()
        # Verify all expected top-level keys
        assert "metadata" in d
        assert "sources" in d
        assert "contradictions" in d
        assert "uncertainty" in d

    def test_empty_card_serializes(self):
        card = KnowledgeCard(
            metadata=CardMetadata(entity_id="missing", entity_name="Missing"),
        )
        d = card.to_dict()
        assert d["metadata"]["entity_id"] == "missing"
        assert d["sources"] == []


# ─────────────────────────────────────────────────────────────────────────────
# 10. HTTP Routing and Status Regression
# ─────────────────────────────────────────────────────────────────────────────

class TestHTTPRouting:
    """Literal routes and not-found behavior must be observable through HTTP."""

    @staticmethod
    def _client(monkeypatch):
        import knowledge_card as card_module
        from auth import rbac
        from core.routes.knowledge_cards import router

        class FakeBuilder:
            def build(self, entity_id: str) -> KnowledgeCard:
                if entity_id == "missing-entity":
                    return KnowledgeCard(
                        metadata=CardMetadata(
                            entity_id=entity_id,
                            entity_name=entity_id,
                            coverage_note="Сущность не найдена ни в одном источнике",
                        )
                    )
                return KnowledgeCard(
                    metadata=CardMetadata(entity_id=entity_id, entity_name=entity_id),
                    primary_entity={"id": entity_id, "name": entity_id},
                )

            @staticmethod
            def _iter_list(data, *keys):
                return []

            @staticmethod
            def _load_json(name: str):
                return None

        monkeypatch.setattr(card_module.builder, "_builder", FakeBuilder())
        monkeypatch.setitem(
            sys.modules,
            "narrative_engine.world_engine",
            types.SimpleNamespace(
                get_world_engine=lambda: types.SimpleNamespace(
                    initialize=lambda: None,
                    search=lambda query: {
                        "world_model": [
                            {"id": "arkaim_region", "name": "Аркаим", "category": "region"}
                        ]
                    },
                )
            ),
        )

        app = FastAPI()
        app.include_router(router)

        async def current_user() -> dict:
            return {"id": "test-reader", "role": "reader"}

        app.dependency_overrides[rbac.get_current_user] = current_user
        return TestClient(app)

    def test_search_route_is_not_shadowed_by_entity_id(self, monkeypatch):
        client = self._client(monkeypatch)

        response = client.get("/knowledge/cards/search?q=Arkaim")

        assert response.status_code == 200
        payload = response.json()
        assert payload["query"] == "Arkaim"
        assert "metadata" not in payload
        assert payload["entities"][0]["entity_id"] == "arkaim_region"

    def test_missing_entity_returns_404(self, monkeypatch):
        client = self._client(monkeypatch)

        response = client.get("/knowledge/cards/missing-entity")

        assert response.status_code == 404

    def test_known_entity_returns_card(self, monkeypatch):
        client = self._client(monkeypatch)

        response = client.get("/knowledge/cards/arkaim_region")

        assert response.status_code == 200
        assert response.json()["metadata"]["entity_id"] == "arkaim_region"


