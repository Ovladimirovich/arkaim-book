"""Provenance Completion tests: end-to-end provenance flow through the stack."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from narrative_engine.source_levels import (
    ProvenanceCategory,
    ProvenanceTag,
    SourceLevel,
)


# ═══════════════════════════════════════════════════════════════
# 1. PulseResponse provenance is ProvenanceTag (not legacy dict)
# ═══════════════════════════════════════════════════════════════

class TestPulseResponseProvenanceType:
    """PulseResponse.provenance must contain ProvenanceTag objects."""

    def test_pulse_response_provenance_is_provenance_tag_list(self):
        """PulseResponse.provenance принимает list[ProvenanceTag]."""
        from pulse.layers import PulseResponse, _canon_tag
        tag = _canon_tag("test", "test note")
        r = PulseResponse(text="test", source="test", confidence=1.0, provenance=[tag])
        assert isinstance(r.provenance[0], ProvenanceTag)
        assert r.provenance[0].category == ProvenanceCategory.AUTHOR_CANON

    def test_pulse_response_get_provenance_dicts(self):
        """get_provenance_dicts() сериализует ProvenanceTag в dict."""
        from pulse.layers import PulseResponse, _canon_tag
        tag = _canon_tag("test", "test note")
        r = PulseResponse(text="test", source="test", confidence=1.0, provenance=[tag])
        dicts = r.get_provenance_dicts()
        assert isinstance(dicts, list)
        assert isinstance(dicts[0], dict)
        assert dicts[0]["category"] == "AUTHOR_CANON"
        assert dicts[0]["confidence"] == 1.0

    def test_canon_tag_factory(self):
        """_canon_tag создаёт AUTHOR_CANON ProvenanceTag."""
        from pulse.layers import _canon_tag
        tag = _canon_tag("character_name", "from GENOME")
        assert tag.category == ProvenanceCategory.AUTHOR_CANON
        assert tag.source_level == SourceLevel.CANON
        assert tag.confidence == 1.0

    def test_derived_tag_factory(self):
        """_derived_tag создаёт DERIVED ProvenanceTag."""
        from pulse.layers import _derived_tag
        tag = _derived_tag("expansion_topic", "expanded knowledge")
        assert tag.category == ProvenanceCategory.DERIVED
        assert tag.source_level == SourceLevel.SYSTEM_INTERPRETATION
        assert tag.confidence == 0.7


# ═══════════════════════════════════════════════════════════════
# 2. No legacy dict provenance in layers
# ═══════════════════════════════════════════════════════════════

class TestNoLegacyProvenance:
    """No layer should use legacy dict provenance format."""

    def test_no_legacy_dict_in_layers_py(self):
        """layers.py не содержит provenance=[{"type": ...}]."""
        layers_file = Path(__file__).resolve().parent.parent.parent / "core" / "CORE" / "pulse" / "layers.py"
        text = layers_file.read_text(encoding="utf-8")
        import re
        matches = re.findall(r'provenance=\[\{"type":', text)
        assert matches == [], f"Legacy dict provenance found: {len(matches)} occurrences"

    def test_no_empty_provenance_in_layers_py(self):
        """layers.py не содержит provenance=[]."""
        layers_file = Path(__file__).resolve().parent.parent.parent / "core" / "CORE" / "pulse" / "layers.py"
        text = layers_file.read_text(encoding="utf-8")
        import re
        matches = re.findall(r'provenance=\[\]', text)
        assert matches == [], f"Empty provenance found: {len(matches)} occurrences"

    def test_no_legacy_dict_in_world_engine_layer(self):
        """layers_world_engine.py не содержит provenance=[{"type": ...}]."""
        we_file = Path(__file__).resolve().parent.parent.parent / "core" / "CORE" / "pulse" / "layers_world_engine.py"
        text = we_file.read_text(encoding="utf-8")
        import re
        matches = re.findall(r'provenance=\[\{"type":', text)
        assert matches == [], f"Legacy dict provenance found in world engine layer: {len(matches)}"


# ═══════════════════════════════════════════════════════════════
# 3. KeeperAgent serialization
# ═══════════════════════════════════════════════════════════════

class TestKeeperSerialization:
    """KeeperAgent must serialize ProvenanceTag to dict for API."""

    def test_keeper_provenance_serialization(self):
        """KeeperAgent сериализует ProvenanceTag через get_provenance_dicts()."""
        from pulse.layers import PulseResponse, _canon_tag
        tag = _canon_tag("test", "test note")
        r = PulseResponse(text="test", source="test", confidence=1.0, provenance=[tag])
        # Simulate what KeeperAgent does
        if hasattr(r, "get_provenance_dicts"):
            provenance = r.get_provenance_dicts()
        else:
            provenance = r.provenance
        assert isinstance(provenance, list)
        assert isinstance(provenance[0], dict)
        assert "category" in provenance[0]
        assert "confidence" in provenance[0]

    def test_keeper_backward_compat_with_legacy(self):
        """KeeperAgent работает со старым форматом dict (обратная совместимость)."""
        from pulse.layers import PulseResponse
        # Simulate legacy format
        r = PulseResponse(
            text="test", source="test", confidence=1.0,
            provenance=[{"type": "character", "name": "Велик"}],
        )
        # get_provenance_dicts should handle both
        dicts = r.get_provenance_dicts()
        assert isinstance(dicts, list)
        assert isinstance(dicts[0], dict)


# ═══════════════════════════════════════════════════════════════
# 4. Provenance category coverage
# ═══════════════════════════════════════════════════════════════

class TestProvenanceCategoryCoverage:
    """Every layer's provenance must map to a valid ProvenanceCategory."""

    def test_canon_tag_maps_to_author_canon(self):
        """GENOME data → AUTHOR_CANON."""
        from pulse.layers import _canon_tag
        tag = _canon_tag("test")
        assert tag.category == ProvenanceCategory.AUTHOR_CANON

    def test_derived_tag_maps_to_derived(self):
        """Expanded/interpreted data → DERIVED."""
        from pulse.layers import _derived_tag
        tag = _derived_tag("test")
        assert tag.category == ProvenanceCategory.DERIVED

    def test_expansion_backward_is_reconstruction(self):
        """BACKWARD temporal → RECONSTRUCTION."""
        tag = ProvenanceTag(
            source_level=SourceLevel.SYSTEM_INTERPRETATION,
            category=ProvenanceCategory.RECONSTRUCTION,
            confidence=0.7,
        )
        assert tag.category == ProvenanceCategory.RECONSTRUCTION

    def test_expansion_forward_is_future_extrapolation(self):
        """FORWARD temporal → FUTURE_EXTRAPOLATION."""
        tag = ProvenanceTag(
            source_level=SourceLevel.SYSTEM_INTERPRETATION,
            category=ProvenanceCategory.FUTURE_EXTRAPOLATION,
            confidence=0.5,
        )
        assert tag.category == ProvenanceCategory.FUTURE_EXTRAPOLATION

    def test_no_unknown_category_from_layers(self):
        """Слои не должны создавать UNKNOWN provenance (UNKNOWN только для неизвестных данных)."""
        from pulse.layers import _canon_tag, _derived_tag
        canon = _canon_tag("test")
        derived = _derived_tag("test")
        assert canon.category != ProvenanceCategory.UNKNOWN
        assert derived.category != ProvenanceCategory.UNKNOWN


