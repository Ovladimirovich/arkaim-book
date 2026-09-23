"""Scenario Modeler — моделирование альтернативных развитие.

Реализует архитектуру World Explorer: Exploration Core → Scenario Modeler (Этап 3).

Моделирует сценарии развития на основе:
- Гипотез (HypothesisGenerator)
- Причинно-следственных цепочек (CauseEffectPlanner)
- Влияния на мир (ImpactAssessor)
- Модели изменений (WorldDelta)
"""

import logging
from typing import Optional

from pydantic import BaseModel, Field

from narrative_engine.world_model import WorldModel
from narrative_engine.hypothesis_generator import Hypothesis, HypothesisType
from narrative_engine.planners.cause_effect import CauseEffectPlanner, CauseEffectTree
from narrative_engine.constraint_engine import StoryRequest
from narrative_engine.context_assembler import FullContext
from narrative_engine.impact_assessor import ImpactAssessor, ImpactReport
from narrative_engine.contradiction_detector import ContradictionDetector, ContradictionReport
from narrative_engine.world_delta import WorldDeltaCalculator, WorldDelta

log = logging.getLogger("hermes.narrative.scenario_modeler")


class ScenarioBranch(BaseModel):
    """Одна ветвь сценария — альтернативное развитие."""
    id: str
    hypothesis_id: str
    title: str
    title_ru: str
    description: str = ""
    branch_type: str  # "conservative", "moderate", "radical", "unexpected"
    cause_effect_tree: Optional[CauseEffectTree] = None
    impact_report: Optional[ImpactReport] = None
    contradiction_report: Optional[ContradictionReport] = None
    world_delta: Optional[WorldDelta] = None
    quality_score: float = Field(ge=0.0, le=1.0, default=0.5)
    tags: list[str] = Field(default_factory=list)


class ScenarioTree(BaseModel):
    """Дерево сценариев — множество альтернативных развития."""
    hypothesis: Optional[Hypothesis] = None
    branches: list[ScenarioBranch] = Field(default_factory=list)
    best_branch_id: str = ""
    branch_count: int = 0
    epoch: str = ""
    summary: str = ""


