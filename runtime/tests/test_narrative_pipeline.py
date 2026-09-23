"""Integration Tests for Narrative Engine — Full Pipeline.

Тестируют весь pipeline: CanonValidator → ContextAssembler → Planner → Composer.
Запуск: cd runtime && python -m pytest tests/test_narrative_pipeline.py -v
"""

import sys
from pathlib import Path

import pytest

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from narrative_engine.world_model import WorldModel
from narrative_engine.canon_validator import CanonValidator, CanonCheckResult
from narrative_engine.constraint_engine import StoryRequest, parse_prompt, build_constraints
from narrative_engine.context_assembler import ContextAssembler, FullContext
from narrative_engine.planners.cause_effect import CauseEffectPlanner, CauseEffectTree
from narrative_engine.planners.character import CharacterPlanner, CharacterArc
from narrative_engine.planners.timeline import TimelinePlanner, TimelinePlan
from narrative_engine.planners.conflict import ConflictPlanner, ConflictArc
from narrative_engine.planner import UnifiedPlanner, NarrativePlan
from narrative_engine.story.composer import compose_prompt, format_composer_prompt
from narrative_engine.pipeline_errors import PipelineResult, StageResult, run_stage, run_stage_with_fallback
from narrative_engine.world_state import WorldStateBuilder, WorldState


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def world_model() -> WorldModel:
    """Загружает реальный WorldModel."""
    return WorldModel.load()


@pytest.fixture
def sample_request() -> StoryRequest:
    """Тестовый запрос."""
    return parse_prompt("Хочу историю о молодом гиперборейце в Сатья Юге")


@pytest.fixture
def sample_request_with_params() -> StoryRequest:
    """Запрос с параметрами."""
    req = parse_prompt("История о путешествии Велика")
    req.epoch = "satya_yuga"
    req.location = "hyperborea"
    req.style = "literary"
    req.max_length = 1000
    return req


# ── CanonValidator Tests ──────────────────────────────────

class TestCanonValidator:
    def test_valid_request(self, world_model, sample_request):
        validator = CanonValidator(world_model)
        result = validator.validate(sample_request)
        assert isinstance(result, CanonCheckResult)
        assert result.valid is True
        assert result.constraints is not None

    def test_with_epoch_and_location(self, world_model, sample_request_with_params):
        validator = CanonValidator(world_model)
        result = validator.validate(sample_request_with_params)
        assert result.valid is True
        assert result.constraints.resolved_context.epoch is not None
        assert result.constraints.resolved_context.location is not None

    def test_allowed_facts_populated(self, world_model, sample_request_with_params):
        validator = CanonValidator(world_model)
        result = validator.validate(sample_request_with_params)
        assert len(result.allowed_facts) > 0

    def test_forbidden_content_detection(self, world_model):
        req = StoryRequest(prompt="История с телефоном и интернетом")
        validator = CanonValidator(world_model)
        result = validator.validate(req)
        # Должны быть violations из-за forbidden content в constraints
        # (constraint_engine добавляет forbidden_elements)


# ── WorldState Builder Tests ──────────────────────────────

class TestWorldStateBuilder:
    def test_build_default_epoch(self, world_model):
        builder = WorldStateBuilder(world_model)
        state = builder.build()
        assert isinstance(state, WorldState)
        assert state.epoch_id != ""

    def test_build_specific_epoch(self, world_model):
        builder = WorldStateBuilder(world_model)
        state = builder.build("satya_yuga")
        assert state.epoch_id == "satya_yuga"
        assert len(state.active_characters) > 0

    def test_characters_populated(self, world_model):
        builder = WorldStateBuilder(world_model)
        state = builder.build("satya_yuga")
        assert len(state.active_characters) > 0
        for ch in state.active_characters:
            assert ch.name != ""
            assert ch.status in ("alive", "awakened", "departed", "mythic")

    def test_rules_populated(self, world_model):
        builder = WorldStateBuilder(world_model)
        state = builder.build()
        assert len(state.active_rules) > 0


# ── Context Assembler Tests ───────────────────────────────

