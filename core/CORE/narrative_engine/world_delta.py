"""World Delta — модель изменений мира после события.

Реализует архитектуру World Explorer: Logic Engine → World Delta (Этап 2).
Представляет собой «снимок изменений» — что изменилось в мире
в результате цепочки причин-следствий.

Этап 5: дельта может быть применена к WorldModel ТОЛЬКО явным решением
человека и только после прохождения apply-gate (``ConsistencyEngine`` +
``ContradictionDetector``).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from narrative_engine.consistency_engine import ConsistencyEngine
from narrative_engine.contradiction_detector import ContradictionDetector
from narrative_engine.world_model import WorldModel
from narrative_engine.planners.cause_effect import CauseEffectTree
from narrative_engine.impact_assessor import ImpactReport

log = logging.getLogger("hermes.narrative.world_delta")


class CharacterDelta(BaseModel):
    """Изменение состояния персонажа."""
    character_name: str
    before: str = ""
    after: str = ""
    change_type: str = "state_change"  # state_change, location_change, relationship_change
    description: str = ""


class LocationDelta(BaseModel):
    """Изменение локации."""
    location_id: str
    location_name: str
    change_type: str = "modification"  # destruction, creation, modification, energy_shift
    description: str = ""


class CivilizationDelta(BaseModel):
    """Изменение цивилизации."""
    change_type: str = "cultural_shift"  # cultural_shift, technological_advance, decline
    description: str = ""


class TimelineDelta(BaseModel):
    """Изменение временной шкалы."""
    change_type: str = "branch"  # branch, acceleration, deceleration
    description: str = ""
    affected_epochs: list[str] = Field(default_factory=list)


class ValueDelta(BaseModel):
    """Изменение ценностей."""
    value_name: str
    change_type: str = "strengthening"  # strengthening, weakening, transformation
    description: str = ""


class WorldDeltaGateReport(BaseModel):
    """Результат apply-gate проверки дельты."""

    is_valid: bool
    consistency_valid: bool = True
    contradictions_valid: bool = True
    violations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    contradiction_count: int = 0
    contradiction_hard_count: int = 0
    tree_checked: bool = False
    summary: str = ""


class WorldDeltaApplyResult(BaseModel):
    """Результат применения дельты к WorldModel."""

    ok: bool
    applied: bool = False
    reason: str = ""
    gate: Optional[WorldDeltaGateReport] = None
    world_model_saved: bool = False
    applied_delta_id: str = ""


class WorldDeltaApplyGate:
    """Гейт применения WorldDelta (B10).

    Прогоняет дельту через ``ConsistencyEngine`` (3 реально работающих
    правила) и, если передано дерево причин-следствий, через
    ``ContradictionDetector``. Hard-противоречия блокируют применение.
    """

    def __init__(
        self,
        world_model: WorldModel,
        consistency_engine: Optional[ConsistencyEngine] = None,
        contradiction_detector: Optional[ContradictionDetector] = None,
    ):
        self._wm = world_model
        self._consistency = consistency_engine or ConsistencyEngine()
        self._detector = contradiction_detector or ContradictionDetector(world_model)

    def check(
        self,
        delta: "WorldDelta",
        *,
        epoch_id: Optional[str] = None,
        tree: Optional[CauseEffectTree] = None,
    ) -> WorldDeltaGateReport:
        """Проверить дельту без применения к миру."""
        epoch_order = {epoch.id: epoch.order for epoch in self._wm.get_epochs()}
        consistency = self._consistency.validate_world_delta(
            delta,
            epoch_id=epoch_id,
            epoch_order=epoch_order,
        )

        violations = [v.description for v in consistency.violations]
        warnings = [w.description for w in consistency.warnings]

        contradictions_valid = True
        contradiction_count = 0
        contradiction_hard_count = 0
        if tree is not None:
            contradictions = self._detector.detect(tree)
            contradictions_valid = contradictions.is_consistent
            contradiction_count = contradictions.contradiction_count
            contradiction_hard_count = contradictions.hard_count
            if not contradictions_valid:
                violations.extend(
                    c.description
                    for c in contradictions.contradictions
                    if c.severity == "hard"
                )

        is_valid = consistency.is_valid and contradictions_valid
        if is_valid:
            summary = "Гейт пройден: дельта может быть применена явным решением."
        else:
            summary = f"Гейт отклонил дельту: нарушений {len(violations)}."

        return WorldDeltaGateReport(
            is_valid=is_valid,
            consistency_valid=consistency.is_valid,
            contradictions_valid=contradictions_valid,
            violations=violations,
            warnings=warnings,
            contradiction_count=contradiction_count,
            contradiction_hard_count=contradiction_hard_count,
            tree_checked=tree is not None,
            summary=summary,
        )


class WorldDelta(BaseModel):
    """Полная модель изменений мира.

    Содержит все изменения, которые произошли в мире
    в результате цепочки причин-следствий.
    """
    event_description: str = ""
    character_deltas: list[CharacterDelta] = Field(default_factory=list)
    location_deltas: list[LocationDelta] = Field(default_factory=list)
    civilization_deltas: list[CivilizationDelta] = Field(default_factory=list)
    timeline_deltas: list[TimelineDelta] = Field(default_factory=list)
    value_deltas: list[ValueDelta] = Field(default_factory=list)
    total_changes: int = 0
    impact_magnitude: float = Field(ge=0.0, le=1.0, description="Масштаб изменений [0, 1]")
    summary: str = ""

    def apply_delta(
        self,
        world_model: WorldModel,
        *,
        accepted: bool = False,
        epoch_id: Optional[str] = None,
        tree: Optional[CauseEffectTree] = None,
        world_model_path: Optional[Path] = None,
        accepted_by: str = "",
        gate: Optional[WorldDeltaApplyGate] = None,
    ) -> WorldDeltaApplyResult:
        """Применить дельту к WorldModel только после явного accept.

        ``accepted=False`` — предложение: мир не меняется. При ``accepted=True``
        сначала прогоняется apply-gate (``ConsistencyEngine`` +
        ``ContradictionDetector``). Только прошедшая гейт дельта записывается
        в журнал ``world_model.data["applied_world_deltas"]`` с честной
        маркировкой ``SYSTEM_INTERPRETATION`` и сохраняется на диск.
        """
        if accepted is not True:
            return WorldDeltaApplyResult(
                ok=False,
                applied=False,
                reason="explicit_accept_required",
            )

        gate = gate or WorldDeltaApplyGate(world_model)
        report = gate.check(self, epoch_id=epoch_id, tree=tree)
        if not report.is_valid:
            log.warning(
                "delta_apply_blocked epoch=%s violations=%d",
                epoch_id,
                len(report.violations),
            )
            return WorldDeltaApplyResult(
                ok=False,
                applied=False,
                reason="apply_gate_rejected",
                gate=report,
            )

        applied_delta_id = f"delta_{uuid.uuid4().hex[:12]}"
        record = {
            "delta_id": applied_delta_id,
            "applied_at": datetime.now(tz=timezone.utc).isoformat(),
            "epoch_id": epoch_id or "",
            "provenance_category": "SYSTEM_INTERPRETATION",
            "accepted_by": accepted_by or "author",
            "event_description": self.event_description,
            "summary": self.summary,
            "total_changes": self.total_changes,
            "impact_magnitude": self.impact_magnitude,
            "gate": report.model_dump(mode="json"),
            "delta": self.model_dump(mode="json"),
        }

        ledger = world_model.data.setdefault("applied_world_deltas", [])
        ledger.append(record)

        try:
            path = world_model_path or (
                Path(__file__).resolve().parents[1] / "data" / "WORLD_MODEL.json"
            )
            world_model.save(path)
        except Exception as e:
            # Не оставляем «применённую» запись в памяти, если диск не записан.
            ledger.pop()
            log.error(
                "delta_apply_save_error delta_id=%s error=%s", applied_delta_id, e
            )
            return WorldDeltaApplyResult(
                ok=False,
                applied=False,
                reason=f"world_model_save_failed: {e}",
                gate=report,
            )

        log.info(
            "delta_applied delta_id=%s epoch=%s changes=%d",
            applied_delta_id,
            epoch_id,
            self.total_changes,
        )
        return WorldDeltaApplyResult(
            ok=True,
            applied=True,
            gate=report,
            world_model_saved=True,
            applied_delta_id=applied_delta_id,
        )


class WorldDeltaCalculator:
    """Рассчитывает изменения мира на основе CauseEffectTree и ImpactReport.

    Принимает CauseEffectTree + ImpactReport + WorldModel,
    возвращает WorldDelta — полную модель изменений.
    """

    def __init__(self, world_model: WorldModel):
        self._wm = world_model

    def calculate(
        self,
        tree: CauseEffectTree,
        impact_report: ImpactReport,
        epoch_id: Optional[str] = None,
    ) -> WorldDelta:
        """Рассчитать изменения мира."""
        # 1. Изменения персонажей
        character_deltas = self._calculate_character_deltas(tree, impact_report, epoch_id)

        # 2. Изменения локаций
        location_deltas = self._calculate_location_deltas(tree, impact_report, epoch_id)

        # 3. Изменения цивилизаций
        civilization_deltas = self._calculate_civilization_deltas(tree, impact_report)

        # 4. Изменения временной шкалы
        timeline_deltas = self._calculate_timeline_deltas(tree, impact_report)

        # 5. Изменения ценностей
        value_deltas = self._calculate_value_deltas(tree, impact_report)

        # Подсчёт
        total_changes = (
            len(character_deltas)
            + len(location_deltas)
            + len(civilization_deltas)
            + len(timeline_deltas)
            + len(value_deltas)
        )

        impact_magnitude = impact_report.overall_impact_score

        summary = self._generate_summary(
            character_deltas, location_deltas, civilization_deltas,
            timeline_deltas, value_deltas,
        )

        return WorldDelta(
            event_description=tree.root[:200],
            character_deltas=character_deltas,
            location_deltas=location_deltas,
            civilization_deltas=civilization_deltas,
            timeline_deltas=timeline_deltas,
            value_deltas=value_deltas,
            total_changes=total_changes,
            impact_magnitude=impact_magnitude,
            summary=summary,
        )

    def _calculate_character_deltas(
        self,
        tree: CauseEffectTree,
        impact_report: ImpactReport,
        epoch_id: Optional[str],
    ) -> list[CharacterDelta]:
        """Рассчитать изменения персонажей."""
        deltas = []

        for ci in impact_report.character_impacts:
            before = "Текущее состояние"
            after = ci.state_change or ci.description

            deltas.append(CharacterDelta(
                character_name=ci.character_name,
                before=before,
                after=after[:150],
                change_type=ci.impact_type,
                description=ci.description[:150],
            ))

        return deltas

    def _calculate_location_deltas(
        self,
        tree: CauseEffectTree,
        impact_report: ImpactReport,
        epoch_id: Optional[str],
    ) -> list[LocationDelta]:
        """Рассчитать изменения локаций."""
        deltas = []

        for li in impact_report.location_impacts:
            deltas.append(LocationDelta(
                location_id=li.location_id,
                location_name=li.location_name,
                change_type=li.impact_type,
                description=li.description[:150],
            ))

        return deltas

    def _calculate_civilization_deltas(
        self,
        tree: CauseEffectTree,
        impact_report: ImpactReport,
    ) -> list[CivilizationDelta]:
        """Рассчитать изменения цивилизаций."""
        deltas = []

        for ci in impact_report.civilization_impacts:
            deltas.append(CivilizationDelta(
                change_type=ci.impact_type,
                description=ci.description[:150],
            ))

        return deltas

    def _calculate_timeline_deltas(
        self,
        tree: CauseEffectTree,
        impact_report: ImpactReport,
    ) -> list[TimelineDelta]:
        """Рассчитать изменения временной шкалы."""
        deltas = []

        for ti in impact_report.timeline_impacts:
            deltas.append(TimelineDelta(
                change_type=ti.impact_type,
                description=ti.description[:150],
                affected_epochs=ti.affected_epochs,
            ))

        return deltas

    def _calculate_value_deltas(
        self,
        tree: CauseEffectTree,
        impact_report: ImpactReport,
    ) -> list[ValueDelta]:
        """Рассчитать изменения ценностей."""
        deltas = []

        for vi in impact_report.value_impacts:
            deltas.append(ValueDelta(
                value_name=vi.value_name,
                change_type=vi.impact_type,
                description=vi.description[:150],
            ))

        return deltas

    def _generate_summary(
        self,
        character_deltas: list[CharacterDelta],
        location_deltas: list[LocationDelta],
        civilization_deltas: list[CivilizationDelta],
        timeline_deltas: list[TimelineDelta],
        value_deltas: list[ValueDelta],
    ) -> str:
        """Генерировать сводку изменений."""
        parts = []

        if character_deltas:
            chars = [cd.character_name for cd in character_deltas[:3]]
            parts.append(f"Изменены персонажи: {', '.join(chars)}")

        if location_deltas:
            locs = [ld.location_name for ld in location_deltas[:3]]
            parts.append(f"Изменены локации: {', '.join(locs)}")

        if civilization_deltas:
            parts.append(f"Культурные изменения: {len(civilization_deltas)}")

        if timeline_deltas:
            parts.append(f"Временные ветвления: {len(timeline_deltas)}")

        if value_deltas:
            values = [vd.value_name for vd in value_deltas[:3]]
            parts.append(f"Изменены ценности: {', '.join(values)}")

        return "; ".join(parts) if parts else "Изменений нет"
