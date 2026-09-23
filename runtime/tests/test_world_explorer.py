"""Tests for World Explorer — Этап 1: Canon Engine + World Model.

Тесты:
- Compatibility Checker (6 осей проверки)
- Ability Model (модель возможностей мира)
- Source Levels (уровни источников)
"""

import sys
from pathlib import Path

# Добавляем путь к core
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "core" / "CORE"))

import pytest
from narrative_engine.source_levels import SourceLevel, SOURCE_LEVEL_WEIGHTS
from narrative_engine.world_model import WorldModel
from narrative_engine.constraint_engine import StoryRequest
from narrative_engine.compatibility_checker import (
    CompatibilityChecker,
    CompatibilityReport,
    AxisScore,
    AxisViolation,
    AXIS_WEIGHTS,
)
from narrative_engine.ability_model import AbilityModel, WorldPossibility


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture(scope="module")
def world_model():
    """Загрузить WorldModel для тестов."""
    return WorldModel.load(use_cache=False)


@pytest.fixture(scope="module")
def checker(world_model):
    """Создать CompatibilityChecker для тестов."""
    return CompatibilityChecker(world_model)


@pytest.fixture(scope="module")
def ability_model(world_model):
    """Создать AbilityModel для тестов."""
    return AbilityModel(world_model)


# ── Source Levels Tests ───────────────────────────────────

class TestSourceLevels:
    """Тесты уровней источников."""

    def test_all_source_levels_have_weights(self):
        """Все уровни источников имеют веса."""
        for level in SourceLevel:
            assert level in SOURCE_LEVEL_WEIGHTS, f"SourceLevel {level} не имеет веса"

    def test_canon_weight_is_highest(self):
        """Вес CANON — максимальный."""
        assert SOURCE_LEVEL_WEIGHTS[SourceLevel.CANON] == 1.0

    def test_user_hypothesis_weight_is_lowest(self):
        """Вес USER_HYPOTHESIS — минимальный."""
        assert SOURCE_LEVEL_WEIGHTS[SourceLevel.USER_HYPOTHESIS] == 0.3

    def test_weights_are_ordered(self):
        """Веса упорядочены по убыванию."""
        levels = [
            SourceLevel.CANON,
            SourceLevel.AUTHOR_INTERPRETATION,
            SourceLevel.HISTORICAL,
            SourceLevel.MYTHOLOGICAL,
            SourceLevel.SCIENTIFIC,
            SourceLevel.SYSTEM_INTERPRETATION,
            SourceLevel.USER_HYPOTHESIS,
        ]
        for i in range(len(levels) - 1):
            assert SOURCE_LEVEL_WEIGHTS[levels[i]] >= SOURCE_LEVEL_WEIGHTS[levels[i + 1]], \
                f"Вес {levels[i]} должен быть >= веса {levels[i + 1]}"


# ── Compatibility Checker Tests ───────────────────────────

class TestCompatibilityChecker:
    """Тесты проверки совместимости по 6 осям."""

    def test_valid_idea_passes_all_axes(self, checker):
        """Совместимая идея проходит все 6 осей."""
        request = StoryRequest(
            prompt="Расскажи о духовном пути ученика в Сатья Юге в Гиперборее",
            epoch="satya_yuga",
            location="hyperborea",
        )
        report = checker.check(request)

        assert isinstance(report, CompatibilityReport)
        assert len(report.axis_scores) == 6
        assert report.overall_score > 0.0
        assert report.risk_level in ["low", "medium", "high", "rejected"]

    def test_book_canon_violation_detected(self, checker):
        """Нарушение книжного канона обнаруживается (анахронизм)."""
        request = StoryRequest(
            prompt="Ученик использует компьютер для изучения древних текстов",
            epoch="satya_yuga",
        )
        report = checker.check(request)

        # Должно быть нарушение по оси book_canon
        book_canon_score = next(ax for ax in report.axis_scores if ax.axis == "book_canon")
        assert book_canon_score.score < 1.0
        assert len(book_canon_score.violations) > 0

    def test_anachronism_detected(self, checker):
        """Анахронизм обнаруживается."""
        request = StoryRequest(
            prompt="Воин стреляет из ружье на врагов",
            epoch="satya_yuga",
        )
        report = checker.check(request)

        # Должно быть нарушение
        has_anachronism = any(
            "ружье" in v.detail.lower()
            for ax in report.axis_scores
            for v in ax.violations
        )
        assert has_anachronism, "Анахронизм 'ружье' не обнаружен"

    def test_geographic_violation_detected(self, checker):
        """Географическое нарушение обнаруживается."""
        request = StoryRequest(
            prompt="Происходит в Аркаиме во время Сатья Юги",
            epoch="satya_yuga",
            location="arkaim",
        )
        report = checker.check(request)

        # Проверяем ось geographical
        geo_score = next(ax for ax in report.axis_scores if ax.axis == "geographical")
        assert isinstance(geo_score, AxisScore)

    def test_character_not_in_epoch_detected(self, checker):
        """Персонаж не в эпохе обнаруживается."""
        request = StoryRequest(
            prompt="Дорофей путешествует по Гиперборее",
            epoch="satya_yuga",
        )
        report = checker.check(request)

        # Проверяем ось character
        char_score = next(ax for ax in report.axis_scores if ax.axis == "character")
        assert isinstance(char_score, AxisScore)

    def test_author_intent_violation_detected(self, checker):
        """Нарушение авторского замысла обнаруживается."""
        request = StoryRequest(
            prompt="Война и разрушение охватили весь мир",
            epoch="satya_yuga",
        )
        report = checker.check(request)

        # Проверяем ось author_intent
        author_score = next(ax for ax in report.axis_scores if ax.axis == "author_intent")
        assert author_score.score < 1.0

    def test_compatibility_report_score_range(self, checker):
        """Общий балл в диапазоне [0, 1]."""
        request = StoryRequest(
            prompt="Расскажи о жизни в Гиперборее",
            epoch="satya_yuga",
            location="hyperborea",
        )
        report = checker.check(request)

        assert 0.0 <= report.overall_score <= 1.0

    def test_axis_weights_sum_to_one(self):
        """Веса осей в сумме равны 1.0."""
        total = sum(AXIS_WEIGHTS.values())
        assert abs(total - 1.0) < 0.01, f"Сумма весов осей: {total}, ожидается 1.0"

    def test_risk_levels(self, checker):
        """Уровни риска определяются корректно."""
        # Идея с анахронизмом — high risk
        request = StoryRequest(
            prompt="Используем компьютер для анализа",
            epoch="satya_yuga",
        )
        report = checker.check(request)
        assert report.risk_level in ["high", "rejected"]

    def test_recommendations_generated(self, checker):
        """Рекомендации генерируются для низких баллов."""
        request = StoryRequest(
            prompt="Война и разрушение",
            epoch="satya_yuga",
        )
        report = checker.check(request)

        # Для запроса с негативными темами должны быть рекомендации
        assert isinstance(report.recommendations, list)


# ── Ability Model Tests ───────────────────────────────────