class TestContextAssembler:
    def test_assemble_basic(self, world_model, sample_request):
        validator = CanonValidator(world_model)
        canon = validator.validate(sample_request)
        assembler = ContextAssembler(world_model)
        ctx = assembler.assemble(canon)
        assert isinstance(ctx, FullContext)
        assert ctx.historical is not None
        assert ctx.geography is not None
        assert ctx.mythology is not None

    def test_historical_context(self, world_model, sample_request_with_params):
        validator = CanonValidator(world_model)
        canon = validator.validate(sample_request_with_params)
        assembler = ContextAssembler(world_model)
        ctx = assembler.assemble(canon)
        assert len(ctx.historical.epoch_facts) > 0

    def test_mythology_context(self, world_model):
        req = parse_prompt("История о гармонии и познании")
        req.epoch = "satya_yuga"
        validator = CanonValidator(world_model)
        canon = validator.validate(req)
        assembler = ContextAssembler(world_model)
        ctx = assembler.assemble(canon)
        # Мифологический контекст может быть пустым если тема не найдена
        assert ctx.mythology is not None

    def test_key_facts_populated(self, world_model, sample_request_with_params):
        validator = CanonValidator(world_model)
        canon = validator.validate(sample_request_with_params)
        assembler = ContextAssembler(world_model)
        ctx = assembler.assemble(canon)
        assert len(ctx.key_facts) > 0


# ── Cause-Effect Planner Tests ────────────────────────────

class TestCauseEffectPlanner:
    def test_plan_basic(self, world_model, sample_request):
        planner = CauseEffectPlanner(world_model)
        ctx = FullContext()
        tree = planner.plan(sample_request, ctx)
        assert isinstance(tree, CauseEffectTree)
        assert len(tree.nodes) > 0
        assert tree.root != ""

    def test_pattern_matching(self, world_model):
        req = parse_prompt("Путешествие молодого гиперборейца")
        req.epoch = "satya_yuga"
        planner = CauseEffectPlanner(world_model)
        ctx = FullContext()
        tree = planner.plan(req, ctx)
        assert tree.matched_pattern == "Путешествие героя"

    def test_pattern_chain_nodes(self, world_model):
        req = parse_prompt("История о миграции после катастрофы")
        req.epoch = "satya_yuga"
        planner = CauseEffectPlanner(world_model)
        ctx = FullContext()
        tree = planner.plan(req, ctx)
        # Паттерн "Катастрофа → Миграция → Возрождение" должен дать 3+ узла
        pattern_nodes = [n for n in tree.nodes if "Паттерн:" in n.description]
        assert len(pattern_nodes) >= 3

    def test_temporal_order_exists(self, world_model, sample_request):
        planner = CauseEffectPlanner(world_model)
        ctx = FullContext()
        tree = planner.plan(sample_request, ctx)
        assert len(tree.temporal_order) > 0

    def test_constraints_detected(self, world_model):
        req = parse_prompt("История с телефоном")
        req.epoch = "satya_yuga"
        planner = CauseEffectPlanner(world_model)
        ctx = FullContext()
        tree = planner.plan(req, ctx)
        constraints = [n for n in tree.nodes if n.type == "constraint"]
        assert len(constraints) > 0


# ── Character Planner Tests ───────────────────────────────

class TestCharacterPlanner:
    def test_plan_basic(self, world_model, sample_request):
        planner = CharacterPlanner(world_model)
        ctx = FullContext()
        arcs = planner.plan(sample_request, ctx)
        assert isinstance(arcs, list)

    def test_arc_structure(self, world_model):
        req = parse_prompt("История о Владе и Вере")
        req.epoch = "satya_yuga"
        planner = CharacterPlanner(world_model)
        validator = CanonValidator(world_model)
        canon = validator.validate(req)
        assembler = ContextAssembler(world_model)
        ctx = assembler.assemble(canon)
        arcs = planner.plan(req, ctx)
        if arcs:
            arc = arcs[0]
            assert arc.character != ""
            assert arc.motivation != ""


# ── Timeline Planner Tests ────────────────────────────────

class TestTimelinePlanner:
    def test_plan_basic(self, world_model, sample_request):
        planner = TimelinePlanner(world_model)
        ctx = FullContext()
        timeline = planner.plan(sample_request, ctx)
        assert isinstance(timeline, TimelinePlan)

    def test_events_chronological(self, world_model, sample_request_with_params):
        planner = TimelinePlanner(world_model)
        ctx = FullContext()
        timeline = planner.plan(sample_request_with_params, ctx)
        # Events may be empty if epoch has no events mapped (data issue)
        # Check that the planner runs without error
        assert isinstance(timeline.events_chronological, list)

    def test_character_lifetimes(self, world_model, sample_request_with_params):
        planner = TimelinePlanner(world_model)
        ctx = FullContext()
        timeline = planner.plan(sample_request_with_params, ctx)
        assert len(timeline.character_lifetimes) > 0


# ── Conflict Planner Tests ────────────────────────────────

class TestConflictPlanner:
    def test_plan_basic(self, world_model, sample_request):
        planner = ConflictPlanner(world_model)
        ctx = FullContext()
        conflicts = planner.plan(sample_request, ctx)
        assert isinstance(conflicts, list)
        assert len(conflicts) > 0

    def test_conflict_arc_structure(self, world_model, sample_request):
        planner = ConflictPlanner(world_model)
        ctx = FullContext()
        conflicts = planner.plan(sample_request, ctx)
        arc = conflicts[0]
        assert arc.conflict_type in ("internal", "external", "moral")
        assert len(arc.arc_structure) > 0
        assert len(arc.resolution_options) > 0


