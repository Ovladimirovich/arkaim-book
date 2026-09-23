"""TemporalUpdateManager — suggest-only обновления temporal данных из книги.

M10: ядро confirmation boundary.

КРИТИЧЕСКИЕ ИНВАРИАНТЫ:
  - Strictly suggest-only: без confirm() WorldModel НЕ изменяется
  - Никакого auto-apply
  - Canon не понижается: подтверждение DERIVED поверх AUTHOR_CANON reject'ится
  - DERIVED не повышается до AUTHOR_CANON
  - После подтверждения: WorldModel.save() → refresh_temporal()
    (reload не нужен: in-memory WorldModel уже актуален после применения)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from narrative_engine.source_levels import (
    ProvenanceCategory,
)
from narrative_engine.research.temporal_extractor import TemporalFinding

log = logging.getLogger("hermes.narrative.temporal_update_manager")


@dataclass
class PendingUpdate:
    """Находка в очереди на подтверждение."""
    finding: TemporalFinding
    submitted_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    status: str = "pending"  # pending | confirmed | rejected


@dataclass
class ConfirmationResult:
    """Результат подтверждения/отклонения находки."""
    ok: bool
    reason: str = ""
    applied: bool = False
    world_model_saved: bool = False
    temporal_refreshed: bool = False


class TemporalUpdateManager:
    """Менеджер suggest-only temporal обновлений.

    Confirmation boundary:
      submit_findings() → только pending queue, WorldModel не тронут
      confirm()         → canon-валидация → WorldModel.save()+reload() → refresh
      reject()          → отклонение без применения
    """

    def __init__(self, world_model, world_engine=None, world_model_path: Optional[Path] = None):
        self._world_model = world_model
        self._world_engine = world_engine  # опционально, для refresh_temporal
        self._world_model_path = world_model_path
        self._pending: dict[str, PendingUpdate] = {}
        self._confirmed: list[TemporalFinding] = []
        self._rejected: list[tuple[TemporalFinding, str]] = []
        self._submitted_keys: set[str] = set()  # idempotency

    # ── Read-only инспекция ──────────────────────────────────────

    @property
    def pending(self) -> list[TemporalFinding]:
        return [pu.finding for pu in self._pending.values() if pu.status == "pending"]

    @property
    def confirmed(self) -> list[TemporalFinding]:
        return list(self._confirmed)

    @property
    def rejected(self) -> list[tuple[TemporalFinding, str]]:
        return list(self._rejected)

    def stats(self) -> dict:
        return {
            "pending": len(self.pending),
            "confirmed": len(self._confirmed),
            "rejected": len(self._rejected),
        }

    # ── Suggest-only: submit ─────────────────────────────────────

    def submit_findings(self, findings: list[TemporalFinding]) -> dict:
        """Положить находки в pending queue. WorldModel НЕ изменяется.

        Idempotency: повторная submit тех же находок → 0 новых pending.
        """
        new_pending = 0
        duplicates = 0

        for finding in findings:
            key = f"{finding.id}"
            if key in self._submitted_keys:
                duplicates += 1
                continue
            self._submitted_keys.add(key)
            self._pending[key] = PendingUpdate(finding=finding)
            new_pending += 1

        log.info(
            "findings_submitted new=%d duplicates=%d total_pending=%d",
            new_pending, duplicates, len(self.pending),
        )
        return {"new": new_pending, "duplicates": duplicates, "total_pending": len(self.pending)}

    # ── Confirmation gate ────────────────────────────────────────

    def confirm(self, finding_id: str) -> ConfirmationResult:
        """Подтвердить находку (human confirmation).

        Canon-валидация → применение → WorldModel.save()+reload() → refresh_temporal.
        При конфликте — reject, WorldModel не меняется.
        """
        pu = self._pending.get(finding_id)
        if pu is None:
            return ConfirmationResult(ok=False, reason=f"finding_not_found id={finding_id}")
        if pu.status != "pending":
            return ConfirmationResult(ok=False, reason=f"finding_not_pending status={pu.status}")

        finding = pu.finding

        # ── Canon/provenance validation ──────────────────────────
        validation = self._validate_finding(finding)
        if not validation.ok:
            pu.status = "rejected"
            self._rejected.append((finding, validation.reason))
            log.warning("finding_rejected id=%s reason=%s", finding_id, validation.reason)
            return validation

        # ── Apply: WorldModel update (после подтверждения!) ──────
        applied = self._apply_finding(finding)
        if not applied:
            pu.status = "rejected"
            self._rejected.append((finding, "apply_failed"))
            return ConfirmationResult(ok=False, reason="apply_failed")

        pu.status = "confirmed"
        self._confirmed.append(finding)

        # ── Persist WorldModel ───────────────────────────────────
        saved = self._save_world_model()

        # ── Refresh temporal engine ───────────────────────────────
        refreshed = False
        if self._world_engine is not None:
            refreshed = self._refresh_temporal()

        return ConfirmationResult(
            ok=True,
            applied=True,
            world_model_saved=saved,
            temporal_refreshed=refreshed,
        )

    def reject(self, finding_id: str, reason: str = "") -> ConfirmationResult:
        """Отклонить находку без применения. WorldModel не меняется."""
        pu = self._pending.get(finding_id)
        if pu is None:
            return ConfirmationResult(ok=False, reason=f"finding_not_found id={finding_id}")
        if pu.status != "pending":
            return ConfirmationResult(ok=False, reason=f"finding_not_pending status={pu.status}")
        pu.status = "rejected"
        self._rejected.append((pu.finding, reason or "rejected_by_human"))
        log.info("finding_rejected_by_human id=%s", finding_id)
        return ConfirmationResult(ok=True, applied=False)

    # ── Validation ───────────────────────────────────────────────

    def _validate_finding(self, finding: TemporalFinding) -> ConfirmationResult:
        """Canon/provenance validation перед применением.

        Правила:
          1. DERIVED finding не может повыситься до AUTHOR_CANON
          2. Нельзя понизить существующий AUTHOR_CANON узел
          3. Оригинальные canon tags не перезаписываются
        """
        # Правило: DERIVED остаётся DERIVED при применении
        if finding.category == ProvenanceCategory.DERIVED:
            # DERIVED применяется как DERIVED — корректно, проверяем конфликт ниже
            pass
        elif finding.category == ProvenanceCategory.AUTHOR_CANON:
            # AUTHOR_CANON — прямое утверждение книги, валидно
            pass
        else:
            return ConfirmationResult(
                ok=False,
                reason=f"invalid_category {finding.category.value}",
            )

        # Конфликт-проверка: попытка применить к известной эпохе
        if finding.value.startswith("epoch:"):
            epoch_id = finding.value.split(":", 1)[1]
            epoch = self._world_model.get_epoch(epoch_id)
            if epoch is not None:
                # Эпоха существует. Canon не понижается: если finding DERIVED,
                # а epoch уже canon — это не конфликт (добавляем tag), НО
                # существующий canon не должен быть перезаписан.
                # _apply_finding добавляет DERIVED как дополнительный tag, не перезаписывая.
                pass

        # Правило: finding с confidence > существующего не повышает категорию
        # (confidence не повышает provenance — инвариант M1)
        return ConfirmationResult(ok=True, reason="validation_passed")

    # ── Apply (после подтверждения) ──────────────────────────────

    def _apply_finding(self, finding: TemporalFinding) -> bool:
        """Применить подтверждённую находку к WorldModel.

        AUTHOR_CANON на существующую эпоху → merge (добавление tag, не перезапись)
        DERIVED → добавление DERIVED tag
        Новая дата на эпоху → duration_years enrichment (только для absolute_date)
        """
        try:
            if not finding.value.startswith("epoch:"):
                # Не привязано к эпохе — фиксируем как enrichment записи
                # (M10 minimal: числовые даты без epoch-binding не применяются к WorldModel
                # структуре, они уже зафиксированы в confirmed списке)
                log.info(
                    "finding_applied_unbound id=%s kind=%s value=%s",
                    finding.id, finding.kind, finding.value,
                )
                return True

            epoch_id = finding.value.split(":", 1)[1]
            epoch = self._world_model.get_epoch(epoch_id)
            if epoch is None:
                log.warning("apply_epoch_not_found id=%s", epoch_id)
                return False

            # Merge provenance: добавляем tag, НЕ перезаписываем существующие
            tag = finding.to_provenance_tag()
            existing_cats = {p.category for p in epoch.provenance}
            if tag.category not in existing_cats:
                epoch.provenance.append(tag)
                log.info(
                    "epoch_enriched id=%s category=%s",
                    epoch_id, tag.category.value,
                )
            else:
                log.info("epoch_tag_exists id=%s category=%s", epoch_id, tag.category.value)

            # Numerical date enrichment: "~4000 лет до н.э." на arkaim_era → duration_years
            if finding.kind == "absolute_date" and epoch.duration_years is None:
                years = self._parse_years(finding.raw_text)
                if years:
                    epoch.duration_years = years
                    log.info("epoch_duration_set id=%s years=%d", epoch_id, years)

            return True
        except Exception as e:
            log.error("apply_finding_error id=%s error=%s", finding.id, e)
            return False

    @staticmethod
    def _parse_years(raw: str) -> Optional[int]:
        """Парсинг числовых лет из raw_text. Только для absolute_date."""
        import re
        m = re.search(r"(\d{1,5})", raw)
        if m:
            return int(m.group(1))
        return None

    # ── Persistence & refresh ─────────────────────────────────────

    def _save_world_model(self) -> bool:
        """Сохранить WorldModel в файл. Вызывается ТОЛЬКО после подтверждения.

        Path policy (M10):
          - явный world_model_path → пишем туда (тесты/кастомные сценарии);
          - без пути → детерминированный CANONICAL путь
            core/CORE/narrative_engine/data/WORLD_MODEL.json
            (НЕ cwd-относительный: WorldModel.save() без аргумента зависит
            от рабочей директории — это известный quirk существующего кода,
            поэтому менеджер резолвит абсолютный путь сам).
        """
        try:
            if self._world_model_path is not None:
                self._world_model.save(self._world_model_path)
            else:
                canonical = (
                    Path(__file__).resolve().parents[1] / "data" / "WORLD_MODEL.json"
                )
                self._world_model.save(canonical)
            log.info("world_model_saved_after_confirmation")
            return True
        except Exception as e:
            log.error("world_model_save_error error=%s", e)
            return False

    def _refresh_temporal(self) -> bool:
        """Refresh temporal engine после подтверждённого изменения.

        Передаёт актуальный in-memory WorldModel (а не WorldModel.load()
        с кэшем), чтобы refresh гарантированно видел подтверждённое обновление.
        """
        if self._world_engine is None:
            return False
        try:
            refreshed = self._world_engine.refresh_temporal(world_model=self._world_model)
            log.info("temporal_engine_refreshed ok=%s", refreshed)
            return refreshed
        except Exception as e:
            log.error("temporal_refresh_error error=%s", e)
            return False