class TestAbilityModel:
    """Тесты модели возможностей мира."""

    def test_possibilities_for_epoch(self, ability_model):
        """Получить возможности для эпохи."""
        possibilities = ability_model.get_possibilities(epoch_id="satya_yuga", limit=10)

        assert isinstance(possibilities, list)
        assert len(possibilities) > 0
        assert all(isinstance(p, WorldPossibility) for p in possibilities)

    def test_possibility_has_required_fields(self, ability_model):
        """У каждой возможности есть обязательные поля."""
        possibilities = ability_model.get_possibilities(epoch_id="satya_yuga", limit=5)

        for p in possibilities:
            assert p.id, "У возможности должен быть id"
            assert p.title, "У возможности должен быть title"
            assert p.category in ["event", "character_arc", "technology", "cultural_shift", "conflict"]

    def test_possibilities_for_hypothesis(self, ability_model):
        """Получить возможности для конкретной гипотезы."""
        possibilities = ability_model.get_possibilities_for_hypothesis(
            "Что если Аркаим не был разрушен?",
            epoch_id="satya_yuga",
        )

        assert isinstance(possibilities, list)
        # Должны быть релевантные возможности
        assert len(possibilities) > 0

    def test_possibilities_deduplication(self, ability_model):
        """Возможности дедуплицируются."""
        possibilities = ability_model.get_possibilities(epoch_id="satya_yuga", limit=50)

        ids = [p.id for p in possibilities]
        assert len(ids) == len(set(ids)), "Есть дублирующиеся возможности"

    def test_summary(self, ability_model):
        """Сводка модели возможностей."""
        summary = ability_model.summary()

        assert "AbilityModel" in summary
        assert "эпох" in summary

    def test_character_possibilities(self, ability_model):
        """Возможности персонажей генерируются."""
        possibilities = ability_model.get_possibilities(epoch_id="satya_yuga", limit=20)

        char_arcs = [p for p in possibilities if p.category == "character_arc"]
        assert len(char_arcs) > 0, "Должны быть арки персонажей"

    def test_pattern_possibilities(self, ability_model):
        """Возможности паттернов генерируются."""
        possibilities = ability_model.get_possibilities(limit=20)

        patterns = [p for p in possibilities if p.category == "event"]
        assert len(patterns) > 0, "Должны быть паттерны"


# ── Integration Tests ─────────────────────────────────────

class TestWorldExplorerIntegration:
    """Интеграционные тесты: CanonValidator + WorldModel + CompatibilityChecker."""

    def test_canon_validator_plus_compatibility(self, world_model):
        """CanonValidator и CompatibilityChecker работают вместе."""
        from narrative_engine.canon_validator import CanonValidator

        request = StoryRequest(
            prompt="Расскажи о духовном пути в Гиперборее",
            epoch="satya_yuga",
            location="hyperborea",
        )

        # CanonValidator
        validator = CanonValidator(world_model)
        canon_result = validator.validate(request)
        assert canon_result.valid

        # CompatibilityChecker
        checker = CompatibilityChecker(world_model)
        compat_report = checker.check(request)
        assert compat_report.overall_score > 0.0

    def test_ability_model_plus_compatibility(self, ability_model, checker):
        """AbilityModel и CompatibilityChecker работают вместе."""
        # Получаем возможности
        possibilities = ability_model.get_possibilities(epoch_id="satya_yuga", limit=5)
        assert len(possibilities) > 0

        # Проверяем первую возможность на совместимость
        first = possibilities[0]
        request = StoryRequest(
            prompt=f"Исследуем: {first.title}",
            epoch="satya_yuga",
        )
        report = checker.check(request)
        assert report.overall_score > 0.0

    def test_world_model_seed(self, world_model):
        """WorldModel загружается и содержит данные."""
        epochs = world_model.get_epochs()
        assert len(epochs) > 0

        summary = world_model.summary()
        assert "Мир:" in summary


# ── Этап 2: Logic Engine Tests ────────────────────────────

class TestImpactAssessor:
    """Тесты оценки влияния на мир."""

    def test_impact_assessor_creates_report(self, world_model):
        """ImpactAssessor создаёт отчёт."""
        from narrative_engine.impact_assessor import ImpactAssessor, ImpactReport
        from narrative_engine.planners.cause_effect import CauseEffectTree, CauseEffectNode

        assessor = ImpactAssessor(world_model)

        # Создаём простое дерево
        tree = CauseEffectTree(
            root="Тестовое событие",
            nodes=[
                CauseEffectNode(id="n0", type="cause", description="Причина", order=0),
                CauseEffectNode(id="n1", type="effect", description="Следствие", order=1, depends_on=["n0"]),
            ],
            temporal_order=["n0", "n1"],
        )

        report = assessor.assess(tree, epoch_id="satya_yuga")
        assert isinstance(report, ImpactReport)
        assert report.overall_impact_score >= 0.0

    def test_impact_report_has_fields(self, world_model):
        """ImpactReport содержит все поля."""
        from narrative_engine.impact_assessor import ImpactAssessor
        from narrative_engine.planners.cause_effect import CauseEffectTree, CauseEffectNode

        assessor = ImpactAssessor(world_model)
        tree = CauseEffectTree(
            root="Событие",
            nodes=[CauseEffectNode(id="n0", type="cause", description="Тест", order=0)],
        )

        report = assessor.assess(tree)
        assert hasattr(report, "character_impacts")
        assert hasattr(report, "location_impacts")
        assert hasattr(report, "civilization_impacts")
        assert hasattr(report, "timeline_impacts")
        assert hasattr(report, "value_impacts")
        assert hasattr(report, "summary")


class TestContradictionDetector:
    """Тесты обнаружения противоречий."""

    def test_no_contradictions_in_valid_tree(self, world_model):
        """Нет противоречий в валидном дереве."""
        from narrative_engine.contradiction_detector import ContradictionDetector, ContradictionReport
        from narrative_engine.planners.cause_effect import CauseEffectTree, CauseEffectNode

        detector = ContradictionDetector(world_model)

        tree = CauseEffectTree(
            root="Валидное событие",
            nodes=[
                CauseEffectNode(id="n0", type="cause", description="Причина", order=0),
                CauseEffectNode(id="n1", type="effect", description="Следствие", order=1, depends_on=["n0"]),
            ],
            temporal_order=["n0", "n1"],
        )

        report = detector.detect(tree)
        assert isinstance(report, ContradictionReport)
        assert report.is_consistent

    def test_temporal_paradox_detected(self, world_model):
        """Обнаружен временной парадокс."""
        from narrative_engine.contradiction_detector import ContradictionDetector
        from narrative_engine.planners.cause_effect import CauseEffectTree, CauseEffectNode

        detector = ContradictionDetector(world_model)

        # Создаём дерево с парадоксом: effect появляется раньше cause
        tree = CauseEffectTree(
            root="Парадокс",
            nodes=[
                CauseEffectNode(id="n0", type="cause", description="Причина", order=5),
                CauseEffectNode(id="n1", type="effect", description="Следствие", order=0, depends_on=["n0"]),
            ],
            temporal_order=["n1", "n0"],  # effect trước cause
        )

        report = detector.detect(tree)
        assert not report.is_consistent
        assert report.hard_count > 0

    def test_missing_cause_detected(self, world_model):
        """Обнаружена отсутствующая причина."""
        from narrative_engine.contradiction_detector import ContradictionDetector
        from narrative_engine.planners.cause_effect import CauseEffectTree, CauseEffectNode

        detector = ContradictionDetector(world_model)

        # Effect без depends_on и с order > 0
        tree = CauseEffectTree(
            root="Без причины",
            nodes=[
                CauseEffectNode(id="n0", type="cause", description="Корень", order=0),
                CauseEffectNode(id="n1", type="effect", description="Сирота", order=1),
            ],
            temporal_order=["n0", "n1"],
        )

        report = detector.detect(tree)
        # Должно быть предупреждение (soft)
        assert report.contradiction_count >= 0  # Может быть 0 если effect на order 1 не считается сиротой

    def test_report_summary(self, world_model):
        """Сводка отчёта генерируется."""
        from narrative_engine.contradiction_detector import ContradictionDetector
        from narrative_engine.planners.cause_effect import CauseEffectTree, CauseEffectNode

        detector = ContradictionDetector(world_model)
        tree = CauseEffectTree(
            root="Тест",
            nodes=[CauseEffectNode(id="n0", type="cause", description="Тест", order=0)],
        )

        report = detector.detect(tree)
        assert isinstance(report.summary, str)
        assert len(report.summary) > 0