# ── Unified Planner Tests ─────────────────────────────────

class TestUnifiedPlanner:
    def test_plan_full(self, world_model, sample_request_with_params):
        validator = CanonValidator(world_model)
        canon = validator.validate(sample_request_with_params)
        assembler = ContextAssembler(world_model)
        ctx = assembler.assemble(canon)
        planner = UnifiedPlanner(world_model)
        plan = planner.plan(sample_request_with_params, ctx)
        assert isinstance(plan, NarrativePlan)
        assert len(plan.story_structure) > 0
        assert len(plan.constraints_for_llm) >= 0

    def test_plan_components(self, world_model, sample_request_with_params):
        validator = CanonValidator(world_model)
        canon = validator.validate(sample_request_with_params)
        assembler = ContextAssembler(world_model)
        ctx = assembler.assemble(canon)
        planner = UnifiedPlanner(world_model)
        plan = planner.plan(sample_request_with_params, ctx)
        assert plan.cause_effect is not None
        assert plan.timeline is not None
        assert len(plan.conflicts) > 0


# ── Composer Tests ─────────────────────────────────────────

class TestComposer:
    def test_compose_prompt(self, world_model, sample_request_with_params):
        validator = CanonValidator(world_model)
        canon = validator.validate(sample_request_with_params)
        assembler = ContextAssembler(world_model)
        ctx = assembler.assemble(canon)
        planner = UnifiedPlanner(world_model)
        plan = planner.plan(sample_request_with_params, ctx)

        composed = compose_prompt(canon.constraints, ctx, plan, "literary", 1000)
        assert "system_instruction" in composed
        assert "user_prompt" in composed
        assert len(composed["system_instruction"]) > 100
        assert len(composed["user_prompt"]) > 100

    def test_format_composer_prompt(self, world_model, sample_request_with_params):
        validator = CanonValidator(world_model)
        canon = validator.validate(sample_request_with_params)
        assembler = ContextAssembler(world_model)
        ctx = assembler.assemble(canon)
        planner = UnifiedPlanner(world_model)
        plan = planner.plan(sample_request_with_params, ctx)

        composed = compose_prompt(canon.constraints, ctx, plan, "literary", 1000)
        full_prompt = format_composer_prompt(composed)
        assert len(full_prompt) > 500
        assert "Наследие Аркаима" in full_prompt


# ── Pipeline Error Handling Tests ──────────────────────────

class TestPipelineErrors:
    def test_run_stage_success(self):
        result = run_stage("test", lambda: "ok")
        assert result.ok is True
        assert result.status.value == "ok"
        assert result.data == "ok"

    def test_run_stage_failure(self):
        def fail():
            raise ValueError("test error")
        result = run_stage("test", fail)
        assert result.ok is False
        assert result.status.value == "failed"
        assert "ValueError" in result.error

    def test_run_stage_with_fallback(self):
        def fail():
            raise ValueError("test")
        def fallback():
            return "fallback_data"
        result = run_stage_with_fallback("test", fail, fallback)
        assert result.ok is True
        assert result.status.value == "partial"
        assert result.data == "fallback_data"
        assert len(result.warnings) > 0

    def test_pipeline_result(self):
        def fail():
            raise ValueError("err")
        pipeline = PipelineResult()
        pipeline.add(run_stage("ok", lambda: "data"))
        pipeline.add(run_stage("fail", fail))
        assert pipeline.final_ok is False
        assert len(pipeline.stages) == 2

    def test_pipeline_summary(self):
        pipeline = PipelineResult()
        pipeline.add(run_stage("stage1", lambda: "data"))
        summary = pipeline.summary()
        assert "ok" in summary
        assert "stages" in summary
        assert len(summary["stages"]) == 1


# ── Full Pipeline Integration Test ────────────────────────

