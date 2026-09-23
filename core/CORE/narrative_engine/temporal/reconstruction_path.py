"""ReconstructionPath — путь реконструкции temporal chain.

M2: структура для сохранения пути реконструкции.
Пока только структура, без inference engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from narrative_engine.source_levels import ProvenanceCategory, ProvenanceTag, SourceLevel
from narrative_engine.temporal.node import TemporalNode
from narrative_engine.temporal.relation import TemporalRelation
from narrative_engine.temporal.gap import TemporalGap
from narrative_engine.temporal.chain import ChainDirection


@dataclass
class ReconstructionPath:
    """Путь реконструкции: nodes + relations + gaps.

    Минимальная семантика:
      id, direction, nodes, relations, gaps, provenance, confidence
    """

    id: str
    direction: ChainDirection
    nodes: list[TemporalNode] = field(default_factory=list)
    relations: list[TemporalRelation] = field(default_factory=list)
    gaps: list[TemporalGap] = field(default_factory=list)
    provenance: list[ProvenanceTag] = field(default_factory=list)
    confidence: float = 0.5
    description: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    # ── Properties ───────────────────────────────────────────────────

    @property
    def start_node_id(self) -> Optional[str]:
        return self.nodes[0].id if self.nodes else None

    @property
    def end_node_id(self) -> Optional[str]:
        return self.nodes[-1].id if self.nodes else None

    @property
    def is_complete(self) -> bool:
        """Путь полон (без UNKNOWN GAP)."""
        return all(not g.has_insufficient_data for g in self.gaps)

    @property
    def gap_count(self) -> int:
        return len(self.gaps)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def unknown_gap_count(self) -> int:
        return sum(1 for g in self.gaps if g.has_insufficient_data)

    # ── Methods ──────────────────────────────────────────────────────

    def add_node(self, node: TemporalNode) -> None:
        self.nodes.append(node)
        self.updated_at = datetime.now(tz=timezone.utc)

    def add_relation(self, rel: TemporalRelation) -> None:
        self.relations.append(rel)
        self.updated_at = datetime.now(tz=timezone.utc)

    def add_gap(self, gap: TemporalGap) -> None:
        self.gaps.append(gap)
        self.updated_at = datetime.now(tz=timezone.utc)

    def get_node_at(self, index: int) -> Optional[TemporalNode]:
        if 0 <= index < len(self.nodes):
            return self.nodes[index]
        return None

    def stats(self) -> dict:
        return {
            "id": self.id,
            "direction": self.direction.value,
            "nodes": len(self.nodes),
            "relations": len(self.relations),
            "gaps": len(self.gaps),
            "unknown_gaps": self.unknown_gap_count,
            "is_complete": self.is_complete,
            "confidence": self.confidence,
        }

    # ── Serialization ────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "direction": self.direction.value,
            "nodes": [n.to_dict() for n in self.nodes],
            "relations": [r.to_dict() for r in self.relations],
            "gaps": [g.to_dict() for g in self.gaps],
            "provenance": [p.to_dict() for p in self.provenance],
            "confidence": self.confidence,
            "description": self.description,
            "stats": self.stats(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReconstructionPath":
        from narrative_engine.temporal.chain import ChainDirection
        direction = ChainDirection(data.get("direction", "BACKWARD"))
        nodes = [TemporalNode.from_dict(n) for n in data.get("nodes", [])]
        relations = [TemporalRelation.from_dict(r) for r in data.get("relations", [])]
        gaps = [TemporalGap.from_dict(g) for g in data.get("gaps", [])]
        provenance = [ProvenanceTag.from_dict(p) for p in data.get("provenance", [])]
        return cls(
            id=data["id"],
            direction=direction,
            nodes=nodes,
            relations=relations,
            gaps=gaps,
            provenance=provenance,
            confidence=data.get("confidence", 0.5),
            description=data.get("description", ""),
        )
