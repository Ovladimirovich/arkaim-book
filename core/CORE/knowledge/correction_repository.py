"""M7 — persistence and lifecycle for Knowledge temporal corrections."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from schemas.correction import CorrectionRecord, CorrectionStatus


class CorrectionRepository:
    """Durable correction lineage; canonical mutation remains in M10 manager."""

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self.path = self.data_dir / "corrections.json"
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
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, record: CorrectionRecord) -> CorrectionRecord:
        records = self._load()
        records[record.id] = record.model_dump(mode="json")
        self._save(records)
        return record

    def get(self, correction_id: str) -> CorrectionRecord | None:
        value = self._load().get(correction_id)
        return CorrectionRecord.model_validate(value) if value else None

    def list(self, *, status: str | None = None, subject_id: str | None = None) -> list[CorrectionRecord]:
        result = [CorrectionRecord.model_validate(value) for value in self._load().values()]
        if status is not None:
            result = [record for record in result if record.status.value == status]
        if subject_id is not None:
            result = [record for record in result if record.subject_id == subject_id]
        return result

    def confirm(
        self,
        correction_id: str,
        *,
        replacement_claim_id: str,
        decision_by: str,
        decided_at: str,
        affected_reasoning_ids: list[str] | None = None,
    ) -> CorrectionRecord:
        record = self.get(correction_id)
        if record is None:
            raise KeyError(f"correction not found: {correction_id}")
        if record.status is not CorrectionStatus.PENDING:
            raise ValueError(f"correction is not pending: {record.status.value}")
        updated = record.model_copy(update={
            "status": CorrectionStatus.CONFIRMED,
            "replacement_claim_id": replacement_claim_id,
            "decision_by": decision_by,
            "decided_at": decided_at,
            "affected_reasoning_ids": affected_reasoning_ids or record.affected_reasoning_ids,
        })
        return self.add(updated)

    def reject(self, correction_id: str, *, reason: str, decision_by: str, decided_at: str) -> CorrectionRecord:
        record = self.get(correction_id)
        if record is None:
            raise KeyError(f"correction not found: {correction_id}")
        if record.status is not CorrectionStatus.PENDING:
            raise ValueError(f"correction is not pending: {record.status.value}")
        updated = record.model_copy(update={
            "status": CorrectionStatus.REJECTED,
            "reason": reason,
            "decision_by": decision_by,
            "decided_at": decided_at,
        })
        return self.add(updated)

    def stale_reasoning_ids(self, *, subject_id: str | None = None) -> set[str]:
        result: set[str] = set()
        for record in self.list(subject_id=subject_id):
            if record.status is CorrectionStatus.CONFIRMED:
                result.update(record.affected_reasoning_ids)
        return result


__all__ = ["CorrectionRepository"]