class ScenarioModeler:
    """Моделирует альтернативные развития для гипотезы.

    Для каждой гипотезы создаёт 2-5 ветвей:
    - Conservative: минимальные изменения
    - Moderate: сбалансированные изменения
    - Radical: максимальные изменения
    - Unexpected: неожиданное развитие
    """

    def __init__(self, world_model: WorldModel):
        self._wm = world_model
        self._planner = CauseEffectPlanner(world_model)
        self._impact_assessor = ImpactAssessor(world_model)
        self._contradiction_detector = ContradictionDetector(world_model)
        self._delta_calculator = WorldDeltaCalculator(world_model)

    def model_scenario(
        self,
        hypothesis: Hypothesis,
        branch_count: int = 4,
    ) -> ScenarioTree:
        """Смоделировать сценарий для гипотезы."""
        branches = []

        # Типы ветвей
        branch_types = [
            ("conservative", "Консервативное развитие"),
            ("moderate", "Умеренное развитие"),
            ("radical", "Радикальное развитие"),
            ("unexpected", "Неожиданное развитие"),
        ]

        for i, (b_type, b_label) in enumerate(branch_types[:branch_count]):
            branch = self._model_branch(hypothesis, b_type, b_label)
            if branch:
                branches.append(branch)

        # Определяем лучшую ветвь
        best_branch_id = ""
        if branches:
            best = max(branches, key=lambda b: b.quality_score)
            best_branch_id = best.id

        return ScenarioTree(
            hypothesis=hypothesis,
            branches=branches,
            best_branch_id=best_branch_id,
            branch_count=len(branches),
            epoch=hypothesis.epoch,
            summary=f"Сценарий: {len(branches)} ветвей, лучшая: {best_branch_id}",
        )

    def model_scenario_for_possibility(
        self,
        possibility_id: str,
        epoch_id: str,
    ) -> ScenarioTree:
        """Смоделировать сценарий для возможности."""
        from narrative_engine.ability_model import AbilityModel

        ability = AbilityModel(self._wm)
        possibilities = ability.get_possibilities(epoch_id, limit=20)

        # Находим возможность по ID
        target = None
        for p in possibilities:
            if p.id == possibility_id:
                target = p
                break

        if not target:
            return ScenarioTree(summary="Возможность не найдена")

        # Создаём гипотезу из возможности
        from narrative_engine.hypothesis_generator import HypothesisGenerator
        gen = HypothesisGenerator(self._wm)
        hyps = gen.generate_for_possibility(target, epoch_id)

        if not hyps:
            return ScenarioTree(summary="Гипотеза не создана")

        return self.model_scenario(hyps[0])

    def _model_branch(
        self,
        hypothesis: Hypothesis,
        branch_type: str,
        branch_label: str,
    ) -> Optional[ScenarioBranch]:
        """Смоделировать одну ветвь сценария."""
        branch_id = f"{hypothesis.id}_{branch_type}"

        # Модифицируем запрос в зависимости от типа ветви
        prompt = self._create_branch_prompt(hypothesis, branch_type)

        # Создаём StoryRequest
        request = StoryRequest(
            prompt=prompt,
            epoch=hypothesis.epoch or None,
        )

        # Строим дерево причин-следствий
        context = FullContext()
        try:
            tree = self._planner.plan(request, context)
        except Exception as e:
            log.warning("planner_error branch=%s error=%s", branch_id, e)
            tree = CauseEffectTree(root=prompt)

        # Оцениваем влияние
        impact = self._impact_assessor.assess(tree, epoch_id=hypothesis.epoch)

        # Проверяем противоречия
        contradictions = self._contradiction_detector.detect(tree)

        # Рассчитываем изменения мира
        delta = self._delta_calculator.calculate(tree, impact, epoch_id=hypothesis.epoch)

        # Рассчитываем качество
        quality_score = self._calculate_quality(
            hypothesis, tree, impact, contradictions, branch_type
        )

        # Генерируем описание
        description = self._generate_branch_description(
            hypothesis, branch_type, tree, impact, contradictions
        )

        return ScenarioBranch(
            id=branch_id,
            hypothesis_id=hypothesis.id,
            title=f"{branch_label}: {hypothesis.title}",
            title_ru=f"{branch_label}: {hypothesis.title_ru}",
            description=description,
            branch_type=branch_type,
            cause_effect_tree=tree,
            impact_report=impact,
            contradiction_report=contradictions,
            world_delta=delta,
            quality_score=quality_score,
            tags=[branch_type, hypothesis.epoch],
        )

    def _create_branch_prompt(self, hypothesis: Hypothesis, branch_type: str) -> str:
        """Создать промпт для ветви."""
        base = hypothesis.description or hypothesis.title

        if branch_type == "conservative":
            return f"Минимальные изменения: {base}"
        elif branch_type == "moderate":
            return f"Сбалансированные изменения: {base}"
        elif branch_type == "radical":
            return f"Максимальные изменения: {base}"
        elif branch_type == "unexpected":
            return f"Неожиданное развитие: {base}"
        else:
            return base

    def _calculate_quality(
        self,
        hypothesis: Hypothesis,
        tree: CauseEffectTree,
        impact: ImpactReport,
        contradictions: ContradictionReport,
        branch_type: str,
    ) -> float:
        """Рассчитать качество ветви."""
        score = 0.5  # Базовый балл

        # За непротиворечивость
        if contradictions.is_consistent:
            score += 0.2
        else:
            score -= 0.2 * contradictions.hard_count

        # За количество узлов в дереве (больше — богаче)
        node_count = len(tree.nodes)
        if node_count >= 5:
            score += 0.1
        elif node_count < 2:
            score -= 0.1

        # За влияние
        if impact.overall_impact_score > 0.3:
            score += 0.1

        # За тип ветви
        type_bonus = {
            "conservative": 0.0,
            "moderate": 0.1,
            "radical": 0.05,
            "unexpected": 0.15,
        }
        score += type_bonus.get(branch_type, 0)

        return max(0.0, min(1.0, score))

    def _generate_branch_description(
        self,
        hypothesis: Hypothesis,
        branch_type: str,
        tree: CauseEffectTree,
        impact: ImpactReport,
        contradictions: ContradictionReport,
    ) -> str:
        """Генерировать описание ветви."""
        parts = [
            f"Тип: {branch_type}",
            f"Узлов в цепочке: {len(tree.nodes)}",
            f"Влияние: {impact.overall_impact_score:.2f}",
            f"Противоречия: {contradictions.hard_count} критических",
        ]

        if impact.summary:
            parts.append(f"Сводка: {impact.summary[:100]}")

        return "; ".join(parts)
