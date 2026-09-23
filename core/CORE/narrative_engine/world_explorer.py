"""World Explorer — единый pipeline исследования мира.

Реализует архитектуру World Explorer: Этап 5 — Интеграция.

Объединяет все модули в единый pipeline:
1. HypothesisGenerator → генерация гипотез
2. CompatibilityChecker → проверка совместимости
3. ScenarioModeler → моделирование сценариев
4. ImpactAssessor → оценка влияния
5. ContradictionDetector → обнаружение противоречий
6. WorldDelta → изменения мира
7. QualityEvaluator → оценка качества
8. BranchManager → управление ветвями
"""

import logging
import time
import uuid
from typing import Optional

from narrative_engine.exploration_ws import ExplorationNotifier, exploration_notifier

from pydantic import BaseModel, Field

from narrative_engine.world_model import WorldModel
from narrative_engine.constraint_engine import StoryRequest
from narrative_engine.compatibility_checker import CompatibilityChecker, CompatibilityReport
from narrative_engine.hypothesis_generator import (
    HypothesisGenerator, Hypothesis, HypothesisGraph, HypothesisType,
)
from narrative_engine.scenario_modeler import ScenarioModeler, ScenarioTree, ScenarioBranch
from narrative_engine.impact_assessor import ImpactAssessor, ImpactReport
from narrative_engine.contradiction_detector import ContradictionDetector, ContradictionReport
from narrative_engine.world_delta import WorldDeltaCalculator, WorldDelta
from narrative_engine.quality_evaluator import QualityEvaluator, QualityReport
from narrative_engine.branch_manager import BranchManager, ExplorationTree

log = logging.getLogger("hermes.narrative.world_explorer")


class ExplorationRequest(BaseModel):
    """Запрос на исследование."""
    prompt: str
    epoch: Optional[str] = None
    location: Optional[str] = None
    branch_count: int = Field(default=3, ge=1, le=10)
    max_depth: int = Field(default=2, ge=1, le=5)


class ExplorationResult(BaseModel):
    """Результат исследования."""
    request: ExplorationRequest
    hypothesis: Optional[Hypothesis] = None
    scenario: Optional[ScenarioTree] = None
    ranked_branches: list[RankedBranch] = Field(default_factory=list)
    exploration_tree: Optional[ExplorationTree] = None
    duration_ms: float = 0.0
    summary: str = ""


class RankedBranch(BaseModel):
    """Ветвь с рангом и отчётом о качестве."""
    rank: int
    branch: ScenarioBranch
    quality_report: QualityReport
    impact_report: Optional[ImpactReport] = None
    contradiction_report: Optional[ContradictionReport] = None
    world_delta: Optional[WorldDelta] = None


