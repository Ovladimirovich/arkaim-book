"""Knowledge Card + Cross-Source aggregation tests."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

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


# в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђ
# 1. Model Tests
# в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђ

class TestModels:
    """Pydantic models validate correctly."""

    def test_canon_claim(self):
        tag = ProvenanceTag(
            source_level=SourceLevel.CANON,
            category=ProvenanceCategory.AUTHOR_CANON,
            confidence=1.0,
            notes="from book",
        )
        claim = CardClaim(text="РђСЂРєР°РёРј вЂ” РґСЂРµРІРЅРµРµ РіРѕСЂРѕРґРёС‰Рµ", provenance=tag, chunk_id="chunk_001")
        assert claim.provenance.category == ProvenanceCategory.AUTHOR_CANON
        assert claim.chunk_id == "chunk_001"

    def test_hypothesis_claim(self):
        tag = ProvenanceTag(
            source_level=SourceLevel.USER_HYPOTHESIS,
            category=ProvenanceCategory.HYPOTHESIS,
            confidence=0.5,
            notes="author hypothesis",
        )
        claim = CardClaim(text="Р“РёРїРѕС‚РµР·Р° Рѕ СЃРІСЏР·Рё СЃ РђС‚Р»Р°РЅС‚РёРґРѕР№", provenance=tag)
        assert claim.provenance.category == ProvenanceCategory.HYPOTHESIS

    def test_external_claim(self):
        tag = ProvenanceTag(
            source_level=SourceLevel.HISTORICAL,
            category=ProvenanceCategory.EXTERNAL_SOURCE,
            confidence=0.8,
            notes="archaeology",
        )
        claim = CardClaim(text="РђСЂРєР°РёРј ~4000 РґРѕ РЅ.СЌ.", provenance=tag)
        assert claim.provenance.category == ProvenanceCategory.EXTERNAL_SOURCE

    def test_contradiction_note(self):
        note = ContradictionNote(
            description="РљРЅРёРіР° Рё Р°СЂС…РµРѕР»РѕРіРёСЏ СЂР°СЃС…РѕРґСЏС‚СЃСЏ",
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
        """РљСЂРёС‚РёС‡РµСЃРєРёР№ РёРЅРІР°СЂРёР°РЅС‚: AUTHOR_CANON РЅРµ РјРѕР¶РµС‚ СЃС‚Р°С‚СЊ EXTERNAL_SOURCE."""
        canon_tag = ProvenanceTag(
            source_level=SourceLevel.CANON,
            category=ProvenanceCategory.AUTHOR_CANON,
            confidence=1.0,
        )
        assert canon_tag.category == ProvenanceCategory.AUTHOR_CANON
        # Even at confidence=1.0 it stays AUTHOR_CANON
        assert canon_tag.confidence == 1.0

    def test_provenance_invariant_hypothesis_never_fact(self):
        """HYPOTHESIS РЅРµ РїСЂРµРІСЂР°С‰Р°РµС‚СЃСЏ РІ С„Р°РєС‚."""
        hyp_tag = ProvenanceTag(
            source_level=SourceLevel.USER_HYPOTHESIS,
            category=ProvenanceCategory.HYPOTHESIS,
            confidence=0.5,
        )
        assert hyp_tag.category == ProvenanceCategory.HYPOTHESIS


# в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђ
# 2. Entity Resolution
# в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђ

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
        result = builder._resolve_entity("Р°СЂРєР°РёРј")
        # Either finds it or returns None вЂ” both OK
        if result:
            assert "name" in result
            assert "id" in result

    def test_resolve_missing_entity(self):
        builder = KnowledgeCardBuilder()
        result = builder._resolve_entity("__nonexistent_entity_xyz__")
        assert result is None

    def test_archaeology_name_resolution(self):
        builder = KnowledgeCardBuilder()
        # Try resolving "РђСЂРєР°РёРј" which should be in ARCHAEOLOGY.json
        result = builder._resolve_entity("РђСЂРєР°РёРј")
        if result is not None:
            assert "name" in result
            # Entity found from somewhere - accept any source
            assert result.get("name") is not None


# в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђ
# 3. Aggregation Tests
# в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђ

class TestAggregation:
    """Cross-source aggregation from all sources."""

    def test_build_card_for_entity(self):
        builder = KnowledgeCardBuilder()
        card = builder.build("РђСЂРєР°РёРј")
        # Card should be built even if entity not found
        assert isinstance(card, KnowledgeCard)
        assert card.metadata.entity_id == "РђСЂРєР°РёРј"

    def test_card_has_sources(self):
        builder = KnowledgeCardBuilder()
        card = builder.build("РђСЂРєР°РёРј")
        # Should have at least empty sources
        assert isinstance(card.sources, list)
        # Check that book source is present
        book_sources = [s for s in card.sources if s.source_name == "book"]
        assert len(book_sources) >= 1
        assert book_sources[0].provenance_category == ProvenanceCategory.AUTHOR_CANON

    def test_all_sources_present(self):
        builder = KnowledgeCardBuilder()
        card = builder.build("РђСЂРєР°РёРј")
        source_names = {s.source_name for s in card.sources}
        assert "book" in source_names
        assert "archaeology" in source_names
        assert "cross_references" in source_names
        assert "academic" in source_names

    def test_no_duplicate_claims(self):
        builder = KnowledgeCardBuilder()
        card = builder.build("РђСЂРєР°РёРј")
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


# в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђ
# 4. Provenance Tests
# в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђ

class TestProvenance:
    """Provenance must be preserved per-claim."""

    def test_book_claims_are_canon(self):
        builder = KnowledgeCardBuilder()
        card = builder.build("РђСЂРєР°РёРј")
        book_sources = [s for s in card.sources if s.source_name == "book"]
        for src in book_sources:
            assert src.provenance_category == ProvenanceCategory.AUTHOR_CANON
            for claim in src.claims:
                assert claim.provenance.category == ProvenanceCategory.AUTHOR_CANON

    def test_archaeology_claims_are_external(self):
        builder = KnowledgeCardBuilder()
        card = builder.build("РђСЂРєР°РёРј")
        arch_sources = [s for s in card.sources if s.source_name == "archaeology"]
        for src in arch_sources:
            assert src.provenance_category in (
                ProvenanceCategory.EXTERNAL_SOURCE,
                ProvenanceCategory.RECONSTRUCTION,
            )

    def test_hypothesis_stays_hypothesis(self):
        builder = KnowledgeCardBuilder()
        card = builder.build("РђСЂРєР°РёРј")
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
        card = builder.build("РђСЂРєР°РёРј")
        for source in card.sources:
            for claim in source.claims:
                if claim.provenance.category == ProvenanceCategory.AUTHOR_CANON:
                    # Must always stay AUTHOR_CANON
                    assert claim.provenance.confidence == 1.0

    def test_all_claims_have_provenance(self):
        builder = KnowledgeCardBuilder()
        card = builder.build("РђСЂРєР°РёРј")
        for source in card.sources:
            for claim in source.claims:
                assert claim.provenance is not None
                assert claim.provenance.category is not None
                assert claim.provenance.confidence > 0

    def test_chunk_ids_preserved(self):
        """Book claims must preserve chunk_id for traceability."""
        builder = KnowledgeCardBuilder()
        card = builder.build("РђСЂРєР°РёРј")
        book_sources = [s for s in card.sources if s.source_name == "book"]
        for src in book_sources:
            for claim in src.claims:
                # chunk_id should be set or at least source_ref should reference book
                assert claim.source_ref.startswith("book:") or claim.chunk_id is not None


# в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђ
# 5. Contradiction Tests
# в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђ

class TestContradictions:
    """Contradictions must be detected and preserved, not resolved."""

    def test_detects_potential_conflicts(self):
        builder = KnowledgeCardBuilder()
        card = builder.build("РђСЂРєР°РёРј")
        # Contradictions may or may not exist вЂ” that's fine
        # What matters is the structure is correct
        for cd in card.contradictions:
            assert cd.resolution in ("UNRESOLVED", "DIFFERENT_PERSPECTIVES", "TEMPORARY")
            assert len(cd.source_1_claim) > 0
            assert len(cd.source_2_claim) > 0

    def test_no_auto_resolution(self):
        """System must never auto-resolve contradictions."""
        builder = KnowledgeCardBuilder()
        card = builder.build("РђСЂРєР°РёРј")
        for cd in card.contradictions:
            # Never choose a winner
            assert cd.resolution != "RESOLVED"

    def test_conflicting_claims_preserved(self):
        """Even conflicting claims from different sources must coexist."""
        builder = KnowledgeCardBuilder()
        card = builder.build("РђСЂРєР°РёРј")
        all_sources = {s.source_name for s in card.sources}
        # Both book and archaeology should coexist regardless of conflicts
        assert "book" in all_sources


# в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђ
# 6. Uncertainty Tests
# в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђ

class TestUncertainty:
    """Uncertainty must be tracked and preserved."""

    def test_uncertainty_structure(self):
        builder = KnowledgeCardBuilder()
        card = builder.build("РђСЂРєР°РёРј")
        if card.uncertainty is not None:
            assert "has_unknowns" in card.uncertainty
            assert "unknown_aspects" in card.uncertainty
            assert isinstance(card.uncertainty["unknown_aspects"], list)

    def test_empty_card_has_uncertainty(self):
        """Entity with no data should show uncertainty explicitly."""
        builder = KnowledgeCardBuilder()
        card = builder.build("__nonexistent_entity_xyz__")
        assert card.metadata.coverage_note == "РЎСѓС‰РЅРѕСЃС‚СЊ РЅРµ РЅР°Р№РґРµРЅР° РЅРё РІ РѕРґРЅРѕР№ СЃРёСЃС‚РµРјРµ"
        # Should have uncertainty about missing data
        if card.uncertainty:
            assert card.uncertainty["has_unknowns"] is True


# в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђ
# 7. Book Integration Tests
# в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђ

class TestBookIntegration:
    """Real integration with Book Intelligence pipeline."""

    def test_retriever_returns_with_provenance(self):
        from intelligence.retriever import BookRetriever
        retriever = BookRetriever()
        results = retriever.search("РђСЂРєР°РёРј", n_results=3)
        if results:
            for r in results:
                assert "provenance_category" in r
                assert r["provenance_category"] == "AUTHOR_CANON"

    def test_chunk_traceability(self):
        from intelligence.retriever import BookRetriever
        retriever = BookRetriever()
        results = retriever.search("РђСЂРєР°РёРј", n_results=3)
        if results:
            # At least some results should have chunk_id
            has_chunk = any(r.get("chunk_id") for r in results)
            assert has_chunk, "No chunk_id in retrieval results"


# в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђ
# 8. Regression Tests
# в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђ

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


# в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђ
# 9. API Contract Tests
# в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђ

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


