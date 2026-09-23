"""TemporalNode — временной узел temporal graph.

M2: обёртка над Epoch с временными границами, precision и provenance.
Может представлять как эпоху, так и отдельное событие.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from narrative_engine.source_levels import ProvenanceCategory, ProvenanceTag, SourceLevel
from narrative_engine.temporal.precision import TemporalPrecision


@dataclass
class TemporalBounds:
    """Временные границы узла."""
    start: Optional[str] = None      # "2500 BCE" или None
    end: Optional[str] = None        # "2000 BCE" или None
    start_iso: Optional[datetime] = None  # parsed ISO datetime (if available)
    end_iso: Optional[datetime] = None
    uncertainty: Optional[str] = None  # "±200 лет" или None

    def is_finite(self) -> bool:
        """Есть ли обе границы."""
        return self.start is not None and self.end is not None

    def duration_label(self) -> str:
        """Описание длительности."""
        if not self.is_finite():
            return "неизвестно"
        return f"{self.start} — {self.end}"


class TemporalNode:
    """Временной узел temporal graph.

    Минимальная семантика:
      id, label, precision, era_id, entity_ids, event_ids, provenance, confidence

    Примеры:
      TemporalNode(id="arkaim_era", precision=RELATIVE, era_id="arkaim_era")
      TemporalNode(id="today", precision=EXACT, label="Современность")
      TemporalNode(id="gap_between_eras", precision=UNKNOWN, label="Неизвестный пробел")
    """

    def __init__(
        self,
        id: str,
        label: str,
        precision: TemporalPrecision = TemporalPrecision.UNKNOWN,
        era_id: str = "",
        entity_ids: Optional[list[str]] = None,
        event_ids: Optional[list[str]] = None,
        provenance: Optional[list[ProvenanceTag]] = None,
        confidence: float = 0.5,
        bounds: Optional[TemporalBounds] = None,
        notes: str = "",
        is_anchor: bool = False,
    ):
        self.id = id
        self.label = label
        self.precision = precision
        self.era_id = era_id
        self.entity_ids = entity_ids or []
        self.event_ids = event_ids or []
        self.provenance = provenance or []
        self.confidence = max(0.0, min(1.0, confidence))
        self.bounds = bounds or TemporalBounds()
        self.notes = notes
        self.is_anchor = is_anchor
        self.created_at = datetime.now(tz=timezone.utc)
        self.updated_at = datetime.now(tz=timezone.utc)

    # ── Properties ─────────────────────────────────────────────────────

    @property
    def is_known_temporal(self) -> bool:
        """Есть ли временные границы (не UNKNOWN precision)."""
        return self.precision != TemporalPrecision.UNKNOWN

    @property
    def has_bounds(self) -> bool:
        """Есть ли обе временные границы."""
        return self.bounds.is_finite()

    @property
    def is_canon(self) -> bool:
        """Является ли узел каноническим."""
        return any(p.category == ProvenanceCategory.AUTHOR_CANON for p in self.provenance)

    @property
    def is_external(self) -> bool:
        return any(p.category == ProvenanceCategory.EXTERNAL_SOURCE for p in self.provenance)

    @property
    def is_hypothesis(self) -> bool:
        return any(p.category == ProvenanceCategory.HYPOTHESIS for p in self.provenance)

    @property
    def is_reconstruction(self) -> bool:
        return any(p.category == ProvenanceCategory.RECONSTRUCTION for p in self.provenance)

    @property
    def is_gap(self) -> bool:
        """Является ли узел временным пробелом."""
        return self.precision == TemporalPrecision.UNKNOWN and self.era_id == ""

    # ── Factory methods ────────────────────────────────────────────────

    @staticmethod
    def from_epoch(
        epoch_id: str,
        epoch_name_ru: str,
        epoch_order: int,
        precision: TemporalPrecision = TemporalPrecision.RELATIVE,
        bounds: Optional[TemporalBounds] = None,
        provenance: Optional[list[ProvenanceTag]] = None,
    ) -> "TemporalNode":
        """Создать TemporalNode из Epoch."""
        return TemporalNode(
            id=f"temporal_{epoch_id}",
            label=epoch_name_ru,
            precision=precision,
            era_id=epoch_id,
            provenance=provenance or [],
            bounds=bounds or TemporalBounds(),
            notes=f"Epoch order: {epoch_order}",
        )

    @staticmethod
    def present_anchor() -> "TemporalNode":
        """Создать узел «Современность».

        M8.1: provenance = HYPOTHESIS — методологическая точка отсчёта,
        НЕ AUTHOR_CANON (present day reader's reality не является каноном книги).
        """
        return TemporalNode(
            id="temporal_today",
            label="Современность",
            precision=TemporalPrecision.EXACT,
            bounds=TemporalBounds(start="2025 CE", end="2025 CE"),
            provenance=[ProvenanceTag(
                source_level=SourceLevel.SYSTEM_INTERPRETATION,
                category=ProvenanceCategory.HYPOTHESIS,
                confidence=1.0,
                notes="methodological anchor for temporal reconstruction — not book canon",
            )],
            confidence=1.0,
        )

    @staticmethod
    def gap_node(gap_id: str, label: str = "Неизвестный пробел") -> "TemporalNode":
        """Создать узел-пробел."""
        return TemporalNode(
            id=f"temporal_gap_{gap_id}",
            label=label,
            precision=TemporalPrecision.UNKNOWN,
            provenance=[ProvenanceTag(
                source_level=SourceLevel.SYSTEM_INTERPRETATION,
                category=ProvenanceCategory.HYPOTHESIS,
                confidence=0.0,
                notes="gap — no data",
            )],
            confidence=0.0,
            notes="TEMPORAL GAP — evidence insufficient",
        )

    # ── Serialization ──────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "precision": self.precision.value,
            "era_id": self.era_id,
            "entity_ids": self.entity_ids,
            "event_ids": self.event_ids,
            "provenance": [p.to_dict() for p in self.provenance],
            "confidence": self.confidence,
            "bounds": {
                "start": self.bounds.start,
                "end": self.bounds.end,
                "uncertainty": self.bounds.uncertainty,
            } if self.bounds.start or self.bounds.end else None,
            "notes": self.notes,
            "is_anchor": self.is_anchor,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TemporalNode":
        prec_val = data.get("precision", "UNKNOWN")
        precision = TemporalPrecision(prec_val) if prec_val else TemporalPrecision.UNKNOWN
        bounds_data = data.get("bounds")
        bounds = TemporalBounds(
            start=bounds_data.get("start") if bounds_data else None,
            end=bounds_data.get("end") if bounds_data else None,
            uncertainty=bounds_data.get("uncertainty") if bounds_data else None,
        ) if bounds_data else TemporalBounds()
        provenance = [ProvenanceTag.from_dict(p) for p in data.get("provenance", [])]
        return cls(
            id=data["id"],
            label=data["label"],
            precision=precision,
            era_id=data.get("era_id", ""),
            entity_ids=data.get("entity_ids", []),
            event_ids=data.get("event_ids", []),
            provenance=provenance,
            confidence=data.get("confidence", 0.5),
            bounds=bounds,
            notes=data.get("notes", ""),
            is_anchor=data.get("is_anchor", False),
        )