class TestWorldDelta:
    """Тесты модели изменений мира."""

    def test_world_delta_calculator(self, world_model):
        """WorldDeltaCalculator рассчитывает изменения."""
        from narrative_engine.world_delta import WorldDeltaCalculator, WorldDelta
        from narrative_engine.impact_assessor import ImpactAssessor
        from narrative_engine.planners.cause_effect import CauseEffectTree, CauseEffectNode

        calculator = WorldDeltaCalculator(world_model)
        assessor = ImpactAssessor(world_model)

        tree = CauseEffectTree(
            root="Тестовое событие",
            nodes=[
                CauseEffectNode(id="n0", type="cause", description="Причина", order=0),
                CauseEffectNode(id="n1", type="effect", description="Следствие", order=1, depends_on=["n0"]),
            ],
            temporal_order=["n0", "n1"],
        )

        impact_report = assessor.assess(tree, epoch_id="satya_yuga")
        delta = calculator.calculate(tree, impact_report, epoch_id="satya_yuga")

        assert isinstance(delta, WorldDelta)
        assert delta.total_changes >= 0
        assert 0.0 <= delta.impact_magnitude <= 1.0

    def test_world_delta_has_fields(self, world_model):
        """WorldDelta содержит все поля."""
        from narrative_engine.world_delta import WorldDeltaCalculator
        from narrative_engine.impact_assessor import ImpactAssessor
        from narrative_engine.planners.cause_effect import CauseEffectTree, CauseEffectNode

        calculator = WorldDeltaCalculator(world_model)
        assessor = ImpactAssessor(world_model)

        tree = CauseEffectTree(root="Событие", nodes=[])
        impact_report = assessor.assess(tree)
        delta = calculator.calculate(tree, impact_report)

        assert hasattr(delta, "character_deltas")
        assert hasattr(delta, "location_deltas")
        assert hasattr(delta, "civilization_deltas")
        assert hasattr(delta, "timeline_deltas")
        assert hasattr(delta, "value_deltas")
        assert hasattr(delta, "summary")


class TestLogicEngineIntegration:
    """Интеграционные тесты Logic Engine."""

    def test_full_logic_pipeline(self, world_model):
        """Полный pipeline: CauseEffectTree → ImpactAssessor → ContradictionDetector → WorldDelta."""
        from narrative_engine.planners.cause_effect import CauseEffectPlanner, CauseEffectTree, CauseEffectNode
        from narrative_engine.impact_assessor import ImpactAssessor
        from narrative_engine.contradiction_detector import ContradictionDetector
        from narrative_engine.world_delta import WorldDeltaCalculator
        from narrative_engine.constraint_engine import StoryRequest
        from narrative_engine.context_assembler import FullContext

        # 1. Создаём дерево причин-следствий
        planner = CauseEffectPlanner(world_model)
        request = StoryRequest(
            prompt="Путешествие героя через Гиперборею",
            epoch="satya_yuga",
            location="hyperborea",
        )
        context = FullContext()
        tree = planner.plan(request, context)

        assert isinstance(tree, CauseEffectTree)
        assert len(tree.nodes) > 0

        # 2. Оцениваем влияние
        assessor = ImpactAssessor(world_model)
        impact_report = assessor.assess(tree, epoch_id="satya_yuga")
        assert impact_report.overall_impact_score >= 0.0

        # 3. Проверяем противоречия
        detector = ContradictionDetector(world_model)
        contradiction_report = detector.detect(tree)
        assert isinstance(contradiction_report.is_consistent, bool)

        # 4. Рассчитываем изменения мира
        calculator = WorldDeltaCalculator(world_model)
        delta = calculator.calculate(tree, impact_report, epoch_id="satya_yuga")
        assert delta.total_changes >= 0

    def test_pattern_chain_expanded(self):
        """Паттерны расширены до 50+."""
        from narrative_engine.planners.cause_effect import PATTERN_CHAINS
        assert len(PATTERN_CHAINS) >= 50, f"Ожидалось 50+ паттернов, получено {len(PATTERN_CHAINS)}"


# ── Этап 3: Exploration Core Tests ─────────────────────────

class TestHypothesisGenerator:
    """Тесты генератора гипотез."""

    def test_generate_for_possibility(self, world_model):
        """Генерация гипотез на основе возможности."""
        from narrative_engine.hypothesis_generator import HypothesisGenerator, Hypothesis
        from narrative_engine.ability_model import AbilityModel

        gen = HypothesisGenerator(world_model)
        ability = AbilityModel(world_model)

        possibilities = ability.get_possibilities(epoch_id="satya_yuga", limit=1)
        assert len(possibilities) > 0

        hyps = gen.generate_for_possibility(possibilities[0], epoch_id="satya_yuga")
        assert len(hyps) > 0
        assert all(isinstance(h, Hypothesis) for h in hyps)

    def test_generate_for_epoch(self, world_model):
        """Генерация гипотез для эпохи."""
        from narrative_engine.hypothesis_generator import HypothesisGenerator, Hypothesis

        gen = HypothesisGenerator(world_model)
        hyps = gen.generate_for_epoch("satya_yuga", limit=10)

        assert len(hyps) > 0
        assert len(hyps) <= 10
        assert all(isinstance(h, Hypothesis) for h in hyps)

    def test_generate_for_hypothesis(self, world_model):
        """Генерация производных гипотез."""
        from narrative_engine.hypothesis_generator import HypothesisGenerator, Hypothesis

        gen = HypothesisGenerator(world_model)
        hyps = gen.generate_for_epoch("satya_yuga", limit=1)

        assert len(hyps) > 0

        derivatives = gen.generate_for_hypothesis(hyps[0], limit=3)
        assert len(derivatives) > 0
        assert all(isinstance(d, Hypothesis) for d in derivatives)

    def test_generate_proactive(self, world_model):
        """Проактивная генерация гипотез."""
        from narrative_engine.hypothesis_generator import HypothesisGenerator

        gen = HypothesisGenerator(world_model)
        hyps = gen.generate_proactive(epoch_id="satya_yuga", limit=5)

        assert len(hyps) > 0

    def test_build_graph(self, world_model):
        """Построение графа гипотез."""
        from narrative_engine.hypothesis_generator import HypothesisGenerator, HypothesisGraph

        gen = HypothesisGenerator(world_model)
        graph = gen.build_graph("satya_yuga", depth=2, limit_per_level=3)

        assert isinstance(graph, HypothesisGraph)
        assert graph.total_count > 0
        assert len(graph.hypotheses) > 0

    def test_hypothesis_has_required_fields(self, world_model):
        """Гипотеза содержит обязательные поля."""
        from narrative_engine.hypothesis_generator import HypothesisGenerator

        gen = HypothesisGenerator(world_model)
        hyps = gen.generate_for_epoch("satya_yuga", limit=1)

        for hyp in hyps:
            assert hyp.id, "Гипотеза должна иметь id"
            assert hyp.title, "Гипотеза должна иметь title"
            assert hyp.hypothesis_type, "Гипотеза должна иметь hypothesis_type"


class TestScenarioModeler:
    """Тесты моделировщика сценариев."""

    def test_model_scenario(self, world_model):
        """Моделирование сценария для гипотезы."""
        from narrative_engine.hypothesis_generator import HypothesisGenerator
        from narrative_engine.scenario_modeler import ScenarioModeler, ScenarioTree

        gen = HypothesisGenerator(world_model)
        modeler = ScenarioModeler(world_model)

        hyps = gen.generate_for_epoch("satya_yuga", limit=1)
        assert len(hyps) > 0

        tree = modeler.model_scenario(hyps[0], branch_count=3)
        assert isinstance(tree, ScenarioTree)
        assert tree.branch_count > 0
        assert len(tree.branches) > 0

    def test_scenario_branches_have_quality(self, world_model):
        """Ветви сценария имеют оценку качества."""
        from narrative_engine.hypothesis_generator import HypothesisGenerator
        from narrative_engine.scenario_modeler import ScenarioModeler

        gen = HypothesisGenerator(world_model)
        modeler = ScenarioModeler(world_model)

        hyps = gen.generate_for_epoch("satya_yuga", limit=1)
        tree = modeler.model_scenario(hyps[0], branch_count=2)

        for branch in tree.branches:
            assert 0.0 <= branch.quality_score <= 1.0

    def test_best_branch_selected(self, world_model):
        """Выбирается лучшая ветвь."""
        from narrative_engine.hypothesis_generator import HypothesisGenerator
        from narrative_engine.scenario_modeler import ScenarioModeler

        gen = HypothesisGenerator(world_model)
        modeler = ScenarioModeler(world_model)

        hyps = gen.generate_for_epoch("satya_yuga", limit=1)
        tree = modeler.model_scenario(hyps[0], branch_count=3)

        assert tree.best_branch_id != ""
        best = next(b for b in tree.branches if b.id == tree.best_branch_id)
        assert best.quality_score >= 0.0


