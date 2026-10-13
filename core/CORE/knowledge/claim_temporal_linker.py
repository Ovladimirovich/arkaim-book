"""M17/M18 — Claim-Level Temporal Linking registry.

Read-only resolver явных связей claim → temporal-узел (+ каноническое событие).
Использует только подтверждённые связи из claim_temporal_links.json; эвристики
запрещены. Стабильный claim_id для книжных claims вычисляется через
CanonClaim.make_id (тот же контракт, что в knowledge_cards._card_claim_id).

M18: добавлен типизированный event_id. Цепочка claim_id → event_id → epoch_id
→ temporal_node_id валидируется против WORLD_MODEL (каноническое событие
должно существовать, его epoch должен существовать, temporal-узел должен
соответствовать точному epoch события). Невалидная цепочка не выбрасывается
и не подменяется — она помечается и передаётся дальше с явным статусом.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "KNOWLEDGE"
CLAIM_TEMPORAL_LINKS_PATH = KNOWLEDGE_DIR / "claim_temporal_links.json"

# Извлечение event_id из notes (первая часть до ";"), формат M17.3
_EVENT_IN_NOTES_RE = re.compile(r"^(event_[a-z0-9_]+)\s*;")


def _extract_event_id_from_notes(notes: str) -> Optional[str]:
    """Извлечь event_id из notes (формат «event_xxx; …»)."""
    match = _EVENT_IN_NOTES_RE.match(notes.strip())
    return match.group(1) if match else None


@dataclass
class ClaimTemporalLink:
    """Подтверждённая связь claim → temporal-узел (+ каноническое событие)."""

    claim_id: str
    temporal_node_id: str
    notes: str = ""
    event_id: Optional[str] = None  # M18: каноническое событие WORLD_MODEL


@dataclass
class ChainValidation:
    """Результат валидации цепочки claim_id → event_id → epoch_id → temporal_node_id."""

    valid: bool
    event_id: Optional[str] = None
    epoch_id: Optional[str] = None
    temporal_node_id: Optional[str] = None
    reason: str = ""


@dataclass
class ClaimTemporalLinker:
    """Read-only реестр связей claim → temporal-узел (+ событие)."""

    links: list[ClaimTemporalLink] = field(default_factory=list)

    @classmethod
    def from_json(cls, path: Optional[Path] = None) -> "ClaimTemporalLinker":
        """Загрузить подтверждённые связи из JSON файла."""
        path = path or CLAIM_TEMPORAL_LINKS_PATH
        if not path.exists():
            return cls(links=[])

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return cls(links=[])

        links = []
        for item in data:
            notes = str(item.get("notes", ""))
            # M18: явный event_id из JSON приоритетнее извлечения из notes
            event_id = str(item.get("event_id") or "").strip() or None
            if event_id is None:
                event_id = _extract_event_id_from_notes(notes)
            link = ClaimTemporalLink(
                claim_id=str(item.get("claim_id", "")),
                temporal_node_id=str(item.get("temporal_node_id", "")),
                notes=notes,
                event_id=event_id,
            )
            if link.claim_id and link.temporal_node_id:
                links.append(link)

        return cls(links=links)

    def get_links_for_claim(self, claim_id: str) -> list[ClaimTemporalLink]:
        """Получить подтверждённые связи для claim."""
        return [link for link in self.links if link.claim_id == claim_id]

    def has_links(self) -> bool:
        """Есть ли вообще подтверждённые связи."""
        return bool(self.links)

    @staticmethod
    def validate_chain(link: ClaimTemporalLink) -> ChainValidation:
        """M18: проверить цепочку claim_id → event_id → epoch_id → temporal_node_id.

        Событие и эпоха должны существовать в WORLD_MODEL; temporal-узел должен
        соответствовать точному epoch события (temporal_{epoch_id}).
        Нет event_id → valid=False (event_id необязателен по схеме M17, но M18
        требует его для машинно-читаемой связи).
        """
        if not link.event_id:
            return ChainValidation(
                valid=False,
                temporal_node_id=link.temporal_node_id,
                reason="event_id отсутствует",
            )

        try:
            from narrative_engine.world_model import WorldModel

            wm = WorldModel.load()
        except Exception as exc:
            return ChainValidation(
                valid=False,
                event_id=link.event_id,
                temporal_node_id=link.temporal_node_id,
                reason=f"WORLD_MODEL недоступен: {exc}",
            )

        # 1. Событие должно существовать
        event = next((e for e in wm.get_events() if e.id == link.event_id), None)
        if event is None:
            return ChainValidation(
                valid=False,
                event_id=link.event_id,
                temporal_node_id=link.temporal_node_id,
                reason=f"событие {link.event_id} не найдено в WORLD_MODEL",
            )

        # 2. Эпоха события должна существовать
        epoch_id = event.epoch
        epoch = wm.get_epoch(epoch_id)
        if epoch is None:
            return ChainValidation(
                valid=False,
                event_id=link.event_id,
                epoch_id=epoch_id,
                temporal_node_id=link.temporal_node_id,
                reason=f"эпоха {epoch_id} события {link.event_id} не найдена в WORLD_MODEL",
            )

        # 3. Temporal-узел должен соответствовать точному epoch события
        expected_node = f"temporal_{epoch_id}"
        if link.temporal_node_id != expected_node:
            return ChainValidation(
                valid=False,
                event_id=link.event_id,
                epoch_id=epoch_id,
                temporal_node_id=link.temporal_node_id,
                reason=(
                    f"temporal-узел {link.temporal_node_id} не соответствует "
                    f"epoch события {link.event_id} (ожидается {expected_node})"
                ),
            )

        return ChainValidation(
            valid=True,
            event_id=link.event_id,
            epoch_id=epoch_id,
            temporal_node_id=link.temporal_node_id,
            reason="цепочка валидна",
        )