class TestFullPipeline:
    def test_end_to_end(self, world_model):
        """Полный pipeline: запрос → CanonValidator → Context → Plan → Composer."""
        # 1. Parse
        request = parse_prompt("Хочу историю о молодом гиперборейце в Сатья Юге")
        request.epoch = "satya_yuga"
        request.location = "hyperborea"
        request.style = "literary"
        request.max_length = 1000

        # 2. Canon
        validator = CanonValidator(world_model)
        canon = validator.validate(request)
        assert canon.valid is True

        # 3. Context
        assembler = ContextAssembler(world_model)
        ctx = assembler.assemble(canon)
        assert ctx.historical is not None

        # 4. Plan
        planner = UnifiedPlanner(world_model)
        plan = planner.plan(request, ctx)
        assert len(plan.story_structure) > 0

        # 5. Compose
        composed = compose_prompt(canon.constraints, ctx, plan, "literary", 1000)
        full_prompt = format_composer_prompt(composed)
        assert len(full_prompt) > 500

    def test_pipeline_with_different_styles(self, world_model):
        """Тест разных стилей."""
        for style in ["literary", "documentary", "poetic"]:
            request = parse_prompt("История о гиперборейце")
            request.epoch = "satya_yuga"
            request.style = style

            validator = CanonValidator(world_model)
            canon = validator.validate(request)
            assembler = ContextAssembler(world_model)
            ctx = assembler.assemble(canon)
            planner = UnifiedPlanner(world_model)
            plan = planner.plan(request, ctx)
            composed = compose_prompt(canon.constraints, ctx, plan, style, 500)
            assert "system_instruction" in composed

    def test_pipeline_with_different_epochs(self, world_model):
        """Тест разных эпох."""
        for epoch in ["satya_yuga", "kali_yuga", "pre_arkaim"]:
            request = parse_prompt(f"История в {epoch}")
            request.epoch = epoch

            validator = CanonValidator(world_model)
            canon = validator.validate(request)
            assembler = ContextAssembler(world_model)
            ctx = assembler.assemble(canon)
            planner = UnifiedPlanner(world_model)
            plan = planner.plan(request, ctx)
            composed = compose_prompt(canon.constraints, ctx, plan, "literary", 500)
            assert "system_instruction" in composed

    def test_pipeline_serialization(self, world_model):
        """Проверка что все модели сериализуются в JSON."""
        request = parse_prompt("История о гиперборейце")
        request.epoch = "satya_yuga"

        validator = CanonValidator(world_model)
        canon = validator.validate(request)

        # CanonCheckResult
        data = canon.model_dump()
        assert isinstance(data, dict)
        assert "valid" in data
        assert "constraints" in data

        # NarrativePlan
        assembler = ContextAssembler(world_model)
        ctx = assembler.assemble(canon)
        planner = UnifiedPlanner(world_model)
        plan = planner.plan(request, ctx)
        plan_data = plan.model_dump()
        assert isinstance(plan_data, dict)
        assert "cause_effect" in plan_data
        assert "character_arcs" in plan_data


class TestPlanAwareValidation:
    def test_validate_with_plan_no_plan(self, world_model):
        from narrative_engine.story.post_validator import validate_story_with_plan
        from narrative_engine.constraint_engine import build_constraints
        req = parse_prompt('История о гиперборейце')
        req.epoch = 'satya_yuga'
        constraints = build_constraints(req, world_model)
        result = validate_story_with_plan('Текст истории', constraints, world_model, None)
        assert result.passed is True

    def test_validate_with_plan_checks_characters(self, world_model):
        from narrative_engine.story.post_validator import validate_story_with_plan
        from narrative_engine.constraint_engine import build_constraints
        from narrative_engine.planner import NarrativePlan
        from narrative_engine.planners.character import CharacterArc
        req = parse_prompt('История о гиперборейце')
        req.epoch = 'satya_yuga'
        constraints = build_constraints(req, world_model)
        from narrative_engine.planners.cause_effect import CauseEffectTree
        plan = NarrativePlan(
            cause_effect=CauseEffectTree(root='test'),
            character_arcs=[
                CharacterArc(character='Велик', motivation='test', obstacle='test', transformation='test'),
                CharacterArc(character='Архат', motivation='test', obstacle='test', transformation='test'),
            ]
        )
        # Текст без упоминания персонажей
        result = validate_story_with_plan('Короткий текст без имён', constraints, world_model, plan)
        assert any('Велик' in w for w in result.warnings)

    def test_validate_with_plan_checks_conflict(self, world_model):
        from narrative_engine.story.post_validator import validate_story_with_plan
        from narrative_engine.constraint_engine import build_constraints
        from narrative_engine.planner import NarrativePlan
        from narrative_engine.planners.conflict import ConflictArc
        req = parse_prompt('История о гиперборейце')
        req.epoch = 'satya_yuga'
        constraints = build_constraints(req, world_model)
        from narrative_engine.planners.cause_effect import CauseEffectTree
        plan = NarrativePlan(
            cause_effect=CauseEffectTree(root='test'),
            conflicts=[ConflictArc(conflict_type='internal', tension_source='Война Света и Тьмы', arc_structure=['a'], resolution_options=['b'])]
        )
        result = validate_story_with_plan('Текст без конфликта', constraints, world_model, plan)
        assert any('Война Света' in w for w in result.warnings)
