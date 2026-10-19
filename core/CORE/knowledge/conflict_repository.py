"""M5 — persistence for Knowledge conflict records."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from schemas.conflict import ConflictRecord, ConflictStatus

log = logging.getLogger(__name__)


class ConflictRepository:
    """Small durable repository; claims remain owned by their claim store."""

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self.path = self.data_dir / "conflicts.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self.path.is_file():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _save(self, data: dict[str, dict[str, Any]]) -> None:
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def add(self, record: ConflictRecord) -> ConflictRecord:
        records = self._load()
        records[record.id] = record.model_dump(mode="json")
        self._save(records)
        return record

    def get(self, conflict_id: str) -> ConflictRecord | None:
        data = self._load().get(conflict_id)
        return ConflictRecord.model_validate(data) if data else None

    def list(
        self, *, subject_id: str | None = None, status: str | None = None
    ) -> list[ConflictRecord]:
        result = []
        for value in self._load().values():
            try:
                result.append(ConflictRecord.model_validate(value))
            except Exception:
                log.warning(
                    "conflict_record_validate_failed id=%s", value.get("id", "unknown")
                )
        if subject_id is not None:
            result = [record for record in result if record.subject_id == subject_id]
        if status is not None:
            result = [record for record in result if record.status.value == status]
        return result

    def resolve_with_evidence(
        self,
        conflict_id: str,
        *,
        resolution_claim_id: str,
        resolution_reason: str,
        resolved_at: str,
    ) -> ConflictRecord:
        record = self.get(conflict_id)
        if record is None:
            raise KeyError(f"conflict not found: {conflict_id}")
        updated = record.model_copy(
            update={
                "status": ConflictStatus.RESOLVED_WITH_EVIDENCE,
                "resolution_claim_id": resolution_claim_id,
                "resolution_reason": resolution_reason,
                "resolved_at": resolved_at,
            }
        )
        return self.add(updated)

    def accept_as_perspectives(self, conflict_id: str) -> ConflictRecord:
        record = self.get(conflict_id)
        if record is None:
            raise KeyError(f"conflict not found: {conflict_id}")
        return self.add(
            record.model_copy(
                update={"status": ConflictStatus.ACCEPTED_AS_PERSPECTIVES}
            )
        )


__all__ = ["ConflictRepository"]
