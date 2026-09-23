"""Pipeline Error Handling — PipelineResult + best-effort.

Каждый этап pipeline возвращает StageResult(ok, data, error).
Pipeline собирает все результаты и продолжает работу даже при ошибках.
LLM получает всё что удалось собрать (best-effort).
"""

import logging
import time
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

log = logging.getLogger("hermes.narrative.pipeline")


class StageStatus(str, Enum):
    OK = "ok"
    PARTIAL = "partial"  # часть данных получена
    FAILED = "failed"    # этап полностью провалился
    SKIPPED = "skipped"  # пропущен из-за зависимости


class StageResult(BaseModel):
    """Результат одного этапа pipeline."""
    stage: str
    status: StageStatus = StageStatus.OK
    data: Any = None
    error: Optional[str] = None
    duration_ms: float = 0
    warnings: list[str] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status in (StageStatus.OK, StageStatus.PARTIAL)


class PipelineResult(BaseModel):
    """Полный результат pipeline со всеми этапами."""
    stages: list[StageResult] = Field(default_factory=list)
    final_ok: bool = True
    total_duration_ms: float = 0

    def add(self, result: StageResult):
        self.stages.append(result)
        if result.status == StageStatus.FAILED:
            self.final_ok = False

    def get_stage(self, name: str) -> Optional[StageResult]:
        for s in self.stages:
            if s.stage == name:
                return s
        return None

    def summary(self) -> dict:
        """Краткая сводка для SSE."""
        return {
            "ok": self.final_ok,
            "stages": [
                {
                    "name": s.stage,
                    "status": s.status.value,
                    "error": s.error,
                    "duration_ms": s.duration_ms,
                    "warnings": s.warnings,
                }
                for s in self.stages
            ],
            "total_ms": self.total_duration_ms,
        }


def run_stage(name: str, fn, *args, **kwargs) -> StageResult:
    """
    Запустить этап pipeline с обработкой ошибок.

    Использование:
        result = run_stage("canon_validator", validator.validate, request)
    """
    start = time.time()
    try:
        data = fn(*args, **kwargs)
        duration = (time.time() - start) * 1000

        # Если результат — CanonCheckResult с violations
        if hasattr(data, 'violations') and data.violations:
            hard = [v for v in data.violations if v.severity == "hard"]
            if hard:
                return StageResult(
                    stage=name,
                    status=StageStatus.PARTIAL,
                    data=data,
                    duration_ms=duration,
                    warnings=[v.detail for v in data.violations],
                )

        return StageResult(
            stage=name,
            status=StageStatus.OK,
            data=data,
            duration_ms=duration,
        )

    except Exception as e:
        duration = (time.time() - start) * 1000
        error_msg = f"{type(e).__name__}: {e}"
        log.error("pipeline_stage_failed stage=%s error=%s", name, error_msg)
        return StageResult(
            stage=name,
            status=StageStatus.FAILED,
            error=error_msg,
            duration_ms=duration,
        )


def run_stage_with_fallback(name: str, fn, fallback, *args, **kwargs) -> StageResult:
    """
    Запустить этап с fallback при ошибке.

    Использование:
        result = run_stage_with_fallback(
            "context_assembler",
            assembler.assemble,
            lambda: FullContext(),  # пустой контекст
            canon_result,
        )
    """
    start = time.time()
    try:
        data = fn(*args, **kwargs)
        duration = (time.time() - start) * 1000
        return StageResult(
            stage=name,
            status=StageStatus.OK,
            data=data,
            duration_ms=duration,
        )
    except Exception as e:
        duration = (time.time() - start) * 1000
        error_msg = f"{type(e).__name__}: {e}"
        log.warning("pipeline_stage_fallback stage=%s error=%s fallback=used", name, error_msg)
        try:
            fallback_data = fallback()
            return StageResult(
                stage=name,
                status=StageStatus.PARTIAL,
                data=fallback_data,
                error=error_msg,
                duration_ms=duration,
                warnings=[f"Использован fallback из-за: {error_msg}"],
            )
        except Exception as e2:
            return StageResult(
                stage=name,
                status=StageStatus.FAILED,
                error=f"{error_msg} | fallback failed: {e2}",
                duration_ms=duration,
            )
