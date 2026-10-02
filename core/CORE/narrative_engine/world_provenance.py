"""Read-only World Engine provenance contract (B4-A).

This contract does not infer provenance and does not merge World Engine data
with canonical WorldModel/Temporal provenance.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class WorldEntityProvenance(BaseModel):
    """Provenance values explicitly present on a World Engine entity."""

    model_config = ConfigDict(extra="allow")

    status: str
    source: str | None = None
    source_category: str | None = None
    source_level: str | None = None
    notes: str | None = None
    confidence: float | None = None
    source_file: str | None = None


_MARKER_FIELDS = ("source", "provenance_category", "provenance_notes", "source_level", "confidence")


def normalize_world_provenance(
    entity: dict[str, Any], *, source_file: str | None = None
) -> WorldEntityProvenance:
    """Return only provenance values that exist in the raw World Engine entity.

    Missing values stay ``None`` and produce ``status="missing"``. This function
    does not calculate confidence, infer a source, or read canonical data.
    """
    values = {
        "source": entity.get("source"),
        "source_category": entity.get("provenance_category"),
        "source_level": entity.get("source_level"),
        "notes": entity.get("provenance_notes"),
        "confidence": entity.get("confidence"),
        "source_file": source_file,
    }
    has_marker = any(entity.get(field) is not None for field in _MARKER_FIELDS)
    return WorldEntityProvenance(status="available" if has_marker else "missing", **values)