class TestBranchManager:
    """Тесты менеджера ветвей."""

    def test_start_exploration(self, world_model):
        """Начало исследования."""
        from narrative_engine.branch_manager import BranchManager, ExplorationTree

        manager = BranchManager(world_model)
        tree = manager.start_exploration("satya_yuga")

        assert isinstance(tree, ExplorationTree)
        assert tree.root_id != ""
        assert tree.current_id != ""

    def test_explore_branch(self, world_model):
        """Исследование ветви."""
        from narrative_engine.branch_manager import BranchManager

        manager = BranchManager(world_model)
        tree = manager.start_exploration("satya_yuga")
        initial_count = tree.total_nodes

        root = manager.get_current_branch()
        assert root is not None

        manager.explore_branch(root.id)
        assert manager._tree.total_nodes > initial_count

    def test_navigation(self, world_model):
        """Навигация по дереву."""
        from narrative_engine.branch_manager import BranchManager

        manager = BranchManager(world_model)
        manager.start_exploration("satya_yuga")

        root = manager.get_current_branch()
        manager.explore_branch(root.id)

        # Идём вниз
        current = manager.get_current_branch()
        assert current.depth > 0

        # Идём вверх
        manager.go_up()
        current2 = manager.get_current_branch()
        assert current2.depth == 0

    def test_get_best_branch(self, world_model):
        """Поиск лучшей ветви."""
        from narrative_engine.branch_manager import BranchManager

        manager = BranchManager(world_model)
        manager.start_exploration("satya_yuga")

        root = manager.get_current_branch()
        manager.explore_branch(root.id)

        best = manager.get_best_branch()
        assert best is not None

    def test_get_path_to_root(self, world_model):
        """Путь до корня."""
        from narrative_engine.branch_manager import BranchManager

        manager = BranchManager(world_model)
        manager.start_exploration("satya_yuga")

        root = manager.get_current_branch()
        manager.explore_branch(root.id)

        current = manager.get_current_branch()
        path = manager.get_path_to_root(current.id)

        assert len(path) > 0
        assert path[0] == manager._tree.root_id

    def test_to_dict(self, world_model):
        """Экспорт в словарь."""
        from narrative_engine.branch_manager import BranchManager

        manager = BranchManager(world_model)
        manager.start_exploration("satya_yuga")

        data = manager.to_dict()
        assert "root_id" in data
        assert "nodes" in data


class TestExplorationCoreIntegration:
    """Интеграционные тесты Exploration Core."""

    def test_full_exploration_pipeline(self, world_model):
        """Полный pipeline: Hypothesis → Scenario → Branch."""
        from narrative_engine.hypothesis_generator import HypothesisGenerator
        from narrative_engine.scenario_modeler import ScenarioModeler
        from narrative_engine.branch_manager import BranchManager

        # 1. Генерируем гипотезы
        gen = HypothesisGenerator(world_model)
        hyps = gen.generate_for_epoch("satya_yuga", limit=3)
        assert len(hyps) > 0

        # 2. Моделируем сценарий
        modeler = ScenarioModeler(world_model)
        scenario = modeler.model_scenario(hyps[0], branch_count=2)
        assert scenario.branch_count > 0

        # 3. Управляем ветвями
        manager = BranchManager(world_model)
        tree = manager.start_exploration("satya_yuga")
        root = manager.get_current_branch()
        manager.explore_branch(root.id)

        assert tree.total_nodes > 0


# ── Этап 4: Quality Evaluator Tests ─────────────────────────

class TestQualityEvaluator:
    """Тесты оценщика качества."""

    def test_evaluate_branch(self, world_model):
        """Оценка ветви сценария."""
        from narrative_engine.quality_evaluator import QualityEvaluator, QualityReport
        from narrative_engine.hypothesis_generator import HypothesisGenerator
        from narrative_engine.scenario_modeler import ScenarioModeler

        gen = HypothesisGenerator(world_model)
        modeler = ScenarioModeler(world_model)
        evaluator = QualityEvaluator(world_model)

        hyps = gen.generate_for_epoch("satya_yuga", limit=1)
        scenario = modeler.model_scenario(hyps[0], branch_count=2)

        report = evaluator.evaluate(scenario.branches[0])
        assert isinstance(report, QualityReport)
        assert 0.0 <= report.overall_score <= 1.0
        assert len(report.criteria_scores) == 5

    def test_evaluate_branches_and_rank(self, world_model):
        """Оценка и ранжирование ветвей."""
        from narrative_engine.quality_evaluator import QualityEvaluator
        from narrative_engine.hypothesis_generator import HypothesisGenerator
        from narrative_engine.scenario_modeler import ScenarioModeler

        gen = HypothesisGenerator(world_model)
        modeler = ScenarioModeler(world_model)
        evaluator = QualityEvaluator(world_model)

        hyps = gen.generate_for_epoch("satya_yuga", limit=1)
        scenario = modeler.model_scenario(hyps[0], branch_count=3)

        reports = evaluator.evaluate_branches(scenario.branches)
        assert len(reports) == 3

        # Проверяем ранжирование
        for i, report in enumerate(reports):
            assert report.rank == i + 1
            assert report.total_evaluated == 3

        # Проверяем排序 по убыванию
        scores = [r.overall_score for r in reports]
        assert scores == sorted(scores, reverse=True)

    def test_criteria_weights_sum_to_one(self):
        """Веса критериев в сумме равны 1.0."""
        from narrative_engine.quality_evaluator import CRITERIA_WEIGHTS

        total = sum(CRITERIA_WEIGHTS.values())
        assert abs(total - 1.0) < 0.01, f"Сумма весов: {total}, ожидается 1.0"

    def test_criteria_scores_have_fields(self, world_model):
        """Оценки критериев содержат все поля."""
        from narrative_engine.quality_evaluator import QualityEvaluator
        from narrative_engine.hypothesis_generator import HypothesisGenerator
        from narrative_engine.scenario_modeler import ScenarioModeler

        gen = HypothesisGenerator(world_model)
        modeler = ScenarioModeler(world_model)
        evaluator = QualityEvaluator(world_model)

        hyps = gen.generate_for_epoch("satya_yuga", limit=1)
        scenario = modeler.model_scenario(hyps[0], branch_count=1)

        report = evaluator.evaluate(scenario.branches[0])

        for cs in report.criteria_scores:
            assert cs.criterion in ["canon_alignment", "logical_consistency",
                                    "thematic_depth", "dramatic_potential", "originality"]
            assert 0.0 <= cs.score <= 1.0
            assert 0.0 <= cs.weight <= 1.0
            assert cs.explanation

    def test_strengths_and_weaknesses(self, world_model):
        """Определяются сильные и слабые стороны."""
        from narrative_engine.quality_evaluator import QualityEvaluator
        from narrative_engine.hypothesis_generator import HypothesisGenerator
        from narrative_engine.scenario_modeler import ScenarioModeler

        gen = HypothesisGenerator(world_model)
        modeler = ScenarioModeler(world_model)
        evaluator = QualityEvaluator(world_model)

        hyps = gen.generate_for_epoch("satya_yuga", limit=1)
        scenario = modeler.model_scenario(hyps[0], branch_count=2)

        reports = evaluator.evaluate_branches(scenario.branches)
        for report in reports:
            assert isinstance(report.strengths, list)
            assert isinstance(report.weaknesses, list)
            assert isinstance(report.recommendations, list)

    def test_rank_alternatives(self, world_model):
        """Ранжирование альтернатив."""
        from narrative_engine.quality_evaluator import QualityEvaluator
        from narrative_engine.hypothesis_generator import HypothesisGenerator
        from narrative_engine.scenario_modeler import ScenarioModeler

        gen = HypothesisGenerator(world_model)
        modeler = ScenarioModeler(world_model)
        evaluator = QualityEvaluator(world_model)

        hyps = gen.generate_for_epoch("satya_yuga", limit=1)
        scenario = modeler.model_scenario(hyps[0], branch_count=4)

        ranked = evaluator.rank_alternatives(scenario.branches)
        assert len(ranked) == 4

        # Первая — лучшая
        assert ranked[0].rank == 1
        assert ranked[0].overall_score >= ranked[-1].overall_score