class WorldExplorer:
    """Единый pipeline исследования мира.

    Использование:
        explorer = WorldExplorer(world_model)
        result = explorer.explore(request)
    """

    def __init__(self, world_model: WorldModel):
        self._wm = world_model
        self._compatibility_checker = CompatibilityChecker(world_model)
        self._hypothesis_generator = HypothesisGenerator(world_model)
        self._scenario_modeler = ScenarioModeler(world_model)
        self._impact_assessor = ImpactAssessor(world_model)
        self._contradiction_detector = ContradictionDetector(world_model)
        self._delta_calculator = WorldDeltaCalculator(world_model)
        self._quality_evaluator = QualityEvaluator(world_model)
        self._branch_manager = BranchManager(world_model)

    def explore(self, request: ExplorationRequest, ws_notifier: Optional[ExplorationNotifier] = None) -> ExplorationResult:
        """Полный pipeline исследования с опциональными WebSocket нотификациями."""
        start_time = time.time()
        exploration_id = str(uuid.uuid4())[:8]
        notify = ws_notifier or exploration_notifier

        # 0. Уведомление о начале
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.ensure_future(notify.notify_started(
                    exploration_id, request.prompt, request.epoch, request.branch_count
                ))
        except RuntimeError:
            pass  # No running event loop

        # 1. Проверка совместимости
        story_request = StoryRequest(
            prompt=request.prompt,
            epoch=request.epoch,
            location=request.location,
        )
        compat_report = self._compatibility_checker.check(story_request)
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.ensure_future(notify.notify_progress(0, f"Score: {compat_report.overall_score:.2f}"))
        except RuntimeError:
            pass  # No running event loop

        if not compat_report.is_compatible:
            log.warning("idea_not_compatible score=%.2f", compat_report.overall_score)

        # 2. Генерация гипотез
        if request.epoch:
            hypotheses = self._hypothesis_generator.generate_for_epoch(
                request.epoch, limit=request.branch_count
            )
        else:
            hypotheses = self._hypothesis_generator.generate_proactive(
                limit=request.branch_count
            )

        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.ensure_future(notify.notify_progress(1, f"Гипотез: {len(hypotheses)}"))
        except RuntimeError:
            pass  # No running event loop

        if not hypotheses:
            return ExplorationResult(
                request=request,
                summary="Гипотезы не сгенерированы",
                duration_ms=(time.time() - start_time) * 1000,
            )

        best_hypothesis = hypotheses[0]

        # 3. Моделирование сценария
        scenario = self._scenario_modeler.model_scenario(
            best_hypothesis, branch_count=request.branch_count
        )
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.ensure_future(notify.notify_progress(2, f"Ветвей: {scenario.branch_count}"))
        except RuntimeError:
            pass  # No running event loop

        # 4. Оценка влияния и противоречий для каждой ветви
        ranked_branches = []
        for idx, branch in enumerate(scenario.branches):
            impact = None
            if branch.cause_effect_tree:
                impact = self._impact_assessor.assess(
                    branch.cause_effect_tree, epoch_id=request.epoch
                )

            contradictions = None
            if branch.cause_effect_tree:
                contradictions = self._contradiction_detector.detect(
                    branch.cause_effect_tree
                )

            delta = None
            if branch.cause_effect_tree and impact:
                delta = self._delta_calculator.calculate(
                    branch.cause_effect_tree, impact, epoch_id=request.epoch
                )

            branch.impact_report = impact
            branch.contradiction_report = contradictions
            branch.world_delta = delta

        # Уведомления об этапах 3-6
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.ensure_future(notify.notify_progress(3, "Влияние оценено"))
                asyncio.ensure_future(notify.notify_progress(4, "Противоречия проверены"))
                asyncio.ensure_future(notify.notify_progress(5, "Изменения рассчитаны"))
        except RuntimeError:
            pass  # No running event loop

        # 5. Оценка качества и ранжирование
        quality_reports = self._quality_evaluator.evaluate_branches(scenario.branches)
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.ensure_future(notify.notify_progress(6, "Качество оценено"))
        except RuntimeError:
            pass  # No running event loop

        for i, (branch, quality) in enumerate(zip(scenario.branches, quality_reports)):
            ranked_branches.append(RankedBranch(
                rank=quality.rank,
                branch=branch,
                quality_report=quality,
                impact_report=branch.impact_report,
                contradiction_report=branch.contradiction_report,
                world_delta=branch.world_delta,
            ))

        # 6. Управление ветвями
        exploration_tree = self._branch_manager.start_exploration(
            request.epoch or "unknown",
            None,
        )

        # 7. Формируем результат
        duration_ms = (time.time() - start_time) * 1000
        best_score = ranked_branches[0].quality_report.overall_score if ranked_branches else 0.0

        summary = self._generate_summary(
            best_hypothesis, scenario, ranked_branches, duration_ms
        )

        # Уведомление о завершении
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.ensure_future(notify.notify_progress(7, "Ранжирование завершено"))
                asyncio.ensure_future(notify.notify_complete(
                    summary, len(ranked_branches), best_score, duration_ms
                ))
        except RuntimeError:
            pass  # No running event loop

        return ExplorationResult(
            request=request,
            hypothesis=best_hypothesis,
            scenario=scenario,
            ranked_branches=ranked_branches,
            exploration_tree=exploration_tree,
            duration_ms=duration_ms,
            summary=summary,
        )

    def explore_from_hypothesis(
        self,
        hypothesis: Hypothesis,
        branch_count: int = 3,
    ) -> ExplorationResult:
        """Исследование от конкретной гипотезы."""
        start_time = time.time()

        # Моделируем сценарий
        scenario = self._scenario_modeler.model_scenario(
            hypothesis, branch_count=branch_count
        )

        # Оцениваем каждую ветвь
        ranked_branches = []
        for branch in scenario.branches:
            impact = None
            if branch.cause_effect_tree:
                impact = self._impact_assessor.assess(
                    branch.cause_effect_tree, epoch_id=hypothesis.epoch
                )

            contradictions = None
            if branch.cause_effect_tree:
                contradictions = self._contradiction_detector.detect(
                    branch.cause_effect_tree
                )

            delta = None
            if branch.cause_effect_tree and impact:
                delta = self._delta_calculator.calculate(
                    branch.cause_effect_tree, impact, epoch_id=hypothesis.epoch
                )

            branch.impact_report = impact
            branch.contradiction_report = contradictions
            branch.world_delta = delta

        # Оцениваем качество
        quality_reports = self._quality_evaluator.evaluate_branches(scenario.branches)

        for branch, quality in zip(scenario.branches, quality_reports):
            ranked_branches.append(RankedBranch(
                rank=quality.rank,
                branch=branch,
                quality_report=quality,
                impact_report=branch.impact_report,
                contradiction_report=branch.contradiction_report,
                world_delta=branch.world_delta,
            ))

        duration_ms = (time.time() - start_time) * 1000
        summary = self._generate_summary(hypothesis, scenario, ranked_branches, duration_ms)

        return ExplorationResult(
            request=ExplorationRequest(
                prompt=hypothesis.title,
                epoch=hypothesis.epoch,
                branch_count=branch_count,
            ),
            hypothesis=hypothesis,
            scenario=scenario,
            ranked_branches=ranked_branches,
            duration_ms=duration_ms,
            summary=summary,
        )

    def get_hypotheses(
        self,
        epoch_id: str,
        limit: int = 10,
    ) -> list[Hypothesis]:
        """Получить гипотезы для эпохи."""
        return self._hypothesis_generator.generate_for_epoch(epoch_id, limit=limit)

    def get_possibilities(
        self,
        epoch_id: str,
        limit: int = 10,
    ) -> list:
        """Получить возможности для эпохи."""
        from narrative_engine.ability_model import AbilityModel
        ability = AbilityModel(self._wm)
        return ability.get_possibilities(epoch_id, limit=limit)

    def _generate_summary(
        self,
        hypothesis: Hypothesis,
        scenario: ScenarioTree,
        ranked_branches: list[RankedBranch],
        duration_ms: float,
    ) -> str:
        """Генерировать сводку исследования."""
        best = ranked_branches[0] if ranked_branches else None
        best_score = best.quality_report.overall_score if best else 0.0

        parts = [
            f"Гипотеза: {hypothesis.title_ru}",
            f"Ветвей: {len(ranked_branches)}",
            f"Лучшая: {best_score:.3f}",
            f"Время: {duration_ms:.0f}ms",
        ]

        return "; ".join(parts)
