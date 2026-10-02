"""M1 — unified claim/provenance compatibility contract tests."""

from __future__ import annotations

import sys
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from narrative_engine.provenance.claim import CanonClaim
from narrative_engine.source_levels import (
    ProvenanceCategory,
    ProvenanceTag,
    SourceLevel,
    normalize_provenance_category,
)
from schemas.fact import Fact


class TestM1ProvenanceMapping:
    def test_legacy_labels_map_without_category_promotion(self):
        assert normalize_provenance_category("source") is ProvenanceCategory.AUTHOR_CANON
        assert normalize_provenance_category("external") is ProvenanceCategory.EXTERNAL_SOURCE
        assert normalize_provenance_category("derived") is ProvenanceCategory.DERIVED
        assert normalize_provenance_category("interpretation") is ProvenanceCategory.RECONSTRUCTION
        assert normalize_provenance_category("hypothesis") is ProvenanceCategory.HYPOTHESIS

    def test_unknown_legacy_label_is_explicit_unknown(self):
        assert normalize_provenance_category("not-a-real-source") is ProvenanceCategory.UNKNOWN

    def test_current_category_labels_are_idempotent(self):
        for category in ProvenanceCategory:
            assert normalize_provenance_category(category) is category
            assert normalize_provenance_category(category.value) is category


class TestM1ClaimContract:
    def test_canon_claim_round_trip_preserves_m1_fields(self):
        claim = CanonClaim.from_canon(
            "Аркаим — древнее городище",
            source_id="book",
            location="chapter:1 paragraph:5",
            entity_ids=["region_arkaim"],
            epoch_ids=["arkaim_era"],
        )

        restored = CanonClaim.from_dict(claim.to_dict())

        assert restored.id == claim.id
        assert restored.category is ProvenanceCategory.AUTHOR_CANON
        assert restored.confidence == 1.0
        assert restored.entity_ids == claim.entity_ids
        assert restored.epoch_ids == claim.epoch_ids

    def test_high_confidence_hypothesis_is_not_promoted(self):
        claim = CanonClaim.from_hypothesis(
            "Аркаим был центром мира",
            source_id="system_analysis",
            location="internal",
            confidence=1.0,
        )
        assert claim.confidence == 1.0
        assert claim.category is ProvenanceCategory.HYPOTHESIS
        assert claim.is_canon is False

    def test_legacy_fact_exposes_category_without_rewriting_label(self):
        fact = Fact(
            statement="Археологическая датировка",
            entity_id="region_arkaim",
            doc_id="archaeology:1",
            provenance="external",
            confidence=0.8,
        )
        assert fact.provenance == "external"
        assert fact.provenance_category() is ProvenanceCategory.EXTERNAL_SOURCE

    def test_legacy_fact_genome_is_canon_category_only(self):
        fact = Fact(
            statement="Геном содержит описание персонажа",
            entity_id="character:1",
            doc_id="genome:1",
            provenance="genome",
        )
        assert fact.provenance_category() is ProvenanceCategory.AUTHOR_CANON
        assert fact.provenance_category() is not ProvenanceCategory.UNKNOWN

    def test_provenance_tag_from_legacy_source_level_maps_to_category(self):
        tag = ProvenanceTag.from_dict(
            {
                "source_level": SourceLevel.CANON.value,
                "confidence": 1.0,
            }
        )
        assert tag.category is ProvenanceCategory.AUTHOR_CANON