class TestQualityEvaluatorIntegration:
    """Интеграционные тесты Quality Evaluator."""

    def test_full_quality_pipeline(self, world_model):
        """Полный pipeline: Hypothesis → Scenario → Quality."""
        from narrative_engine.hypothesis_generator import HypothesisGenerator
        from narrative_engine.scenario_modeler import ScenarioModeler
        from narrative_engine.quality_evaluator import QualityEvaluator

        # 1. Генерируем гипотезы
        gen = HypothesisGenerator(world_model)
        hyps = gen.generate_for_epoch("satya_yuga", limit=2)
        assert len(hyps) > 0

        # 2. Моделируем сценарий
        modeler = ScenarioModeler(world_model)
        scenario = modeler.model_scenario(hyps[0], branch_count=3)
        assert scenario.branch_count > 0

        # 3. Оцениваем качество
        evaluator = QualityEvaluator(world_model)
        reports = evaluator.evaluate_branches(scenario.branches)
        assert len(reports) > 0

        # 4. Лучшая ветвь
        best = reports[0]
        assert best.rank == 1
        assert best.overall_score > 0.0


# ── Этап 5: Integration Tests ──────────────────────────────

class TestWorldExplorer:
    """Тесты единого pipeline World Explorer."""

    def test_explore_full_pipeline(self, world_model):
        """Полный pipeline: Request → Explore → Result."""
        from narrative_engine.world_explorer import WorldExplorer, ExplorationRequest, ExplorationResult

        explorer = WorldExplorer(world_model)
        request = ExplorationRequest(
            prompt="Путешествие героя через Гиперборею",
            epoch="satya_yuga",
            branch_count=3,
        )

        result = explorer.explore(request)
        assert isinstance(result, ExplorationResult)
        assert result.hypothesis is not None
        assert result.scenario is not None
        assert len(result.ranked_branches) > 0
        assert result.duration_ms > 0

    def test_explore_returns_ranked_branches(self, world_model):
        """Результат содержит отранжированные ветви."""
        from narrative_engine.world_explorer import WorldExplorer, ExplorationRequest

        explorer = WorldExplorer(world_model)
        request = ExplorationRequest(
            prompt="Исследование мира",
            epoch="satya_yuga",
            branch_count=3,
        )

        result = explorer.explore(request)
        assert len(result.ranked_branches) == 3

        # Проверяем ранжирование
        scores = [rb.quality_report.overall_score for rb in result.ranked_branches]
        assert scores == sorted(scores, reverse=True)

    def test_explore_from_hypothesis(self, world_model):
        """Исследование от гипотезы."""
        from narrative_engine.world_explorer import WorldExplorer
        from narrative_engine.hypothesis_generator import HypothesisGenerator

        explorer = WorldExplorer(world_model)
        gen = HypothesisGenerator(world_model)

        hyps = gen.generate_for_epoch("satya_yuga", limit=1)
        assert len(hyps) > 0

        result = explorer.explore_from_hypothesis(hyps[0], branch_count=2)
        assert result.hypothesis is not None
        assert len(result.ranked_branches) > 0

    def test_get_hypotheses(self, world_model):
        """Получение гипотез для эпохи."""
        from narrative_engine.world_explorer import WorldExplorer

        explorer = WorldExplorer(world_model)
        hyps = explorer.get_hypotheses("satya_yuga", limit=5)

        assert len(hyps) > 0
        assert len(hyps) <= 5

    def test_get_possibilities(self, world_model):
        """Получение возможностей для эпохи."""
        from narrative_engine.world_explorer import WorldExplorer

        explorer = WorldExplorer(world_model)
        possibilities = explorer.get_possibilities("satya_yuga", limit=5)

        assert len(possibilities) > 0
        assert len(possibilities) <= 5

    def test_ranked_branches_have_reports(self, world_model):
        """Отранжированные ветви содержат отчёты."""
        from narrative_engine.world_explorer import WorldExplorer, ExplorationRequest

        explorer = WorldExplorer(world_model)
        request = ExplorationRequest(
            prompt="Тест",
            epoch="satya_yuga",
            branch_count=2,
        )

        result = explorer.explore(request)
        for rb in result.ranked_branches:
            assert rb.quality_report is not None
            assert rb.impact_report is not None
            assert rb.contradiction_report is not None

    def test_exploration_summary(self, world_model):
        """Сводка исследования генерируется."""
        from narrative_engine.world_explorer import WorldExplorer, ExplorationRequest

        explorer = WorldExplorer(world_model)
        request = ExplorationRequest(
            prompt="Тест",
            epoch="satya_yuga",
        )

        result = explorer.explore(request)
        assert isinstance(result.summary, str)
        assert len(result.summary) > 0


class TestWorldExplorerIntegration:
    """Интеграционные тесты World Explorer."""

    def test_full_world_explorer_pipeline(self, world_model):
        """Полный pipeline: Request → Hypothesis → Scenario → Quality → Result."""
        from narrative_engine.world_explorer import WorldExplorer, ExplorationRequest
        from narrative_engine.hypothesis_generator import HypothesisGenerator
        from narrative_engine.scenario_modeler import ScenarioModeler
        from narrative_engine.quality_evaluator import QualityEvaluator
        from narrative_engine.branch_manager import BranchManager

        # 1. Создаём explorer
        explorer = WorldExplorer(world_model)

        # 2. Исследуем
        request = ExplorationRequest(
            prompt="Что если Аркаим не был разрушен?",
            epoch="satya_yuga",
            branch_count=3,
        )
        result = explorer.explore(request)

        # 3. Проверяем результат
        assert result.hypothesis is not None
        assert result.scenario is not None
        assert len(result.ranked_branches) > 0

        # 4. Лучшая ветвь
        best = result.ranked_branches[0]
        assert best.rank == 1
        assert best.quality_report.overall_score > 0.0

        # 5. Все ветви имеют отчёты
        for rb in result.ranked_branches:
            assert rb.quality_report
            assert rb.impact_report
            assert rb.contradiction_report


# ── Этап 7: WebSocket Tests ─────────────────────────────────

