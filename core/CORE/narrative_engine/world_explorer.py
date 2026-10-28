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
from narrative_engine.compatibility_checker import (
    CompatibilityChecker,
    CompatibilityReport,
)
from narrative_engine.hypothesis_generator import (
    HypothesisGenerator,
    Hypothesis,
    HypothesisGraph,
    HypothesisStore,
    HypothesisType,
)
from narrative_engine.scenario_modeler import (
    ScenarioModeler,
    ScenarioTree,
    ScenarioBranch,
)
from narrative_engine.impact_assessor import ImpactAssessor, ImpactReport
from narrative_engine.contradiction_detector import (
    ContradictionDetector,
    ContradictionReport,
)
from narrative_engine.world_delta import WorldDeltaCalculator, WorldDelta
from narrative_engine.quality_evaluator import QualityEvaluator, QualityReport
from narrative_engine.branch_manager import (
    BranchManager,
    ExplorationTree,
    ScenarioStore,
)
from narrative_engine.lifecycle_store import LifecycleDecision

log = logging.getLogger("hermes.narrative.world_explorer")


def _load_graph_engine():
    """Граф знаний из runtime-реестра (fail open: без графа — без BFS)."""
    try:
        from core.adc_deps import get_graph_engine

        return get_graph_engine()
    except Exception as e:
        log.debug("graph_engine_unavailable error=%s", e)
        return None


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
    exploration_id: str = ""
    hypothesis: Optional[Hypothesis] = None
    scenario: Optional[ScenarioTree] = None
    ranked_branches: list[RankedBranch] = Field(default_factory=list)
    exploration_tree: Optional[ExplorationTree] = None
    new_connections: list[dict] = Field(default_factory=list)
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

    def __init__(
        self,
        world_model: WorldModel,
        graph_engine=None,
        hypothesis_store: Optional[HypothesisStore] = None,
        scenario_store: Optional[ScenarioStore] = None,
    ):
        self._wm = world_model
        self._compatibility_checker = CompatibilityChecker(world_model)
        self._hypothesis_store = hypothesis_store or HypothesisStore()
        self._scenario_store = scenario_store or ScenarioStore()
        self._hypothesis_generator = HypothesisGenerator(
            world_model,
            store=self._hypothesis_store,
        )
        self._scenario_modeler = ScenarioModeler(world_model)
        self._impact_assessor = ImpactAssessor(world_model)
        self._contradiction_detector = ContradictionDetector(world_model)
        self._delta_calculator = WorldDeltaCalculator(world_model)
        self._quality_evaluator = QualityEvaluator(world_model)
        self._branch_manager = BranchManager(world_model)
        self._graph_engine = (
            graph_engine if graph_engine is not None else _load_graph_engine()
        )

    def explore(
        self,
        request: ExplorationRequest,
        ws_notifier: Optional[ExplorationNotifier] = None,
    ) -> ExplorationResult:
        """Полный pipeline исследования с опциональными WebSocket нотификациями."""
        start_time = time.time()
        exploration_id = str(uuid.uuid4())[:8]
        notify = ws_notifier or exploration_notifier

        # 0. Уведомление о начале
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.ensure_future(
                    notify.notify_started(
                        exploration_id,
                        request.prompt,
                        request.epoch,
                        request.branch_count,
                    )
                )
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
                asyncio.ensure_future(
                    notify.notify_progress(
                        0, f"Score: {compat_report.overall_score:.2f}"
                    )
                )
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
                asyncio.ensure_future(
                    notify.notify_progress(1, f"Гипотез: {len(hypotheses)}")
                )
        except RuntimeError:
            pass  # No running event loop

        if not hypotheses:
            return ExplorationResult(
                request=request,
                exploration_id=exploration_id,
                summary="Гипотезы не сгенерированы",
                duration_ms=(time.time() - start_time) * 1000,
            )

        best_hypothesis = hypotheses[0]

        # 3. Моделирование сценария
        scenario = self._scenario_modeler.model_scenario(
            best_hypothesis, branch_count=request.branch_count
        )
        self._propose_scenario(scenario)
        new_connections = self.find_new_connections(best_hypothesis)
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.ensure_future(
                    notify.notify_progress(2, f"Ветвей: {scenario.branch_count}")
                )
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
                asyncio.ensure_future(
                    notify.notify_progress(4, "Противоречия проверены")
                )
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
            ranked_branches.append(
                RankedBranch(
                    rank=quality.rank,
                    branch=branch,
                    quality_report=quality,
                    impact_report=branch.impact_report,
                    contradiction_report=branch.contradiction_report,
                    world_delta=branch.world_delta,
                )
            )

        # 6. Управление ветвями
        exploration_tree = self._branch_manager.start_exploration(
            request.epoch or "unknown",
            None,
        )

        # 7. Формируем результат
        duration_ms = (time.time() - start_time) * 1000
        best_score = (
            ranked_branches[0].quality_report.overall_score if ranked_branches else 0.0
        )

        summary = self._generate_summary(
            best_hypothesis, scenario, ranked_branches, duration_ms
        )

        # Уведомление о завершении
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.ensure_future(
                    notify.notify_progress(7, "Ранжирование завершено")
                )
                asyncio.ensure_future(
                    notify.notify_complete(
                        summary, len(ranked_branches), best_score, duration_ms
                    )
                )
        except RuntimeError:
            pass  # No running event loop

        return ExplorationResult(
            request=request,
            exploration_id=exploration_id,
            hypothesis=best_hypothesis,
            scenario=scenario,
            ranked_branches=ranked_branches,
            exploration_tree=exploration_tree,
            new_connections=new_connections,
            duration_ms=duration_ms,
            summary=summary,
        )

    def explore_from_hypothesis(
        self,
        hypothesis: Hypothesis,
        branch_count: int = 3,
    ) -> ExplorationResult:
        """Исследование от конкретной гипотезы."""
        import uuid

        exploration_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        # Моделируем сценарий
        scenario = self._scenario_modeler.model_scenario(
            hypothesis, branch_count=branch_count
        )
        self._propose_scenario(scenario)
        new_connections = self.find_new_connections(hypothesis)

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
            ranked_branches.append(
                RankedBranch(
                    rank=quality.rank,
                    branch=branch,
                    quality_report=quality,
                    impact_report=branch.impact_report,
                    contradiction_report=branch.contradiction_report,
                    world_delta=branch.world_delta,
                )
            )

        duration_ms = (time.time() - start_time) * 1000
        summary = self._generate_summary(
            hypothesis, scenario, ranked_branches, duration_ms
        )

        return ExplorationResult(
            request=ExplorationRequest(
                prompt=hypothesis.title,
                epoch=hypothesis.epoch,
                branch_count=branch_count,
            ),
            exploration_id=exploration_id,
            hypothesis=hypothesis,
            scenario=scenario,
            ranked_branches=ranked_branches,
            new_connections=new_connections,
            duration_ms=duration_ms,
            summary=summary,
        )

    def get_hypotheses(
        self,
        epoch_id: str,
        limit: int = 10,
    ) -> list[Hypothesis]:
        """Получить гипотезы для эпохи (с персистентностью предложений).

        Свежесгенерированные гипотезы сохраняются как ``proposed``, поэтому
        принятые решения и сами гипотезы переживают перезапуск сервера.
        """
        generated = self._hypothesis_generator.generate_for_epoch(epoch_id, limit=limit)
        for hypothesis in generated:
            self._hypothesis_store.propose(hypothesis)

        stored = self._hypothesis_store.list_hypotheses(epoch_id, limit=limit)
        if stored:
            return [hypothesis for hypothesis, _record in stored]
        return generated

    def list_stored_hypotheses(
        self,
        epoch_id: Optional[str] = None,
        limit: int = 50,
    ) -> list[Hypothesis]:
        """Активные (proposed/accepted) гипотезы из хранилища."""
        return [
            hypothesis
            for hypothesis, _record in self._hypothesis_store.list_hypotheses(
                epoch_id, limit=limit
            )
        ]

    def hypothesis_record(self, hypothesis_id: str):
        """Запись жизненного цикла гипотезы (статус, время, решение)."""
        return self._hypothesis_store.get(hypothesis_id)

    def accept_hypothesis(
        self, hypothesis_id: str, note: str = ""
    ) -> LifecycleDecision:
        """Принять гипотезу — явное решение человека (без auto-apply)."""
        return self._hypothesis_store.accept(hypothesis_id, note=note)

    def reject_hypothesis(
        self, hypothesis_id: str, reason: str = ""
    ) -> LifecycleDecision:
        """Отклонить гипотезу, сохранив её как историю."""
        return self._hypothesis_store.reject(hypothesis_id, reason=reason)

    def list_stored_scenarios(
        self,
        hypothesis_id: Optional[str] = None,
        limit: int = 50,
    ) -> list[ScenarioBranch]:
        return [
            branch
            for branch, _record in self._scenario_store.list_scenarios(
                hypothesis_id, limit=limit
            )
        ]

    def supersede_scenario(
        self,
        scenario_id: str,
        superseded_by: str,
        reason: str = "",
    ) -> LifecycleDecision:
        """Пометить сценарий заменённым (исходный сохраняется как история)."""
        return self._scenario_store.supersede(
            scenario_id,
            superseded_by=superseded_by,
            reason=reason,
        )

    def _propose_scenario(self, scenario: ScenarioTree) -> None:
        """Сохранить ветви сценария как предложения (мир не меняется)."""
        for branch in scenario.branches:
            self._scenario_store.propose(branch)

    def find_new_connections(self, hypothesis: Hypothesis) -> list[dict]:
        """Опциональный BFS-проход по GraphEngine для «новых связей».

        Все результаты помечены ``SYSTEM_INTERPRETATION``: это не факты книги,
        а системная интерпретация. Без графа/совпадений — пустой список.
        """
        if self._graph_engine is None:
            return []

        candidates: list[str] = []
        for value in [*hypothesis.required_elements, *hypothesis.tags]:
            if value and value not in candidates:
                candidates.append(value)

        connections: list[dict] = []
        seen: set[tuple[str, str, str]] = set()

        for candidate in candidates:
            has_entity = getattr(self._graph_engine, "has_entity", None)
            if callable(has_entity) and not has_entity(candidate):
                continue
            try:
                neighbors = self._graph_engine.get_neighbors(candidate, max_depth=2)
            except Exception as e:
                log.warning("graph_bfs_error entity=%s error=%s", candidate, e)
                continue

            for neighbor in neighbors:
                target_id = neighbor.get("entity_id") or neighbor.get("name", "")
                if not target_id:
                    continue
                rel_type = neighbor.get("relationship_type") or "related_to"
                key = (candidate, target_id, rel_type)
                if key in seen:
                    continue
                seen.add(key)
                connections.append(
                    {
                        "source": candidate,
                        "target_id": target_id,
                        "target": neighbor.get("name") or target_id,
                        "type": rel_type,
                        "depth": neighbor.get("depth", 1),
                        "provenance_category": "SYSTEM_INTERPRETATION",
                        "source_level": "SYSTEM_INTERPRETATION",
                    }
                )

        return connections

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
