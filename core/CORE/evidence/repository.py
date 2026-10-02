"""M2 — Evidence repository.

Persistence boundary for Evidence records. Evidence is stored as a separate
Knowledge Core record next to the existing Book OS / source infrastructure.
It is not stored inside WorldModel and it does not become a second authority
store for claims.

Policy (M2 STOP GATE):
  * Evidence records are addressed by their stable ``Evidence.id``.
  * Records are append/overwrite by id only; there is no bulk rewrite of the
    Book OS source layer.
  * The physical backend is a JSON directory, mirroring ``SourceStore``.
    The domain contract does not depend on the physical backend.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from schemas.evidence import ClaimEvidenceLink, Evidence, EvidenceStatus

OS_DATA_DIR = Path(__file__).resolve().parents[2] / "OS_DATA"


class EvidenceNotFoundError(KeyError):
    """Raised when an Evidence record cannot be found by id."""


class ClaimEvidenceLinkNotFoundError(KeyError):
    """Raised when a claim→evidence link cannot be found by id."""


class EvidenceRepository:
    """Immutable-by-id store of Evidence records.

    Each record is saved as ``{data_dir}/evidence/{evidence_id}.json``.
    Re-adding the same id (e.g. the same source/locator/hash) overwrites the
    identical record; changing content yields a different ``Evidence.id``.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = Path(data_dir) if data_dir is not None else OS_DATA_DIR
        self._evidence_dir = self.data_dir / "evidence"
        self._evidence_dir.mkdir(parents=True, exist_ok=True)

    def add(self, evidence: Evidence) -> Evidence:
        """Persist evidence keyed by its stable id."""
        path = self._path_for(evidence.id)
        path.write_text(
            json.dumps(evidence.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return evidence

    def get(self, evidence_id: str) -> Evidence:
        path = self._path_for(evidence_id)
        if not path.exists():
            raise EvidenceNotFoundError(f"Evidence not found: {evidence_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return Evidence(**data)

    def find(self, evidence_id: str) -> Optional[Evidence]:
        """Return evidence or None without raising."""
        try:
            return self.get(evidence_id)
        except EvidenceNotFoundError:
            return None

    def list(self) -> List[Evidence]:
        records: List[Evidence] = []
        for path in sorted(self._evidence_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                records.append(Evidence(**data))
            except Exception:
                continue
        return records

    def count(self) -> int:
        return len(list(self._evidence_dir.glob("*.json")))

    def _path_for(self, evidence_id: str) -> Path:
        return self._evidence_dir / f"{evidence_id}.json"


class ClaimEvidenceLinkRepository:
    """Persistent store of claim→evidence links with lifecycle status.

    Links are never deleted when a reference breaks. A broken reference moves to
    ``UNAVAILABLE`` (or ``SUPERSEDED`` when the fragment changed and a new
    version replaced it); the original record is kept as history. This mirrors
    the M2 STOP GATE policy: no silent deletion, no fabricated evidence.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = Path(data_dir) if data_dir is not None else OS_DATA_DIR
        self._links_dir = self.data_dir / "evidence_links"
        self._links_dir.mkdir(parents=True, exist_ok=True)

    def add(self, link: ClaimEvidenceLink) -> ClaimEvidenceLink:
        path = self._path_for(link.link_id)
        path.write_text(
            json.dumps(link.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return link

    def get(self, link_id: str) -> ClaimEvidenceLink:
        path = self._path_for(link_id)
        if not path.exists():
            raise ClaimEvidenceLinkNotFoundError(f"ClaimEvidenceLink not found: {link_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return ClaimEvidenceLink(**data)

    def find(self, link_id: str) -> Optional[ClaimEvidenceLink]:
        try:
            return self.get(link_id)
        except ClaimEvidenceLinkNotFoundError:
            return None

    def for_claim(self, claim_id: str) -> List[ClaimEvidenceLink]:
        return [link for link in self.list() if link.claim_id == claim_id]

    def list(self) -> List[ClaimEvidenceLink]:
        records: List[ClaimEvidenceLink] = []
        for path in sorted(self._links_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                records.append(ClaimEvidenceLink(**data))
            except Exception:
                continue
        return records

    def mark_status(
        self,
        link_id: str,
        status: EvidenceStatus,
        *,
        reason: str = "",
    ) -> ClaimEvidenceLink:
        """Update lifecycle status while keeping the record (never deletes)."""
        from datetime import datetime, timezone

        link = self.get(link_id)
        link.status = status
        if reason:
            link.reason = reason
        link.checked_at = datetime.now(tz=timezone.utc)
        return self.add(link)

    def _path_for(self, link_id: str) -> Path:
        return self._links_dir / f"{link_id}.json"


__all__ = [
    "EvidenceRepository",
    "EvidenceNotFoundError",
    "ClaimEvidenceLinkRepository",
    "ClaimEvidenceLinkNotFoundError",
]