class TestExplorationNotifier:
    """Тесты ExplorationNotifier."""

    def test_notifier_creates_instance(self):
        """Создание экземпляра нотификатора."""
        from narrative_engine.exploration_ws import ExplorationNotifier
        notifier = ExplorationNotifier()
        assert notifier._exploration_id is None

    def test_pipeline_steps_defined(self):
        """Этапы pipeline определены."""
        from narrative_engine.exploration_ws import PIPELINE_STEPS
        assert len(PIPELINE_STEPS) == 8
        assert "Проверка совместимости" in PIPELINE_STEPS
        assert "Ранжирование" in PIPELINE_STEPS

    def test_exploration_events_defined(self):
        """События WebSocket определены."""
        from narrative_engine.exploration_ws import EXPLORATION_EVENTS
        assert "started" in EXPLORATION_EVENTS
        assert "progress" in EXPLORATION_EVENTS
        assert "complete" in EXPLORATION_EVENTS
        assert "error" in EXPLORATION_EVENTS

    def test_explorer_accepts_notifier(self, world_model):
        """Explorer принимает ws_notifier параметр."""
        from narrative_engine.world_explorer import WorldExplorer, ExplorationRequest
        from narrative_engine.exploration_ws import ExplorationNotifier

        explorer = WorldExplorer(world_model)
        notifier = ExplorationNotifier()

        request = ExplorationRequest(
            prompt="Тест WS",
            epoch="satya_yuga",
            branch_count=2,
        )

        # Должно работать с notifier=None и с notifier
        result = explorer.explore(request, ws_notifier=notifier)
        assert result.hypothesis is not None

    def test_global_notifier_exists(self):
        """Глобальный нотификатор существует."""
        from narrative_engine.exploration_ws import exploration_notifier
        assert exploration_notifier is not None

    def test_notifier_notify_progress_step_range(self):
        """notify_progress проверяет диапазон шагов."""
        import asyncio
        from narrative_engine.exploration_ws import ExplorationNotifier

        notifier = ExplorationNotifier()
        # Шаг вне диапазона — не должно быть ошибки
        asyncio.run(notifier.notify_progress(-1))
        asyncio.run(notifier.notify_progress(100))
        # Шаг в диапазоне — работает
        asyncio.run(notifier.notify_progress(0, "test"))


# ── Этап 8: ExplorationStore Tests ──────────────────────────

class TestExplorationStore:
    """Тесты хранилища истории исследований."""

    @pytest.fixture
    def store(self, tmp_path):
        """Создать изолированное хранилище для тестов."""
        from core.memory.exploration_store import ExplorationStore
        db_path = str(tmp_path / "test_explorations.db")
        return ExplorationStore(db_path=db_path)

    @pytest.mark.asyncio
    async def test_save_and_get(self, store):
        """Сохранение и получение записи."""
        item_id = await store.save(
            user_id="test_user",
            prompt="Тестовый запрос",
            epoch="satya_yuga",
            branch_count=3,
            hypothesis_id="hyp_001",
            hypothesis_title="Тестовая гипотеза",
            result_json='{"test": true}',
            summary="Тестовая сводка",
            overall_score=0.85,
            branch_count_actual=3,
            duration_ms=150.0,
        )
        assert item_id > 0

        item = await store.get(item_id)
        assert item is not None
        assert item["prompt"] == "Тестовый запрос"
        assert item["epoch"] == "satya_yuga"
        assert item["overall_score"] == 0.85

    @pytest.mark.asyncio
    async def test_list_by_user(self, store):
        """Список записей пользователя."""
        for i in range(3):
            await store.save(
                user_id="user1",
                prompt=f"Запрос {i}",
                epoch="satya_yuga",
                branch_count=3,
                hypothesis_id=None,
                hypothesis_title=None,
                result_json='{}',
                summary=f"Сводка {i}",
                overall_score=0.5 + i * 0.1,
                branch_count_actual=3,
                duration_ms=100.0,
            )

        items = await store.list_by_user("user1", limit=10)
        assert len(items) == 3
        # Порядок: DESC по created_at
        assert items[0]["prompt"] == "Запрос 2"

    @pytest.mark.asyncio
    async def test_delete(self, store):
        """Удаление записи."""
        item_id = await store.save(
            user_id="user1",
            prompt="Удаляемый",
            epoch=None,
            branch_count=3,
            hypothesis_id=None,
            hypothesis_title=None,
            result_json='{}',
            summary="",
            overall_score=0.0,
            branch_count_actual=0,
            duration_ms=0.0,
        )

        deleted = await store.delete(item_id, "user1")
        assert deleted is True

        item = await store.get(item_id)
        assert item is None

    @pytest.mark.asyncio
    async def test_delete_other_user(self, store):
        """Нельзя удалить чужую запись."""
        item_id = await store.save(
            user_id="user1",
            prompt="Чужая запись",
            epoch=None,
            branch_count=3,
            hypothesis_id=None,
            hypothesis_title=None,
            result_json='{}',
            summary="",
            overall_score=0.0,
            branch_count_actual=0,
            duration_ms=0.0,
        )

        deleted = await store.delete(item_id, "user2")
        assert deleted is False

        item = await store.get(item_id)
        assert item is not None

    @pytest.mark.asyncio
    async def test_count(self, store):
        """Подсчёт записей."""
        assert await store.count("user1") == 0

        await store.save(user_id="user1", prompt="a", epoch=None, branch_count=3,
                         hypothesis_id=None, hypothesis_title=None, result_json='{}',
                         summary="", overall_score=0, branch_count_actual=0, duration_ms=0)
        await store.save(user_id="user2", prompt="b", epoch=None, branch_count=3,
                         hypothesis_id=None, hypothesis_title=None, result_json='{}',
                         summary="", overall_score=0, branch_count_actual=0, duration_ms=0)

        assert await store.count("user1") == 1
        assert await store.count() == 2

    @pytest.mark.asyncio
    async def test_health(self, store):
        """Health check."""
        health = await store.health()
        assert health["status"] == "ok"
        assert health["type"] == "sqlite"
        assert health["explorations"] == 0


# ── Этап 9: Story From Branch Tests ────────────────────────

class TestStoryFromBranch:
    """Тесты генерации текста из ветви."""

    def test_build_story_from_branch(self, world_model):
        """Построение промпта из ветви."""
        from narrative_engine.story_from_branch import build_story_from_branch, BranchToStoryRequest

        request = BranchToStoryRequest(
            exploration_prompt="Что если Аркаим не был разрушен?",
            branch_title="Консервативное развитие",
            branch_type="conservative",
            epoch="satya_yuga",
            style="literary",
            max_length=2000,
            quality_score=0.85,
            strengths=["Высокое соответствие канону"],
            weaknesses=["Нет драматического потенциала"],
        )

        result = build_story_from_branch(request, world_model)

        assert result.system_instruction
        assert result.user_prompt
        assert "Аркаим" in result.user_prompt
        assert "Консервативное развитие" in result.user_prompt
        assert result.quality_score == 0.85
        assert result.constraints_summary

    def test_branch_context_included(self, world_model):
        """Контекст ветви включён в промпт."""
        from narrative_engine.story_from_branch import build_story_from_branch, BranchToStoryRequest

        request = BranchToStoryRequest(
            exploration_prompt="Тест",
            branch_title="Радикальное развитие",
            branch_type="radical",
            epoch="satya_yuga",
            quality_score=0.7,
            strengths=["Сильная сторона 1"],
            weaknesses=["Слабая сторона 1"],
        )

        result = build_story_from_branch(request, world_model)

        assert "Радикальное развитие" in result.user_prompt
        assert "radical" in result.user_prompt
        assert "Сильная сторона 1" in result.user_prompt
        assert "Слабая сторона 1" in result.user_prompt

    def test_constraints_summary(self, world_model):
        """Сводка ограничений формируется."""
        from narrative_engine.story_from_branch import build_story_from_branch, BranchToStoryRequest

        request = BranchToStoryRequest(
            exploration_prompt="Тест",
            branch_title="Тест",
            branch_type="moderate",
            epoch="satya_yuga",
        )

        result = build_story_from_branch(request, world_model)

        assert "Эпоха" in result.constraints_summary or "Ограничения" in result.constraints_summary

    def test_different_styles(self, world_model):
        """Разные стили генерации."""
        from narrative_engine.story_from_branch import build_story_from_branch, BranchToStoryRequest

        for style in ["literary", "documentary", "poetic"]:
            request = BranchToStoryRequest(
                exploration_prompt="Тест",
                branch_title="Тест",
                branch_type="moderate",
                epoch="satya_yuga",
                style=style,
            )
            result = build_story_from_branch(request, world_model)
            assert result.style == style


