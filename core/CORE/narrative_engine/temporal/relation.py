"""TemporalRelationType и TemporalRelation — типизированные временные связи.

M2: типизированные временные отношения между TemporalNode.
Особенно важны DEVELOPS_FROM и TRANSFORMS_INTO для моделирования линии развития.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from narrative_engine.source_levels import ProvenanceCategory, ProvenanceTag, SourceLevel


class TemporalRelationType(str, Enum):
    """Типы временных отношений между узлами.

    Минимум 11 типов для полной temporal семантики.
    """

    BEFORE = "BEFORE"
    """A происходит до B."""

    AFTER = "AFTER"
    """A происходит после B."""

    OVERLAPS = "OVERLAPS"
    """A и B пересекаются во времени."""

    CONTAINS = "CONTAINS"
    """A содержит B (B внутри временных границ A)."""

    CONTAINED_BY = "CONTAINED_BY"
    """A содержится в B."""

    CONTEMPORARY_WITH = "CONTEMPORARY_WITH"
    """A и B существовали одновременно."""

    PRECEDES = "PRECEDES"
    """A предшествует B (строгий порядок, без пересечения)."""

    FOLLOWS = "FOLLOWS"
    """A следует за B."""

    DEVELOPS_FROM = "DEVELOPS_FROM"
    """A развивается из B (качественное развитие, не просто порядок)."""

    TRANSFORMS_INTO = "TRANSFORMS_INTO"
    """A трансформируется в B (качественное изменение)."""

    COEXISTS_WITH = "COEXISTS_WITH"
    """A и B сосуществуют (аналог CONTEMPORARY_WITH, но для сущностей)."""

    CARRIES = "CARRIES"
    """A несёт/хранит знание B (character → knowledge/teaching)."""

    CARRIED_BY = "CARRIED_BY"
    """Обратный к CARRIES: знание B несётся A."""

    TRANSMITS_TO = "TRANSMITS_TO"
    """A передаёт знание B (character → character, учитель → ученик)."""

    RECEIVES_FROM = "RECEIVES_FROM"
    """Обратный к TRANSMITS_TO: B получает знание от A."""

    ECHOES = "ECHOES"
    """A зеркалит/аналогично B (epoch ↔ epoch, НЕ причинная связь)."""

    UNKNOWN = "UNKNOWN"
    """Временная связь не определена."""


# Обратные отношения
REVERSE_RELATIONS: dict[TemporalRelationType, TemporalRelationType] = {
    TemporalRelationType.BEFORE: TemporalRelationType.AFTER,
    TemporalRelationType.AFTER: TemporalRelationType.BEFORE,
    TemporalRelationType.OVERLAPS: TemporalRelationType.OVERLAPS,
    TemporalRelationType.CONTAINS: TemporalRelationType.CONTAINED_BY,
    TemporalRelationType.CONTAINED_BY: TemporalRelationType.CONTAINS,
    TemporalRelationType.CONTEMPORARY_WITH: TemporalRelationType.CONTEMPORARY_WITH,
    TemporalRelationType.PRECEDES: TemporalRelationType.FOLLOWS,
    TemporalRelationType.FOLLOWS: TemporalRelationType.PRECEDES,
    TemporalRelationType.DEVELOPS_FROM: TemporalRelationType.TRANSFORMS_INTO,
    TemporalRelationType.TRANSFORMS_INTO: TemporalRelationType.DEVELOPS_FROM,
    TemporalRelationType.COEXISTS_WITH: TemporalRelationType.COEXISTS_WITH,
    TemporalRelationType.CARRIES: TemporalRelationType.CARRIED_BY,
    TemporalRelationType.CARRIED_BY: TemporalRelationType.CARRIES,
    TemporalRelationType.TRANSMITS_TO: TemporalRelationType.RECEIVES_FROM,
    TemporalRelationType.RECEIVES_FROM: TemporalRelationType.TRANSMITS_TO,
    TemporalRelationType.ECHOES: TemporalRelationType.ECHOES,
}


@dataclass
class TemporalRelation:
    """Временная связь между двумя TemporalNode.

    min семантика:
      id, source_id, target_id, relation_type, strength, provenance
    """

    id: str
    source_id: str
    target_id: str
    relation_type: TemporalRelationType
    strength: float = 1.0
    description: str = ""
    provenance: list[ProvenanceTag] = field(default_factory=list)
    confidence: float = 0.5
    epoch: str = ""
    bidirectional: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    # ── Properties ───────────────────────────────────────────────────

    @property
    def reverse_type(self) -> TemporalRelationType:
        """Обратный тип отношения."""
        return REVERSE_RELATIONS.get(self.relation_type, TemporalRelationType.UNKNOWN)

    @property
    def is_canon(self) -> bool:
        return any(p.category == ProvenanceCategory.AUTHOR_CANON for p in self.provenance)

    @property
    def is_developmental(self) -> bool:
        """Является ли relation relation развития (DEVELOPS_FROM / TRANSFORMS_INTO)."""
        return self.relation_type in (
            TemporalRelationType.DEVELOPS_FROM,
            TemporalRelationType.TRANSFORMS_INTO,
        )

    @property
    def is_contextual(self) -> bool:
        """Является ли relation контекстальной (не часть хронологической оси PRECEDES)."""
        return self.relation_type in (
            TemporalRelationType.CARRIES,
            TemporalRelationType.CARRIED_BY,
            TemporalRelationType.TRANSMITS_TO,
            TemporalRelationType.RECEIVES_FROM,
            TemporalRelationType.ECHOES,
            TemporalRelationType.DEVELOPS_FROM,
            TemporalRelationType.TRANSFORMS_INTO,
            TemporalRelationType.CONTEMPORARY_WITH,
            TemporalRelationType.COEXISTS_WITH,
        )

    # ── Factory ──────────────────────────────────────────────────────

    @staticmethod
    def develops_from(source_id: str, target_id: str, strength: float = 0.8) -> "TemporalRelation":
        """A развивается из B."""
        return TemporalRelation(
            id=f"tr_{source_id}_{target_id}_dev",
            source_id=source_id,
            target_id=target_id,
            relation_type=TemporalRelationType.DEVELOPS_FROM,
            strength=strength,
            provenance=[ProvenanceTag(
                source_level=SourceLevel.SYSTEM_INTERPRETATION,
                category=ProvenanceCategory.HYPOTHESIS,
                confidence=strength,
                notes="developmental relation — requires archaeological confirmation",
            )],
        )

    @staticmethod
    def transforms_into(source_id: str, target_id: str, strength: float = 0.7) -> "TemporalRelation":
        """A трансформируется в B."""
        return TemporalRelation(
            id=f"tr_{source_id}_{target_id}_trans",
            source_id=source_id,
            target_id=target_id,
            relation_type=TemporalRelationType.TRANSFORMS_INTO,
            strength=strength,
            provenance=[ProvenanceTag(
                source_level=SourceLevel.SYSTEM_INTERPRETATION,
                category=ProvenanceCategory.HYPOTHESIS,
                confidence=strength,
                notes="transformative relation — requires archaeological confirmation",
            )],
        )

    @staticmethod
    def precedes(source_id: str, target_id: str, strength: float = 1.0) -> "TemporalRelation":
        """A предшествует B (строгий порядок).

        ADR TEMPORAL §4: PRECEDES-рёбра оси = DERIVED (порядок выведен из канона,
        не прямое утверждение текста). НИКОГДА AUTHOR_CANON.
        """
        return TemporalRelation(
            id=f"tr_{source_id}_{target_id}_prec",
            source_id=source_id,
            target_id=target_id,
            relation_type=TemporalRelationType.PRECEDES,
            strength=strength,
            provenance=[ProvenanceTag(
                source_level=SourceLevel.SYSTEM_INTERPRETATION,
                category=ProvenanceCategory.DERIVED,
                confidence=strength,
                notes="temporal precedence — derived from epoch ordering in canon",
            )],
        )

    @staticmethod
    def contemporary_with(source_id: str, target_id: str, strength: float = 0.6) -> "TemporalRelation":
        """A и B существовали одновременно."""
        return TemporalRelation(
            id=f"tr_{source_id}_{target_id}_cont",
            source_id=source_id,
            target_id=target_id,
            relation_type=TemporalRelationType.CONTEMPORARY_WITH,
            strength=strength,
            provenance=[ProvenanceTag(
                source_level=SourceLevel.SYSTEM_INTERPRETATION,
                category=ProvenanceCategory.HYPOTHESIS,
                confidence=strength,
                notes="contemporary — requires evidence",
            )],
        )

    @staticmethod
    def carries(source_id: str, target_id: str, description: str = "", strength: float = 0.8) -> "TemporalRelation":
        """A несёт/хранит знание B (character → knowledge/teaching)."""
        return TemporalRelation(
            id=f"tr_{source_id}_{target_id}_carries",
            source_id=source_id,
            target_id=target_id,
            relation_type=TemporalRelationType.CARRIES,
            strength=strength,
            description=description,
            provenance=[ProvenanceTag(
                source_level=SourceLevel.AUTHOR_INTERPRETATION,
                category=ProvenanceCategory.AUTHOR_CANON,
                confidence=strength,
                notes="carrier relation — character carries knowledge/teaching",
            )],
        )

    @staticmethod
    def transmits_to(source_id: str, target_id: str, description: str = "", strength: float = 0.8) -> "TemporalRelation":
        """A передаёт знание B (учитель → ученик)."""
        return TemporalRelation(
            id=f"tr_{source_id}_{target_id}_transmit",
            source_id=source_id,
            target_id=target_id,
            relation_type=TemporalRelationType.TRANSMITS_TO,
            strength=strength,
            description=description,
            provenance=[ProvenanceTag(
                source_level=SourceLevel.AUTHOR_INTERPRETATION,
                category=ProvenanceCategory.AUTHOR_CANON,
                confidence=strength,
                notes="transmission relation — knowledge passes from teacher to student",
            )],
        )

    @staticmethod
    def echoes(source_id: str, target_id: str, description: str = "", strength: float = 0.5) -> "TemporalRelation":
        """A зеркалит/аналогично B (epoch ↔ epoch, НЕ причинная связь)."""
        return TemporalRelation(
            id=f"tr_{source_id}_{target_id}_echoes",
            source_id=source_id,
            target_id=target_id,
            relation_type=TemporalRelationType.ECHOES,
            strength=strength,
            description=description,
            provenance=[ProvenanceTag(
                source_level=SourceLevel.SYSTEM_INTERPRETATION,
                category=ProvenanceCategory.HYPOTHESIS,
                confidence=strength,
                notes="structural parallel — not historical causation",
            )],
        )

    # ── Serialization ────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "strength": self.strength,
            "description": self.description,
            "provenance": [p.to_dict() for p in self.provenance],
            "confidence": self.confidence,
            "epoch": self.epoch,
            "bidirectional": self.bidirectional,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TemporalRelation":
        rt_val = data.get("relation_type", "UNKNOWN")
        relation_type = TemporalRelationType(rt_val) if rt_val else TemporalRelationType.UNKNOWN
        provenance = [ProvenanceTag.from_dict(p) for p in data.get("provenance", [])]
        return cls(
            id=data["id"],
            source_id=data["source_id"],
            target_id=data["target_id"],
            relation_type=relation_type,
            strength=data.get("strength", 1.0),
            description=data.get("description", ""),
            provenance=provenance,
            confidence=data.get("confidence", 0.5),
            epoch=data.get("epoch", ""),
            bidirectional=data.get("bidirectional", False),
        )
