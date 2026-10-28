"""Lifecycle Store — suggest-only персистентность предложений.

M10-паттерн (``TemporalUpdateManager``), переиспользуемый для гипотез и
сценариев World Explorer:

  - ``propose()``  — только кладёт запись в хранилище; WorldModel не меняется;
  - ``accept()``   — решение человека (явный вызов, обычно editor/admin);
  - ``reject()``   — отклонение без применения;
  - ``supersede()`` — замена записи другой, исходная сохраняется как история.

Инварианты:
  - никакого auto-apply: статус меняется только явным вызовом;
  - записи не удаляются: reject/supersede — это статусы, а не удаление;
  - физический backend — JSON-директория (как ``EvidenceRepository``),
    доменный контракт от backend'а не зависит.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

log = logging.getLogger("hermes.narrative.lifecycle_store")

STATUS_PROPOSED = "proposed"
STATUS_ACCEPTED = "accepted"
STATUS_REJECTED = "rejected"
STATUS_SUPERSEDED = "superseded"

ACTIVE_STATUSES = (STATUS_PROPOSED, STATUS_ACCEPTED)


class LifecycleRecord(BaseModel):
    """Одна запись жизненного цикла (гипотеза или сценарий)."""

    record_id: str
    status: str = STATUS_PROPOSED
    fingerprint: str = ""
    proposed_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    decided_at: Optional[datetime] = None
    decision_note: str = ""
    superseded_by: str = ""
    payload: dict = Field(default_factory=dict)


@dataclass
class LifecycleDecision:
    """Результат accept/reject/supersede."""

    ok: bool
    reason: str = ""
    record: Optional[LifecycleRecord] = None


class JsonLifecycleStore:
    """JSON-хранилище записей жизненного цикла, адресуемых по id.

    Запись лежит в ``{data_dir}/{subdir}/{record_id}.json``. Повторный
    ``propose`` с тем же отпечатком не сбрасывает уже принятое решение.
    """

    def __init__(self, subdir: str, data_dir: Optional[Path] = None):
        if data_dir is None:
            # core/CORE/narrative_engine/lifecycle_store.py -> core/OS_DATA
            data_dir = Path(__file__).resolve().parents[2] / "OS_DATA"
        self.data_dir = Path(data_dir)
        self._dir = self.data_dir / subdir
        self._dir.mkdir(parents=True, exist_ok=True)

    # ── Чтение ───────────────────────────────────────────────────

    def get(self, record_id: str) -> Optional[LifecycleRecord]:
        path = self._path_for(record_id)
        if not path.exists():
            return None
        try:
            return LifecycleRecord(**json.loads(path.read_text(encoding="utf-8")))
        except Exception as e:
            log.error("lifecycle_record_read_error id=%s error=%s", record_id, e)
            return None

    def list(self, status: Optional[str] = None) -> list[LifecycleRecord]:
        records: list[LifecycleRecord] = []
        for path in sorted(self._dir.glob("*.json")):
            try:
                record = LifecycleRecord(**json.loads(path.read_text(encoding="utf-8")))
            except Exception as e:
                log.warning("lifecycle_record_skip path=%s error=%s", path, e)
                continue
            if status is not None and record.status != status:
                continue
            records.append(record)
        records.sort(key=lambda r: (r.proposed_at, r.record_id))
        return records

    def find_by_fingerprint(self, fingerprint: str) -> Optional[LifecycleRecord]:
        if not fingerprint:
            return None
        for record in self.list():
            if record.fingerprint == fingerprint:
                return record
        return None

    def count(self) -> int:
        return len(list(self._dir.glob("*.json")))

    # ── Suggest-only: propose ────────────────────────────────────

    def propose(
        self,
        record_id: str,
        payload: dict,
        *,
        fingerprint: str = "",
    ) -> LifecycleRecord:
        """Положить предложение в хранилище. Решение не принимается.

        Идемпотентность:
          - запись с тем же ``fingerprint`` уже есть → возвращаем её;
          - если она ещё ``proposed``, обновляем payload (свежая версия);
          - принятое/отклонённое/заменённое решение не перезаписывается.
        """
        existing = self.find_by_fingerprint(fingerprint) if fingerprint else None
        if existing is None:
            existing = self.get(record_id)

        if existing is not None:
            if existing.status == STATUS_PROPOSED and existing.payload != payload:
                existing.payload = payload
                self._write(existing)
            return existing

        record = LifecycleRecord(
            record_id=record_id,
            fingerprint=fingerprint,
            payload=payload,
        )
        self._write(record)
        return record

    # ── Решения человека ─────────────────────────────────────────

    def accept(self, record_id: str, note: str = "") -> LifecycleDecision:
        """Принять предложение (явное решение человека)."""
        return self._decide(record_id, STATUS_ACCEPTED, note)

    def reject(self, record_id: str, reason: str = "") -> LifecycleDecision:
        """Отклонить предложение без применения."""
        return self._decide(record_id, STATUS_REJECTED, reason or "rejected_by_human")

    def supersede(
        self,
        record_id: str,
        superseded_by: str,
        reason: str = "",
    ) -> LifecycleDecision:
        """Пометить запись заменённой, сохранив её как историю."""
        if not superseded_by:
            return LifecycleDecision(ok=False, reason="superseded_by_required")

        record = self.get(record_id)
        if record is None:
            return LifecycleDecision(
                ok=False, reason=f"record_not_found id={record_id}"
            )
        if record.status in (STATUS_REJECTED, STATUS_SUPERSEDED):
            return LifecycleDecision(
                ok=False,
                reason=f"record_not_active status={record.status}",
                record=record,
            )

        record.status = STATUS_SUPERSEDED
        record.superseded_by = superseded_by
        record.decided_at = datetime.now(tz=timezone.utc)
        record.decision_note = reason or "superseded"
        self._write(record)
        log.info("lifecycle_record_superseded id=%s by=%s", record_id, superseded_by)
        return LifecycleDecision(ok=True, record=record)

    def _decide(self, record_id: str, status: str, note: str) -> LifecycleDecision:
        record = self.get(record_id)
        if record is None:
            return LifecycleDecision(
                ok=False, reason=f"record_not_found id={record_id}"
            )
        if record.status != STATUS_PROPOSED:
            return LifecycleDecision(
                ok=False,
                reason=f"record_not_proposed status={record.status}",
                record=record,
            )

        record.status = status
        record.decided_at = datetime.now(tz=timezone.utc)
        record.decision_note = note
        self._write(record)
        log.info("lifecycle_record_decided id=%s status=%s", record_id, status)
        return LifecycleDecision(ok=True, record=record)

    # ── Persistence ──────────────────────────────────────────────

    def _write(self, record: LifecycleRecord) -> None:
        self._path_for(record.record_id).write_text(
            json.dumps(
                record.model_dump(mode="json"),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _path_for(self, record_id: str) -> Path:
        return self._dir / f"{record_id}.json"


__all__ = [
    "ACTIVE_STATUSES",
    "STATUS_ACCEPTED",
    "STATUS_PROPOSED",
    "STATUS_REJECTED",
    "STATUS_SUPERSEDED",
    "JsonLifecycleStore",
    "LifecycleDecision",
    "LifecycleRecord",
]