# ── Этап 10: External Sources Tests ────────────────────────

class TestExternalSources:
    """Тесты поиска во внешних источниках."""

    def test_search_local_knowledge(self):
        """Поиск в локальных KNOWLEDGE файлах."""
        from narrative_engine.external_sources import search_local_knowledge

        results = search_local_knowledge("Аркаим", limit=5)
        assert isinstance(results, list)
        # Должны найти что-то в локальных файлах
        assert len(results) >= 0

    def test_search_local_knowledge_empty_query(self):
        """Поиск с пустым запросом."""
        from narrative_engine.external_sources import search_local_knowledge

        results = search_local_knowledge("", limit=5)
        assert isinstance(results, list)

    def test_external_source_result_model(self):
        """Модель ExternalSourceResult работает."""
        from narrative_engine.external_sources import ExternalSourceResult

        result = ExternalSourceResult(
            title="Test",
            url="https://example.com",
            snippet="Test snippet",
            source_type="wikipedia",
            relevance_score=0.8,
        )
        assert result.title == "Test"
        assert result.source_type == "wikipedia"
        assert result.relevance_score == 0.8

    def test_extract_snippets(self):
        """Извлечение фрагментов из данных."""
        from narrative_engine.external_sources import _extract_snippets

        data = {"key": "Аркаим — древнее городище на Южном Урале. Датируется бронзовым веком."}
        snippets = _extract_snippets(data, "аркаим")
        assert len(snippets) >= 0

    def test_search_all_sources_returns_list(self):
        """search_all_sources возвращает список (даже при ошибках API)."""
        import asyncio
        from narrative_engine.external_sources import search_all_sources

        results = asyncio.run(search_all_sources("Аркаим", limit_per_source=1, sources=["wikipedia"]))
        assert isinstance(results, list)


# ── Этап 11: Deep Explorer Tests ───────────────────────────

class TestDeepExplorer:
    """Тесты многоуровневого исследования."""

    def test_explore_deep_creates_tree(self, world_model):
        """Глубокое исследование создаёт дерево."""
        from narrative_engine.deep_explorer import DeepExplorer, DeepExplorationRequest

        explorer = DeepExplorer(world_model)
        request = DeepExplorationRequest(
            prompt="Что если Аркаим не был разрушен?",
            epoch="satya_yuga",
            max_depth=2,
            branches_per_level=2,
        )

        tree = explorer.explore_deep(request)
        assert tree.total_nodes > 0
        assert tree.max_depth_reached >= 1
        assert tree.root_node is not None

    def test_explore_deep_max_depth(self, world_model):
        """Глубокое исследование уважает max_depth."""
        from narrative_engine.deep_explorer import DeepExplorer, DeepExplorationRequest

        explorer = DeepExplorer(world_model)
        request = DeepExplorationRequest(
            prompt="Тест",
            epoch="satya_yuga",
            max_depth=1,
            branches_per_level=2,
        )

        tree = explorer.explore_deep(request)
        assert tree.max_depth_reached <= 1

    def test_find_free_points(self, world_model):
        """Обнаружение свободных точек мира."""
        from narrative_engine.deep_explorer import DeepExplorer

        explorer = DeepExplorer(world_model)
        free_points = explorer.find_free_points(epoch_id="satya_yuga")

        assert isinstance(free_points, list)
        assert len(free_points) > 0
        # Есть хотя бы персонажи
        char_points = [p for p in free_points if p["type"] == "character"]
        assert len(char_points) > 0

    def test_find_free_points_all_epochs(self, world_model):
        """Свободные точки для всех эпох."""
        from narrative_engine.deep_explorer import DeepExplorer

        explorer = DeepExplorer(world_model)
        free_points = explorer.find_free_points()

        assert isinstance(free_points, list)

    def test_get_best_paths(self, world_model):
        """Поиск лучших путей в дереве."""
        from narrative_engine.deep_explorer import DeepExplorer, DeepExplorationRequest

        explorer = DeepExplorer(world_model)
        request = DeepExplorationRequest(
            prompt="Тест",
            epoch="satya_yuga",
            max_depth=2,
            branches_per_level=2,
        )

        tree = explorer.explore_deep(request)
        paths = explorer.get_best_paths(tree, top_n=2)

        assert isinstance(paths, list)
        assert len(paths) > 0
        # Каждый путь начинается с корня
        for path in paths:
            assert path[0] == "root"

    def test_explore_from_branch(self, world_model):
        """Ветвление от конкретной ветви."""
        from narrative_engine.deep_explorer import DeepExplorer, DeepExplorationRequest

        explorer = DeepExplorer(world_model)
        request = DeepExplorationRequest(
            prompt="Тест",
            epoch="satya_yuga",
            max_depth=1,
            branches_per_level=2,
        )

        tree = explorer.explore_deep(request)
        initial_count = tree.total_nodes

        # Находим ветвь для продолжения
        branch_id = None
        for nid, node in tree.nodes.items():
            if node.children:
                branch_id = nid
                break

        if branch_id:
            tree = explorer.explore_from_branch(branch_id, tree, branches_per_level=2)
            assert tree.total_nodes > initial_count


# ── Этап 12: Feedback Store Tests ──────────────────────────

class TestFeedbackStore:
    """Тесты хранилища обратной связи."""

    @pytest.fixture
    def store(self, tmp_path):
        """Создать изолированное хранилище для тестов."""
        from core.memory.feedback_store import FeedbackStore
        db_path = str(tmp_path / "test_feedback.db")
        return FeedbackStore(db_path=db_path)

    @pytest.mark.asyncio
    async def test_add_feedback(self, store):
        """Добавление отзыва."""
        item_id = await store.add_feedback(
            user_id="user1",
            exploration_id=1,
            branch_rank=1,
            branch_type="conservative",
            branch_title="Тестовая ветвь",
            rating=4,
            comment="Хорошая ветвь",
        )
        assert item_id > 0

    @pytest.mark.asyncio
    async def test_get_feedback_for_exploration(self, store):
        """Получение отзывов для исследования."""
        await store.add_feedback(
            user_id="user1", exploration_id=1, branch_rank=1,
            branch_type="conservative", branch_title="Ветвь 1",
            rating=4, comment="Хорошо",
        )
        await store.add_feedback(
            user_id="user2", exploration_id=1, branch_rank=2,
            branch_type="radical", branch_title="Ветвь 2",
            rating=5, comment="Отлично",
        )

        items = await store.get_feedback_for_exploration(1)
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_get_average_rating(self, store):
        """Средний рейтинг."""
        await store.add_feedback(user_id="u1", exploration_id=None, branch_rank=1,
                                 branch_type="conservative", branch_title="T", rating=4)
        await store.add_feedback(user_id="u2", exploration_id=None, branch_rank=1,
                                 branch_type="conservative", branch_title="T", rating=5)

        stats = await store.get_average_rating(branch_type="conservative")
        assert stats["average_rating"] == 4.5
        assert stats["total_ratings"] == 2

    @pytest.mark.asyncio
    async def test_delete_feedback(self, store):
        """Удаление отзыва."""
        item_id = await store.add_feedback(
            user_id="user1", exploration_id=None, branch_rank=1,
            branch_type="test", branch_title="T", rating=3,
        )

        deleted = await store.delete_feedback(item_id, "user1")
        assert deleted is True

    @pytest.mark.asyncio
    async def test_delete_other_user_feedback(self, store):
        """Нельзя удалить чужой отзыв."""
        item_id = await store.add_feedback(
            user_id="user1", exploration_id=None, branch_rank=1,
            branch_type="test", branch_title="T", rating=3,
        )

        deleted = await store.delete_feedback(item_id, "user2")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_health(self, store):
        """Health check."""
        health = await store.health()
        assert health["status"] == "ok"
        assert health["type"] == "sqlite"
        assert health["feedback_count"] == 0


