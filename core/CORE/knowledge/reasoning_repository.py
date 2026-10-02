"""M6 durable read-only repository for ReasoningResult records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from schemas.reasoning import ReasoningResult


class ReasoningRepository:
    """Persist typed reasoning results without mutation or inference logic."""

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self.path = self.data_dir / "reasoning.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self.path.is_file():
            return {}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _save(self, value: dict[str, dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, record: ReasoningResult) -> ReasoningResult:
        records = self._load()
        records[record.id] = record.model_dump(mode="json")
        self._save(records)
        return record

    def get(self, reasoning_id: str) -> ReasoningResult | None:
        value = self._load().get(reasoning_id)
        return ReasoningResult.model_validate(value) if value else None

    def list(self, *, subject_id: str | None = None, status: str | None = None) -> list[ReasoningResult]:
        result: list[ReasoningResult] = []
        for value in self._load().values():
            try:
                record = ReasoningResult.model_validate(value)
            except ValueError:
                continue
            if status is not None and record.status.value != status:
                continue
            if subject_id is not None:
                subject_ids = {str(i.get("subject_id", "")) for i in record.metadata.get("subjects", []) if isinstance(i, dict)}
                if subject_id not in subject_ids:
                    continue
            result.append(record)
        return result


__all__ = ["ReasoningRepository"]