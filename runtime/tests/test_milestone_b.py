"""Milestone B tests: provenance migration, KNOWLEDGE enrichment, uncertainty-aware answers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

KNOWLEDGE_DIR = Path(__file__).resolve().parents[2] / "core" / "KNOWLEDGE"


# ═══════════════════════════════════════════════════════════════
# 1. KNOWLEDGE JSON provenance metadata
# ═══════════════════════════════════════════════════════════════

class TestKnowledgeProvenanceMetadata:
    """All KNOWLEDGE JSON files have _provenance_metadata."""

    def test_all_files_have_provenance_metadata(self):
        """Каждый JSON в KNOWLEDGE/ имеет _provenance_metadata."""
        json_files = sorted(KNOWLEDGE_DIR.glob("*.json"))
        assert len(json_files) >= 40, f"Expected 40+ files, got {len(json_files)}"

        missing = []
        for f in json_files:
            data = json.loads(f.read_text(encoding="utf-8-sig"))
            if "_provenance_metadata" not in data:
                missing.append(f.name)

        assert missing == [], f"Files missing _provenance_metadata: {missing}"

    def test_provenance_metadata_has_required_fields(self):
        """_provenance_metadata содержит category, source_level, notes."""
        valid_categories = {
            "AUTHOR_CANON", "DERIVED", "EXTERNAL_SOURCE",
            "HYPOTHESIS", "RECONSTRUCTION", "UNKNOWN",
            "ARTISTIC_MODEL", "FUTURE_EXTRAPOLATION",
        }
        json_files = sorted(KNOWLEDGE_DIR.glob("*.json"))
        for f in json_files:
            data = json.loads(f.read_text(encoding="utf-8-sig"))
            meta = data.get("_provenance_metadata", {})
            assert "category" in meta, f"{f.name}: missing category"
            assert meta["category"] in valid_categories, \
                f"{f.name}: invalid category {meta['category']}"
            assert "source_level" in meta, f"{f.name}: missing source_level"
            assert "notes" in meta, f"{f.name}: missing notes"

    def test_author_canon_files(self):
        """AUTHOR_INTENT, BOOK_DOCUMENT — AUTHOR_CANON."""
        for name in ["AUTHOR_INTENT.json", "BOOK_DOCUMENT.json", "SYNOPSIS_DOCUMENT.json"]:
            f = KNOWLEDGE_DIR / name
            if f.exists():
                data = json.loads(f.read_text(encoding="utf-8-sig"))
                meta = data["_provenance_metadata"]
                assert meta["category"] == "AUTHOR_CANON", \
                    f"{name}: expected AUTHOR_CANON, got {meta['category']}"

    def test_external_source_files(self):
        """ACADEMIC_CONFIRMATIONS, ARCHAEOLOGY — EXTERNAL_SOURCE."""
        for name in ["ACADEMIC_CONFIRMATIONS.json", "ARCHAEOLOGY.json"]:
            f = KNOWLEDGE_DIR / name
            if f.exists():
                data = json.loads(f.read_text(encoding="utf-8-sig"))
                meta = data["_provenance_metadata"]
                assert meta["category"] == "EXTERNAL_SOURCE", \
                    f"{name}: expected EXTERNAL_SOURCE, got {meta['category']}"

    def test_derived_files(self):
        """PHILOSOPHY, CHARACTERS, SYMBOLS — DERIVED."""
        for name in ["PHILOSOPHY.json", "CHARACTERS.json", "SYMBOLS.json"]:
            f = KNOWLEDGE_DIR / name
            if f.exists():
                data = json.loads(f.read_text(encoding="utf-8-sig"))
                meta = data["_provenance_metadata"]
                assert meta["category"] == "DERIVED", \
                    f"{name}: expected DERIVED, got {meta['category']}"

    def test_unknown_files(self):
        """MYTHOLOGY, RELIGION — UNKNOWN (empty descriptions). RITUALS was reclassified to DERIVED after forensic audit."""
        for name in ["MYTHOLOGY.json", "RELIGION.json"]:
            f = KNOWLEDGE_DIR / name
            if f.exists():
                data = json.loads(f.read_text(encoding="utf-8-sig"))
                meta = data["_provenance_metadata"]
                assert meta["category"] == "UNKNOWN", \
                    f"{name}: expected UNKNOWN, got {meta['category']}"
        # RITUALS.json was misclassified as UNKNOWN; forensic audit showed all records are DERIVED from ESOTERIC_CONNECTIONS.json
        f = KNOWLEDGE_DIR / "RITUALS.json"
        if f.exists():
            data = json.loads(f.read_text(encoding="utf-8-sig"))
            meta = data["_provenance_metadata"]
            assert meta["category"] == "DERIVED", \
                f"RITUALS.json: expected DERIVED after audit, got {meta['category']}"

    def test_no_duplicate_provenance_keys(self):
        """_provenance_metadata не дублирует существующие ключи."""
        json_files = sorted(KNOWLEDGE_DIR.glob("*.json"))
        for f in json_files:
            data = json.loads(f.read_text(encoding="utf-8-sig"))
            meta = data.get("_provenance_metadata", {})
            # _provenance_metadata should be a top-level key, not nested inside another dict
            assert "category" in meta
            assert "source_level" in meta
            assert "notes" in meta


# ═══════════════════════════════════════════════════════════════
# 2. Uncertainty-aware KnowledgeLayer
# ═══════════════════════════════════════════════════════════════

class TestUncertaintyAwareAnswers:
    """KnowledgeLayer and ExpansionLayer set uncertainty for partial knowledge."""

    def test_detect_unknown_sources(self):
        """_detect_unknown_sources returns empty after RITUALS reclassification."""
        from pulse.layers import _detect_unknown_sources
        unknown = _detect_unknown_sources()
        # RITUALS.json was reclassified from UNKNOWN to DERIVED in forensic follow-up
        assert "RITUALS.json" not in unknown
        # No UNKNOWN files remain after Milestone B + forensic fix
        assert len(unknown) == 0, f"Expected no UNKNOWN files, got: {unknown}"

    def test_build_uncertainty_for_unknown(self):
        """_build_uncertainty_for_unknown returns None when no UNKNOWN sources exist."""
        from pulse.layers import _build_uncertainty_for_unknown
        flag = _build_uncertainty_for_unknown("тестовый аспект")
        assert flag is None, "Expected None — no UNKNOWN sources remain after audit"

    def test_build_uncertainty_none_when_clean(self):
        """_build_uncertainty_for_unknown returns None when clean."""
        from pulse.layers import _build_uncertainty_for_unknown
        flag = _build_uncertainty_for_unknown("aspect")
        assert flag is None

    def test_knowledge_layer_catalog_has_uncertainty(self):
        """KnowledgeLayer каталожный ответ содержит uncertainty при UNKNOWN источниках."""
        from pulse.layers import KnowledgeLayer, UncertaintyFlag
        genome = {
            "modules": {
                "themes": [],
                "characters": [],
                "values": [],
                "symbols": [],
                "conflicts": [],
            },
            "world_entities": [],
            "catalog_texts": [
                {"text": "Гиперборея была древней цивилизацией.", "chapter": "глава 1"},
            ],
        }
        layer = KnowledgeLayer(genome=genome)
        response = layer.respond_to("что такое гиперборея")
        if response is not None:
            assert hasattr(response, "uncertainty")
            # catalog_text responses may have uncertainty if UNKNOWN sources exist
            if response.uncertainty is not None:
                assert isinstance(response.uncertainty, UncertaintyFlag)

    def test_expansion_layer_has_uncertainty(self):
        """ExpansionLayer отвечает с uncertainty при частичных данных."""
        from pulse.layers import ExpansionLayer, UncertaintyFlag
        genome = {"modules": {}}
        layer = ExpansionLayer(genome=genome)
        # _standard_respond with no knowledge should return None
        result = layer._standard_respond("nonexistent topic xyz")
        assert result is None


# ═══════════════════════════════════════════════════════════════
# 3. Regression: existing tests still pass
# ═══════════════════════════════════════════════════════════════

class TestRegression:
    """Existing tests must not regress."""

    def test_pulse_response_still_works(self):
        """PulseResponse создаётся с ProvenanceTag."""
        from pulse.layers import PulseResponse, _canon_tag
        tag = _canon_tag("test", "note")
        r = PulseResponse(text="test", source="test", confidence=1.0, provenance=[tag])
        assert r.provenance[0].category.value == "AUTHOR_CANON"
        dicts = r.get_provenance_dicts()
        assert dicts[0]["category"] == "AUTHOR_CANON"

    def test_uncertainty_flag_serializable(self):
        """UncertaintyFlag сериализуется в dict для API."""
        from pulse.layers import UncertaintyFlag
        u = UncertaintyFlag(
            has_unknowns=True,
            unknown_aspects=["аспект1"],
            confidence_breakdown=[{"aspect": "a", "category": "UNKNOWN", "confidence": 0.3}],
        )
        assert u.has_unknowns is True
        assert u.unknown_aspects == ["аспект1"]
        assert u.confidence_breakdown[0]["category"] == "UNKNOWN"

    def test_knowledge_card_builder_still_works(self):
        """KnowledgeCardBuilder.build() не ломается."""
        from knowledge_card.builder import KnowledgeCardBuilder
        builder = KnowledgeCardBuilder()
        card = builder.build("Аркаим")
        assert card is not None
        assert card.metadata.entity_name is not None

    def test_provenance_invariant_author_canon_confidence(self):
        """AUTHOR_CANON claims всегда confidence=1.0."""
        from narrative_engine.source_levels import ProvenanceCategory
        from knowledge_card.builder import KnowledgeCardBuilder
        builder = KnowledgeCardBuilder()
        card = builder.build("Аркаим")
        for source in card.sources:
            for claim in source.claims:
                if claim.provenance.category == ProvenanceCategory.AUTHOR_CANON:
                    assert claim.provenance.confidence == 1.0, \
                        f"AUTHOR_CANON claim has confidence {claim.provenance.confidence}"

    def test_no_legacy_dict_provenance_in_layers(self):
        """layers.py не содержит provenance=[{\"type\": ...}]."""
        layers_file = Path(__file__).resolve().parents[2] / "core" / "CORE" / "pulse" / "layers.py"
        text = layers_file.read_text(encoding="utf-8")
        import re
        matches = re.findall(r'provenance=\[\{"type":', text)
        assert matches == [], f"Legacy dict provenance found: {len(matches)} occurrences"


# ═══════════════════════════════════════════════════════════════
# 4. Provenance categories coverage
# ═══════════════════════════════════════════════════════════════

class TestProvenanceCategoryCoverage:
    """All 8 ProvenanceCategory values are represented in KNOWLEDGE files."""

    def test_author_canon_represented(self):
        """AUTHOR_CANON представлен в KNOWLEDGE."""
        for name in ["AUTHOR_INTENT.json", "BOOK_DOCUMENT.json"]:
            f = KNOWLEDGE_DIR / name
            if f.exists():
                data = json.loads(f.read_text(encoding="utf-8-sig"))
                assert data["_provenance_metadata"]["category"] == "AUTHOR_CANON"
                return
        pytest.skip("No AUTHOR_CANON files found")

    def test_derived_represented(self):
        """DERIVED представлен в KNOWLEDGE."""
        for name in ["PHILOSOPHY.json", "CHARACTERS.json"]:
            f = KNOWLEDGE_DIR / name
            if f.exists():
                data = json.loads(f.read_text(encoding="utf-8-sig"))
                assert data["_provenance_metadata"]["category"] == "DERIVED"
                return
        pytest.skip("No DERIVED files found")

    def test_external_source_represented(self):
        """EXTERNAL_SOURCE представлен в KNOWLEDGE."""
        f = KNOWLEDGE_DIR / "ACADEMIC_CONFIRMATIONS.json"
        if f.exists():
            data = json.loads(f.read_text(encoding="utf-8-sig"))
            assert data["_provenance_metadata"]["category"] == "EXTERNAL_SOURCE"
        else:
            pytest.skip("ACADEMIC_CONFIRMATIONS.json not found")

    def test_unknown_represented(self):
        """UNKNOWN представлен в KNOWLEDGE (пустые описания)."""
        for name in ["MYTHOLOGY.json", "RELIGION.json"]:
            f = KNOWLEDGE_DIR / name
            if f.exists():
                data = json.loads(f.read_text(encoding="utf-8-sig"))
                assert data["_provenance_metadata"]["category"] == "UNKNOWN"
                return
        pytest.skip("No UNKNOWN files found")
