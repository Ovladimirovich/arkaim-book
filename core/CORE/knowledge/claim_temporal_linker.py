"""M17 — Claim-Level Temporal Linking registry.

Read-only resolver явных связей claim → temporal-узел. Использует только
подтверждённые связи из claim_temporal_links.json; эвристики запрещены.
Стабильный claim_id для книжных claims вычисляется через CanonClaim.make_id
(тот же контракт, что в knowledge_cards._card_claim_id).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "KNOWLEDGE"
CLAIM_TEMPORAL_LINKS_PATH = KNOWLEDGE_DIR / "claim_temporal_links.json"


@dataclass
class ClaimTemporalLink:
    """Подтверждённая связь claim → temporal-узел."""

    claim_id: str
    temporal_node_id: str
    notes: str = ""


@dataclass
class ClaimTemporalLinker:
    """Read-only реестр связей claim → temporal-узел."""

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
            link = ClaimTemporalLink(
                claim_id=str(item.get("claim_id", "")),
                temporal_node_id=str(item.get("temporal_node_id", "")),
                notes=str(item.get("notes", "")),
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
