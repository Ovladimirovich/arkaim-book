"""TemporalGap — явное представление временного пробела.

M2: UNKNOWN GAP — не ошибка, а валидное состояние.
Система не заполняет пробелы автоматически.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class EvidenceStatus(str, Enum):
    """Статус доказательств для временного пробела.

    INSUFFICIENT_DATA — валидный результат, не ошибка.
    """

    DOCUMENTED = "DOCUMENTED"
    """Пробел документирован (известно, что пропустили)."""

    PARTIALLY_DOCUMENTED = "PARTIALLY_DOCUMENTED"
    """Частично документирован (есть фрагментарные данные)."""

    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    """Недостаточно данных. ВАЛИДНОЕ СОСТОЯНИЕ, не ошибка."""

    RECONSTRUCTABLE = "RECONSTRUCTABLE"
    """Может быть реконструирован при наличии новых данных."""

    HYPOTHETICAL = "HYPOTHETICAL"
    """Гипотетический пробел (предполагаемый, но не подтверждённый)."""

    UNKNOWN = "UNKNOWN"
    """Статус не определён."""


@dataclass
class TemporalGap:
    """Временной пробел между двумя узлами.

    Минимальная семантика:
      id, from_node, to_node, reason, evidence_status, candidate_bridges
    """

    id: str
    from_node: str
    to_node: str
    reason: str = ""
    evidence_status: EvidenceStatus = EvidenceStatus.INSUFFICIENT_DATA
    candidate_bridges: list[str] = field(default_factory=list)
    notes: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    # ── Properties ───────────────────────────────────────────────────

    @property
    def is_documented(self) -> bool:
        return self.evidence_status in (
            EvidenceStatus.DOCUMENTED,
            EvidenceStatus.PARTIALLY_DOCUMENTED,
        )

    @property
    def is_reconstructable(self) -> bool:
        return self.evidence_status == EvidenceStatus.RECONSTRUCTABLE

    @property
    def is_hypothetical(self) -> bool:
        return self.evidence_status == EvidenceStatus.HYPOTHETICAL

    @property
    def has_insufficient_data(self) -> bool:
        """Валидный статус — не ошибка."""
        return self.evidence_status == EvidenceStatus.INSUFFICIENT_DATA

    @property
    def bridge_count(self) -> int:
        return len(self.candidate_bridges)

    # ── Serialization ────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "from_node": self.from_node,
            "to_node": self.to_node,
            "reason": self.reason,
            "evidence_status": self.evidence_status.value,
            "candidate_bridges": self.candidate_bridges,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TemporalGap":
        status_val = data.get("evidence_status", "INSUFFICIENT_DATA")
        try:
            status = EvidenceStatus(status_val)
        except ValueError:
            status = EvidenceStatus.INSUFFICIENT_DATA
        return cls(
            id=data["id"],
            from_node=data["from_node"],
            to_node=data["to_node"],
            reason=data.get("reason", ""),
            evidence_status=status,
            candidate_bridges=data.get("candidate_bridges", []),
            notes=data.get("notes", ""),
        )

    @staticmethod
    def unknown_gap(gap_id: str, from_id: str, to_id: str, reason: str = "") -> "TemporalGap":
        """Создать пробел с INSUFFICIENT_DATA — валидное состояние."""
        return TemporalGap(
            id=f"gap_{gap_id}",
            from_node=from_id,
            to_node=to_id,
            reason=reason or "Данные недостаточны для определения временной связи",
            evidence_status=EvidenceStatus.INSUFFICIENT_DATA,
        )

    @staticmethod
    def reconstructable_gap(gap_id: str, from_id: str, to_id: str, bridges: list[str]) -> "TemporalGap":
        """Создать реконструируемый пробел."""
        return TemporalGap(
            id=f"gap_{gap_id}",
            from_node=from_id,
            to_node=to_id,
            evidence_status=EvidenceStatus.RECONSTRUCTABLE,
            candidate_bridges=bridges,
            reason="Возможна реконструкция при наличии новых данных",
        )
