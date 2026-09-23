"""TemporalChain — направленный temporal граф эпох.

M2: двунаправленная цепочка (BACKWARD / FORWARD) с явными пробелами.
Не заполняет пробелы автоматически.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from narrative_engine.source_levels import ProvenanceCategory, ProvenanceTag, SourceLevel
from narrative_engine.temporal.node import TemporalNode
from narrative_engine.temporal.relation import TemporalRelation, TemporalRelationType
from narrative_engine.temporal.gap import TemporalGap


class ChainDirection(str, Enum):
    """Направление temporal chain."""

    BACKWARD = "BACKWARD"
    """Текст: TODAY → HISTORY → ARKAIM (реконструкция)."""

    FORWARD = "FORWARD"
    """Текст: ARKAIM → DEVELOPMENT → TODAY → FUTURE (развитие)."""

    BI_DIRECTIONAL = "BI_DIRECTIONAL"
    """Оба направления."""


@dataclass
class TemporalChain:
    """Направленный temporal граф.

    Поддерживает:
      - BACKWARD: TODAY → ... → ARKAIM
      - FORWARD: ARKAIM → ... → TODAY → FUTURE
      - branching: ветвление от узлов
      - non-continuous: UNKNOWN GAP между узлами
    """

    id: str
    label: str
    direction: ChainDirection
    nodes: list[TemporalNode] = field(default_factory=list)
    relations: list[TemporalRelation] = field(default_factory=list)
    gaps: list[TemporalGap] = field(default_factory=list)
    provenance: list[ProvenanceTag] = field(default_factory=list)
    confidence: float = 0.5
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    # ── Methods ──────────────────────────────────────────────────────

    def add_node(self, node: TemporalNode) -> None:
        """Добавить узел в chain."""
        self.nodes.append(node)
        self.updated_at = datetime.now(tz=timezone.utc)

    def add_relation(self, rel: TemporalRelation) -> None:
        """Добавить relation."""
        self.relations.append(rel)
        self.updated_at = datetime.now(tz=timezone.utc)

    def add_gap(self, gap: TemporalGap) -> None:
        """Добавить временной пробел."""
        self.gaps.append(gap)
        self.updated_at = datetime.now(tz=timezone.utc)

    def get_node(self, node_id: str) -> Optional[TemporalNode]:
        """Получить узел по ID."""
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def get_relation(self, rel_id: str) -> Optional[TemporalRelation]:
        """Получить relation по ID."""
        for r in self.relations:
            if r.id == rel_id:
                return r
        return None

    def get_outgoing_relations(self, node_id: str) -> list[TemporalRelation]:
        """Все outgoing relations от узла."""
        return [r for r in self.relations if r.source_id == node_id]

    def get_incoming_relations(self, node_id: str) -> list[TemporalRelation]:
        """Все incoming relations к узлу."""
        return [r for r in self.relations if r.target_id == node_id]

    def has_gap_between(self, from_id: str, to_id: str) -> bool:
        """Есть ли пробел между двумя узлами."""
        for gap in self.gaps:
            if gap.from_node == from_id or gap.to_node == to_id:
                if gap.from_node == from_id and gap.to_node == to_id:
                    return True
        return False

    def get_gaps(self) -> list[TemporalGap]:
        """Все пробелы в chain."""
        return self.gaps

    @property
    def gap_count(self) -> int:
        return len(self.gaps)

    def is_continuous(self) -> bool:
        """Является ли chain непрерывной (без каких-либо пробелов)."""
        return len(self.gaps) == 0

    def stats(self) -> dict:
        """Статистика chain."""
        return {
            "id": self.id,
            "label": self.label,
            "direction": self.direction.value,
            "nodes": len(self.nodes),
            "relations": len(self.relations),
            "gaps": len(self.gaps),
            "continuous": self.is_continuous(),
            "confidence": self.confidence,
        }

    # ── Factory ──────────────────────────────────────────────────────

    @staticmethod
    def backward_from_today(todays_nodes: list[TemporalNode]) -> "TemporalChain":
        """Создать BACKWARD chain от современности к прошлому."""
        chain = TemporalChain(
            id="backward_chain",
            label="Текст: Современность → Прошлое",
            direction=ChainDirection.BACKWARD,
            nodes=list(todays_nodes),
            provenance=[ProvenanceTag(
                source_level=SourceLevel.SYSTEM_INTERPRETATION,
                category=ProvenanceCategory.HYPOTHESIS,
                confidence=0.5,
                notes="backward reconstruction chain — hypotheses pending evidence",
            )],
        )
        return chain

    @staticmethod
    def forward_from_arkaim(arkaim_nodes: list[TemporalNode]) -> "TemporalChain":
        """Создать FORWARD chain от Аркаима к будущему."""
        chain = TemporalChain(
            id="forward_chain",
            label="Текст: Аркаим → Развитие → Будущее",
            direction=ChainDirection.FORWARD,
            nodes=list(arkaim_nodes),
            provenance=[ProvenanceTag(
                source_level=SourceLevel.SYSTEM_INTERPRETATION,
                category=ProvenanceCategory.HYPOTHESIS,
                confidence=0.5,
                notes="forward development chain — hypotheses pending evidence",
            )],
        )
        return chain

    # ── Serialization ────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "direction": self.direction.value,
            "nodes": [n.to_dict() for n in self.nodes],
            "relations": [r.to_dict() for r in self.relations],
            "gaps": [g.to_dict() for g in self.gaps],
            "provenance": [p.to_dict() for p in self.provenance],
            "confidence": self.confidence,
            "stats": self.stats(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TemporalChain":
        direction = ChainDirection(data.get("direction", "BACKWARD"))
        nodes = [TemporalNode.from_dict(n) for n in data.get("nodes", [])]
        relations = [TemporalRelation.from_dict(r) for r in data.get("relations", [])]
        gaps = []
        for g in data.get("gaps", []):
            from narrative_engine.temporal.gap import TemporalGap
            gaps.append(TemporalGap.from_dict(g))
        provenance = [ProvenanceTag.from_dict(p) for p in data.get("provenance", [])]
        return cls(
            id=data["id"],
            label=data["label"],
            direction=direction,
            nodes=nodes,
            relations=relations,
            gaps=gaps,
            provenance=provenance,
            confidence=data.get("confidence", 0.5),
        )