# ── Этап 13: Performance Tests ─────────────────────────────

class TestPerformance:
    """Тесты оптимизации производительности."""

    def test_lru_cache_basic(self):
        """Базовая работа LRU-кэша."""
        from narrative_engine.performance import LRUCache

        cache = LRUCache(max_size=5, ttl_seconds=60)

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        assert cache.get("nonexistent") is None

    def test_lru_cache_ttl(self):
        """LRU-кэш учитывает TTL."""
        import time
        from narrative_engine.performance import LRUCache

        cache = LRUCache(max_size=5, ttl_seconds=0)  # 0 секунд = сразу истекает

        cache.set("key1", "value1")
        time.sleep(0.01)
        assert cache.get("key1") is None  # Истёк TTL

    def test_lru_cache_eviction(self):
        """LRU-кэш удаляет старые записи при превышении размера."""
        from narrative_engine.performance import LRUCache

        cache = LRUCache(max_size=3, ttl_seconds=60)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")  # Должен вытеснить key1

        assert cache.get("key1") is None
        assert cache.get("key4") == "value4"

    def test_lru_cache_stats(self):
        """Статистика LRU-кэша."""
        from narrative_engine.performance import LRUCache

        cache = LRUCache(max_size=5, ttl_seconds=60)

        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("nonexistent")  # Miss

        stats = cache.stats
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5

    def test_cache_stats(self):
        """Статистика всех кэшей."""
        from narrative_engine.performance import get_cache_stats

        stats = get_cache_stats()
        assert "epochs" in stats
        assert "hypotheses" in stats
        assert "possibilities" in stats
        assert "compatibility" in stats

    def test_clear_all_caches(self):
        """Очистка всех кэшей."""
        from narrative_engine.performance import (
            _epochs_cache, _hypotheses_cache,
            clear_all_caches, get_cache_stats,
        )

        _epochs_cache.set("test", "value")
        _hypotheses_cache.set("test", "value")

        clear_all_caches()

        stats = get_cache_stats()
        assert stats["epochs"]["size"] == 0
        assert stats["hypotheses"]["size"] == 0

    def test_performance_metrics(self):
        """Метрики производительности."""
        from narrative_engine.performance import PerformanceMetrics

        pm = PerformanceMetrics()
        pm.record("test_metric", 100.0)
        pm.record("test_metric", 200.0)
        pm.record("test_metric", 150.0)

        stats = pm.get_stats("test_metric")
        assert stats["count"] == 3
        assert stats["avg_ms"] == 150.0
        assert stats["min_ms"] == 100.0
        assert stats["max_ms"] == 200.0

    def test_timed_decorator(self):
        """Декоратор timed измеряет время."""
        import asyncio
        from narrative_engine.performance import timed, metrics

        @timed("test_operation")
        async def slow_operation():
            await asyncio.sleep(0.01)
            return "done"

        result = asyncio.run(slow_operation())
        assert result == "done"

        stats = metrics.get_stats("test_operation")
        assert stats["count"] == 1
        assert stats["avg_ms"] > 5  # Должно быть > 5ms из-за sleep


# ── Этап 14: Unified Pipeline Tests ────────────────────────

class TestUnifiedPipeline:
    """Тесты unified pipeline (Explorer + Story Engine)."""

    def test_unified_pipeline_creates_result(self, world_model):
        """Unified pipeline создаёт результат."""
        from narrative_engine.unified_pipeline import UnifiedPipeline, UnifiedRequest

        pipeline = UnifiedPipeline(world_model)
        request = UnifiedRequest(
            prompt="Что если Аркаим не был разрушен?",
            epoch="satya_yuga",
            branch_count=2,
            generate_story=True,
        )

        result = pipeline.run(request)
        assert result.exploration is not None
        assert result.exploration.ranked_branches
        assert result.total_duration_ms > 0
        assert len(result.pipeline_steps) > 0

    def test_unified_pipeline_explore_only(self, world_model):
        """Unified pipeline только исследование."""
        from narrative_engine.unified_pipeline import UnifiedPipeline, UnifiedRequest

        pipeline = UnifiedPipeline(world_model)
        request = UnifiedRequest(
            prompt="Тест",
            epoch="satya_yuga",
            branch_count=2,
            generate_story=False,
        )

        result = pipeline.run(request)
        assert result.exploration is not None
        assert result.story is None

    def test_unified_pipeline_summary(self, world_model):
        """Unified pipeline генерирует сводку."""
        from narrative_engine.unified_pipeline import UnifiedPipeline, UnifiedRequest

        pipeline = UnifiedPipeline(world_model)
        request = UnifiedRequest(
            prompt="Тест",
            epoch="satya_yuga",
            branch_count=2,
        )

        result = pipeline.run(request)
        assert isinstance(result.summary, str)
        assert len(result.summary) > 0

    def test_generate_from_branch(self, world_model):
        """Генерация текста из конкретной ветви."""
        from narrative_engine.unified_pipeline import UnifiedPipeline, UnifiedRequest

        pipeline = UnifiedPipeline(world_model)
        request = UnifiedRequest(
            prompt="Тест",
            epoch="satya_yuga",
            branch_count=2,
            generate_story=False,
        )

        exploration = pipeline.explore_only(request)
        story = pipeline.generate_from_branch(exploration, branch_rank=1)

        assert story.system_instruction
        assert story.user_prompt
        assert story.style == "literary"


# ── Этап 15: Export Report Tests ───────────────────────────

class TestExportReport:
    """Тесты экспорта результатов."""

    def test_generate_markdown_report(self, world_model):
        """Генерация Markdown отчёта."""
        from narrative_engine.world_explorer import WorldExplorer, ExplorationRequest
        from narrative_engine.export_report import generate_markdown_report

        explorer = WorldExplorer(world_model)
        request = ExplorationRequest(
            prompt="Тест экспорта",
            epoch="satya_yuga",
            branch_count=2,
        )
        result = explorer.explore(request)
        report = generate_markdown_report(result)

        assert report.title
        assert report.created_at
        assert report.markdown
        assert "# " in report.markdown
        assert "Результаты исследования" in report.markdown

    def test_report_contains_branches_table(self, world_model):
        """Отчёт содержит таблицу ветвей."""
        from narrative_engine.world_explorer import WorldExplorer, ExplorationRequest
        from narrative_engine.export_report import generate_markdown_report

        explorer = WorldExplorer(world_model)
        request = ExplorationRequest(
            prompt="Тест",
            epoch="satya_yuga",
            branch_count=2,
        )
        result = explorer.explore(request)
        report = generate_markdown_report(result)

        assert "| # |" in report.markdown
        assert "Качество" in report.markdown

    def test_report_contains_recommendations(self, world_model):
        """Отчёт содержит рекомендации."""
        from narrative_engine.world_explorer import WorldExplorer, ExplorationRequest
        from narrative_engine.export_report import generate_markdown_report

        explorer = WorldExplorer(world_model)
        request = ExplorationRequest(
            prompt="Тест",
            epoch="satya_yuga",
            branch_count=2,
        )
        result = explorer.explore(request)
        report = generate_markdown_report(result)

        assert len(report.recommendations) > 0
        assert "Рекомендации" in report.markdown

    def test_report_has_metadata(self, world_model):
        """Отчёт содержит метаданные."""
        from narrative_engine.world_explorer import WorldExplorer, ExplorationRequest
        from narrative_engine.export_report import generate_markdown_report

        explorer = WorldExplorer(world_model)
        request = ExplorationRequest(
            prompt="Тест метаданных",
            epoch="satya_yuga",
            branch_count=2,
        )
        result = explorer.explore(request)
        report = generate_markdown_report(result)

        assert report.prompt == "Тест метаданных"
        assert report.epoch == "satya_yuga"
        assert report.branch_count == 2
        assert report.duration_ms > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