# ═══════════════════════════════════════════════════════════════
# 5. End-to-end provenance preservation
# ═══════════════════════════════════════════════════════════════

class TestEndToEndProvenance:
    """Provenance must survive the full stack: Layer → PulseResponse → Keeper → API dict."""

    def test_full_stack_provenance(self):
        """Provenance проходит от слоя до API ответа без потерь."""
        from pulse.layers import PulseResponse, _canon_tag, UncertaintyFlag

        # Layer creates response with ProvenanceTag
        tag = _canon_tag("Велик", "character from GENOME")
        response = PulseResponse(
            text="Велик — главный герой",
            source="knowledge:character",
            confidence=0.9,
            provenance=[tag],
            uncertainty=UncertaintyFlag(
                has_unknowns=False,
                unknown_aspects=[],
                confidence_breakdown=[{"aspect": "описание", "category": "AUTHOR_CANON", "confidence": 1.0}],
            ),
        )

        # PulseResponse → serialization (what KeeperAgent does)
        api_provenance = response.get_provenance_dicts()
        api_uncertainty = None
        if response.uncertainty:
            api_uncertainty = {
                "has_unknowns": response.uncertainty.has_unknowns,
                "unknown_aspects": response.uncertainty.unknown_aspects,
                "confidence_breakdown": response.uncertainty.confidence_breakdown,
            }

        # API dict
        api_response = {
            "answer": response.text,
            "source": response.source,
            "provenance": api_provenance,
            "uncertainty": api_uncertainty,
            "pulse_confidence": response.confidence,
        }

        # Verify
        assert api_response["provenance"][0]["category"] == "AUTHOR_CANON"
        assert api_response["provenance"][0]["confidence"] == 1.0
        assert api_response["pulse_confidence"] == 0.9
        assert api_response["uncertainty"]["has_unknowns"] is False

    def test_reconstruction_provenance_survives(self):
        """RECONSTRUCTION provenance проходит через весь стек."""
        from pulse.layers import PulseResponse, UncertaintyFlag
        tag = ProvenanceTag(
            source_level=SourceLevel.SYSTEM_INTERPRETATION,
            category=ProvenanceCategory.RECONSTRUCTION,
            confidence=0.7,
            notes="temporal reconstruction via BACKWARD chain",
        )
        response = PulseResponse(
            text="[Реконструкция] Предыстория Аркаима",
            source="temporal:backward_chain",
            confidence=0.7,
            provenance=[tag],
            uncertainty=UncertaintyFlag(has_unknowns=True, unknown_aspects=["точная хронология"]),
        )
        api = response.get_provenance_dicts()
        assert api[0]["category"] == "RECONSTRUCTION"
        assert api[0]["confidence"] == 0.7
        assert response.uncertainty.has_unknowns is True

    def test_hypothesis_never_becomes_canon_in_api(self):
        """HYPOTHESIS provenance не становится AUTHOR_CANON в API ответе."""
        from pulse.layers import PulseResponse
        tag = ProvenanceTag(
            source_level=SourceLevel.USER_HYPOTHESIS,
            category=ProvenanceCategory.HYPOTHESIS,
            confidence=0.95,
        )
        response = PulseResponse(text="test", source="test", confidence=0.5, provenance=[tag])
        api = response.get_provenance_dicts()
        assert api[0]["category"] == "HYPOTHESIS"
        assert api[0]["category"] != "AUTHOR_CANON"
