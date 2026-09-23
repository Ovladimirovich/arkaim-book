"""PresentAnchor — якорь современности для исторической реконструкции.

M2: позволяет связать современный объект/процесс с его историческими предшественниками
без автоматического создания связей.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from narrative_engine.source_levels import ProvenanceCategory, ProvenanceTag, SourceLevel
from narrative_engine.temporal.node import TemporalNode
from narrative_engine.temporal.relation import TemporalRelation, TemporalRelationType


@dataclass
class PresentAnchor:
    """Якорь современности — связь современного объекта с историческими слоями.

    Минимальная семантика:
      id, label, modern_entity_id, temporal_nodes, relations, provenance
    """

    id: str
    label: str
    modern_entity_id: str
    temporal_nodes: list[str] = field(default_factory=list)
    relations: list[str] = field(default_factory=list)
    provenance: list[ProvenanceTag] = field(default_factory=list)
    notes: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    # ── Properties ───────────────────────────────────────────────────

    @property
    def is_canon(self) -> bool:
        return any(p.category == ProvenanceCategory.AUTHOR_CANON for p in self.provenance)

    @property
    def node_count(self) -> int:
        return len(self.temporal_nodes)

    # ── Factory ──────────────────────────────────────────────────────

    @staticmethod
    def for_entity(
        entity_id: str,
        label: str,
        provenance_tags: Optional[list[ProvenanceTag]] = None,
        notes: str = "",
    ) -> "PresentAnchor":
        """Создать якорь для современного объекта."""
        return PresentAnchor(
            id=f"present_{entity_id}",
            label=label,
            modern_entity_id=entity_id,
            provenance=provenance_tags or [ProvenanceTag(
                source_level=SourceLevel.CANON,
                category=ProvenanceCategory.AUTHOR_CANON,
                confidence=1.0,
                notes="present anchor — modern reference point",
            )],
            notes=notes,
        )

    # ── Serialization ────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "modern_entity_id": self.modern_entity_id,
            "temporal_nodes": self.temporal_nodes,
            "relations": self.relations,
            "provenance": [p.to_dict() for p in self.provenance],
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PresentAnchor":
        provenance = [ProvenanceTag.from_dict(p) for p in data.get("provenance", [])]
        return cls(
            id=data["id"],
            label=data["label"],
            modern_entity_id=data["modern_entity_id"],
            temporal_nodes=data.get("temporal_nodes", []),
            relations=data.get("relations", []),
            provenance=provenance,
            notes=data.get("notes", ""),
        )
