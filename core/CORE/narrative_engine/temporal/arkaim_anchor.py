"""ArkaimAnchor — специальный temporal anchor для Аркаима.

M2: ARKAIM как special temporal anchor.
Не создаёт новых авторских утверждений об Аркаиме.
Использует только существующие данные (arkaim_era epoch, arkaim location).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from narrative_engine.source_levels import ProvenanceCategory, ProvenanceTag, SourceLevel
from narrative_engine.temporal.node import TemporalNode
from narrative_engine.temporal.precision import TemporalPrecision


@dataclass
class ArkaimAnchor:
    """Специальный temporal anchor для Аркаима.

    Содержит:
      - stable ID
      - temporal bounds (как известно)
      - provenance (канон + археология)
      - связи с археологическими данными
      - связи с авторским канонгом
    """

    id: str = "arkaim_anchor"
    label: str = "Аркаим — temporal anchor"
    epoch_id: str = "arkaim_era"
    location_id: str = "arkaim"
    precision: TemporalPrecision = TemporalPrecision.RELATIVE
    provenance: list[ProvenanceTag] = field(default_factory=list)
    archaeological_links: list[str] = field(default_factory=list)
    canon_links: list[str] = field(default_factory=list)
    notes: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    # ── Properties ───────────────────────────────────────────────────

    @property
    def is_canon_anchor(self) -> bool:
        """Якорь основан на авторском каноне."""
        return any(p.category == ProvenanceCategory.AUTHOR_CANON for p in self.provenance)

    @property
    def has_archaeological_support(self) -> bool:
        return len(self.archaeological_links) > 0

    @property
    def node(self) -> TemporalNode:
        """Представление якоря как TemporalNode."""
        return TemporalNode(
            id=f"temporal_{self.id}",
            label=self.label,
            precision=self.precision,
            era_id=self.epoch_id,
            entity_ids=[self.location_id] + self.canon_links,
            provenance=self.provenance,
            confidence=0.7 if self.has_archaeological_support else 0.5,
            is_anchor=True,
            notes=self.notes,
        )

    # ── Factory ──────────────────────────────────────────────────────

    @staticmethod
    def from_existing_data() -> "ArkaimAnchor":
        """Создать ArkaimAnchor из существующих данных (без новых утверждений)."""
        provenance = [
            ProvenanceTag(
                source_level=SourceLevel.CANON,
                category=ProvenanceCategory.AUTHOR_CANON,
                confidence=1.0,
                source_title="КНИГА.md",
                notes="arkaim_era epoch from book canon",
            ),
            ProvenanceTag(
                source_level=SourceLevel.HISTORICAL,
                category=ProvenanceCategory.EXTERNAL_SOURCE,
                confidence=0.7,
                source_title="ARCHAEOLOGY.json",
                notes="archaeological evidence for Arkaim site",
            ),
        ]
        return ArkaimAnchor(
            epoch_id="arkaim_era",
            location_id="arkaim",
            precision=TemporalPrecision.RELATIVE,
            provenance=provenance,
            archaeological_links=["arkaim_site", "bronze_age_culture"],
            canon_links=["arkaim_era", "hyperborea", "ritual_center"],
            notes="Temporal anchor for Arkaim — based on existing canon + archaeological data",
        )

    # ── Serialization ────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "epoch_id": self.epoch_id,
            "location_id": self.location_id,
            "precision": self.precision.value,
            "provenance": [p.to_dict() for p in self.provenance],
            "archaeological_links": self.archaeological_links,
            "canon_links": self.canon_links,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ArkaimAnchor":
        provenance = [ProvenanceTag.from_dict(p) for p in data.get("provenance", [])]
        return cls(
            id=data.get("id", "arkaim_anchor"),
            label=data.get("label", "Аркаим — temporal anchor"),
            epoch_id=data.get("epoch_id", "arkaim_era"),
            location_id=data.get("location_id", "arkaim"),
            precision=TemporalPrecision(data.get("precision", "RELATIVE")),
            provenance=provenance,
            archaeological_links=data.get("archaeological_links", []),
            canon_links=data.get("canon_links", []),
            notes=data.get("notes", ""),
        )
