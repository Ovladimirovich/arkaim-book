import sys
from pathlib import Path

CORE = Path(__file__).resolve().parents[4] / "core" / "CORE"
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))

from narrative_engine.world_engine import WorldEngine
from narrative_engine.world_provenance import normalize_world_provenance


def test_available_provenance_preserves_explicit_values():
    result = normalize_world_provenance(
        {
            "source": "MAP_DATA.json",
            "provenance_category": "EXTERNAL_SOURCE",
            "provenance_notes": "Археологический факт",
            "source_level": "HISTORICAL",
            "confidence": 0.8,
        },
        source_file="core/CORE/WORLD_MODEL/GEOGRAPHY.json",
    )

    assert result.status == "available"
    assert result.source == "MAP_DATA.json"
    assert result.source_category == "EXTERNAL_SOURCE"
    assert result.source_level == "HISTORICAL"
    assert result.notes == "Археологический факт"
    assert result.confidence == 0.8
    assert result.source_file == "core/CORE/WORLD_MODEL/GEOGRAPHY.json"


def test_partial_provenance_does_not_invent_missing_values():
    result = normalize_world_provenance({"source": "GENOME"})

    assert result.status == "available"
    assert result.source == "GENOME"
    assert result.source_category is None
    assert result.source_level is None
    assert result.notes is None
    assert result.confidence is None


def test_missing_provenance_is_explicitly_missing():
    result = normalize_world_provenance({"id": "unknown"})

    assert result.status == "missing"
    assert result.source is None
    assert result.source_category is None
    assert result.source_level is None
    assert result.notes is None
    assert result.confidence is None


def test_confidence_is_not_calculated_when_absent():
    result = normalize_world_provenance({"source": "GENOME", "source_level": "CANON"})

    assert result.confidence is None


def test_world_engine_adds_provenance_without_mutating_index():
    engine = WorldEngine()
    engine._entity_index["test_entity"] = {
        "category": "test",
        "id": "test_entity",
        "source": "GENOME",
        "provenance_category": "AUTHOR_CANON",
        "source_level": "CANON",
    }

    result = engine.get_entity("test_entity")

    assert result is not None
    assert result["provenance"]["status"] == "available"
    assert result["provenance"]["source"] == "GENOME"
    assert "provenance" not in engine._entity_index["test_entity"]
