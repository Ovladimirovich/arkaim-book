# -*- coding: utf-8 -*-
"""
Stage 3 targeted tests — World Model Structural Gap Detection.

Покрытие:
- структурные правила детектора (missing_description, empty_properties,
  empty_relationships, isolated_entity, low_confidence, missing_temporal,
  unknown_provenance) на синтетических сущностях;
- неизвестное confidence не считается низкой уверенностью;
- отсутствие связи — допустимое состояние (LOW severity, не ошибка);
- каждый GAP прослеживается до исходной сущности (entity_snapshot + provenance);
- диагностика read-only: World Model не мутируется;
- run_world_gap_cycle(apply_stage2=False) НЕ запускает Stage 2;
- expand_gap_via_stage2 работает через моки и не пишет в хранилища;
- реальная структура модели: обнаружение пробелов на фактических данных;
- candidate_sources ссылается только на реально существующие файлы/механизмы.
"""

import copy
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "core" / "CORE"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.services.world_gap_detector import (  # noqa: E402
    CATEGORY_REQUIRED_PROPERTIES,
    LOW_CONFIDENCE_THRESHOLD,
    GapSeverity,
    GapType,
    WorldGap,
    WorldGapDetector,
    WorldGapReport,
    detect_world_gaps,
    expand_gap_via_stage2,
    run_world_gap_cycle,
)


# ─────────────────────────────────────────────────────────────────
# Синтетические заглушки (fake WorldModel / engine / graph)
# ─────────────────────────────────────────────────────────────────


class FakeRelationGraph:
    """Минимальный граф: словарь entity_id -> (out, in)."""

    def __init__(self, links: dict[str, tuple[int, int]] | None = None):
        self._links = links or {}

    def get_entity_context(self, entity_id: str) -> dict:
        out_c, in_c = self._links.get(entity_id, (0, 0))
        return {
            "entity_id": entity_id,
            "outgoing": [],
            "incoming": [],
            "outgoing_count": out_c,
            "incoming_count": in_c,
        }

    def get_stats(self) -> dict:
        with_rel = sum(1 for o, i in self._links.values() if o or i)
        return {
            "total_relations": sum(o + i for o, i in self._links.values()),
            "by_type": {},
            "entities_with_relations": with_rel,
        }


class FakeWorldModel:
    def __init__(self, categories: dict[str, list[dict]]):
        self._categories = categories

    def get_categories(self) -> list[str]:
        return list(self._categories.keys())

    def get_category(self, category: str) -> list[dict]:
        return self._categories.get(category.lower(), [])


class FakeEngine:
    def __init__(self, graph: FakeRelationGraph | None = None):
        self._relation_graph = graph or FakeRelationGraph()


def make_detector(categories: dict[str, list[dict]], links: dict[str, tuple[int, int]] | None = None) -> WorldGapDetector:
    return WorldGapDetector(
        engine=FakeEngine(FakeRelationGraph(links)),
        wm=FakeWorldModel(categories),
    )


def full_entity(**overrides) -> dict:
    """Сущность без пробелов (для проверки, что лишние GAP не появляются)."""
    entity = {
        "id": "geo_1",
        "name": "Аркаим",
        "category": "geography",
        "description": "Поселение бронзового века в Южном Зауралье.",
        "properties": {"coordinates": {"lat": 52.6, "lon": 66.0}},
        "relationships": [{"type": "geographic", "target": "steppe"}],
        "confidence": 0.9,
        "provenance_category": "AUTHOR_CANON",
        "source": "book:chunk_1",
        "source_level": "PRIMARY",
    }
    entity.update(overrides)
    return entity


def gap_types(gaps: list[WorldGap]) -> set[str]:
    return {g.gap_type for g in gaps}


# ─────────────────────────────────────────────────────────────────
# Синтетические правила детектора
# ─────────────────────────────────────────────────────────────────


class TestSyntheticRules:
    def test_full_entity_produces_no_gaps(self):
        detector = make_detector({"geography": [full_entity()]}, links={"geo_1": (1, 1)})
        report = detector.detect_world_gaps()
        assert report.gaps == []
        assert report.total_entities_scanned == 1

    def test_missing_description_is_high_severity(self):
        detector = make_detector({"geography": [full_entity(description="")]})
        report = detector.detect_world_gaps()
        gaps = [g for g in report.gaps if g.gap_type == GapType.MISSING_DESCRIPTION.value]
        assert len(gaps) == 1
        assert gaps[0].severity == GapSeverity.HIGH.value
        assert gaps[0].reason
        assert gaps[0].entity_id == "geo_1"

    def test_missing_required_property_category_configurable(self):
        # geography требует properties.coordinates — конфигурируемый список
        assert "properties.coordinates" in CATEGORY_REQUIRED_PROPERTIES["geography"]
        entity = full_entity(properties={})
        detector = make_detector({"geography": [entity]})
        report = detector.detect_world_gaps()
        gaps = [g for g in report.gaps if g.gap_type == GapType.EMPTY_PROPERTIES.value]
        assert len(gaps) == 1
        assert "properties.coordinates" in gaps[0].description

    def test_required_properties_dotted_path_resolved(self):
        entity = full_entity(properties={"coordinates": {"lat": 1.0}})
        # правило — только наличие properties.coordinates (dict), не вложенные поля
        detector = make_detector({"geography": [entity]})
        report = detector.detect_world_gaps()
        assert not [g for g in report.gaps if g.gap_type == GapType.EMPTY_PROPERTIES.value]

    def test_empty_relationships_is_low_severity_and_not_an_error(self):
        detector = make_detector(
            {"geography": [full_entity(relationships=[])]},
            links={"geo_1": (2, 1)},
        )
        report = detector.detect_world_gaps()
        gaps = [g for g in report.gaps if g.gap_type == GapType.EMPTY_RELATIONSHIPS.value]
        assert len(gaps) == 1
        assert gaps[0].severity == GapSeverity.LOW.value
        # reason явно говорит: это может быть допустимым состоянием
        assert "допустимым состоянием" in gaps[0].reason

    def test_isolated_entity_detected_via_graph(self):
        # relationships есть у сущности, но в RelationGraph она не участвует
        detector = make_detector({"geography": [full_entity()]}, links={})
        report = detector.detect_world_gaps()
        gaps = [g for g in report.gaps if g.gap_type == GapType.ISOLATED_ENTITY.value]
        assert len(gaps) == 1
        assert "RelationGraph" in gaps[0].reason

    def test_entity_in_graph_not_isolated(self):
        detector = make_detector({"geography": [full_entity()]}, links={"geo_1": (1, 0)})
        report = detector.detect_world_gaps()
        assert not [g for g in report.gaps if g.gap_type == GapType.ISOLATED_ENTITY.value]

    def test_unknown_confidence_is_not_low_confidence(self):
        entity = full_entity()
        del entity["confidence"]  # неизвестное значение
        detector = make_detector({"geography": [entity]})
        report = detector.detect_world_gaps()
        assert not [g for g in report.gaps if g.gap_type == GapType.LOW_CONFIDENCE.value]

    def test_explicit_low_confidence_detected(self):
        entity = full_entity(confidence=LOW_CONFIDENCE_THRESHOLD - 0.1)
        detector = make_detector({"geography": [entity]})
        report = detector.detect_world_gaps()
        gaps = [g for g in report.gaps if g.gap_type == GapType.LOW_CONFIDENCE.value]
        assert len(gaps) == 1
        assert gaps[0].severity == GapSeverity.MEDIUM.value
        # неизвестное значение не приравнивается к низкой — в reason явно зафиксировано
        assert "Неизвестное" in gaps[0].reason

    def test_missing_temporal_only_for_temporal_categories(self):
        civ = full_entity(id="civ_1", name="Культура", category="civilizations", properties={})
        geo = full_entity(properties={"coordinates": {"lat": 1.0, "lon": 2.0}})
        detector = make_detector({"civilizations": [civ], "geography": [geo]})
        report = detector.detect_world_gaps()
        temporal = [g for g in report.gaps if g.gap_type == GapType.MISSING_TEMPORAL.value]
        assert len(temporal) == 1
        assert temporal[0].category == "civilizations"

    def test_unknown_provenance_is_high_severity(self):
        entity = full_entity(provenance_category="")
        detector = make_detector({"geography": [entity]})
        report = detector.detect_world_gaps()
        gaps = [g for g in report.gaps if g.gap_type == GapType.UNKNOWN_PROVENANCE.value]
        assert len(gaps) == 1
        assert gaps[0].severity == GapSeverity.HIGH.value

    def test_every_gap_traces_to_source_entity(self):
        entity = full_entity(description="", confidence=0.2)
        detector = make_detector({"geography": [entity]})
        report = detector.detect_world_gaps()
        assert report.gaps
        for gap in report.gaps:
            assert gap.entity_id == entity["id"]
            assert gap.entity_name == entity["name"]
            # снимок сущности прослеживается до исходных полей
            assert gap.entity_snapshot["id"] == entity["id"]
            assert gap.entity_snapshot["confidence"] == entity["confidence"]
            # provenance исходного утверждения сохранён
            assert gap.provenance["source"] == entity["source"]
            assert gap.provenance["provenance_category"] == entity["provenance_category"]

    def test_report_aggregates(self):
        e1 = full_entity(description="")
        e2 = full_entity(id="geo_2", name="Второе", description="", confidence=0.1)
        detector = make_detector({"geography": [e1, e2]}, links={})
        report = detector.detect_world_gaps()
        assert isinstance(report, WorldGapReport)
        assert report.total_entities_scanned == 2
        assert report.by_category.get("geography") == len(report.gaps)
        assert report.by_severity
        assert sum(report.by_type.values()) == len(report.gaps)
        assert report.mutated is False

    def test_candidate_sources_only_existing_mechanisms(self):
        detector = make_detector({"geography": [full_entity(description="")]})
        report = detector.detect_world_gaps()
        for gap in report.gaps:
            assert gap.candidate_sources
            for src in gap.candidate_sources:
                # только реально существующие механизмы проекта
                assert src.startswith(
                    (
                        "entity_source:",
                        "world_model_category:",
                        "knowledge_files:",
                        "search:",
                    )
                ), src
            # файлы из knowledge_files обязаны существовать
            for src in gap.candidate_sources:
                if src.startswith("knowledge_files:"):
                    for fname in src[len("knowledge_files:") :].split(","):
                        assert (REPO_ROOT / "core" / "KNOWLEDGE" / fname).exists(), fname


# ─────────────────────────────────────────────────────────────────
# Read-only: диагностика ничего не меняет
# ─────────────────────────────────────────────────────────────────


class TestReadOnlyGuarantee:
    def test_scan_does_not_mutate_categories(self):
        categories = {"geography": [full_entity(description="")]}
        before = copy.deepcopy(categories)
        detector = make_detector(categories)
        detector.detect_world_gaps()
        assert categories == before

    def test_real_world_model_not_mutated(self):
        """Скан реальной World Model не меняет данные (deep-copy до/после)."""
        detector = WorldGapDetector()
        wm = detector._wm
        before = {c: copy.deepcopy(wm.get_category(c)) for c in wm.get_categories()}
        detector.detect_world_gaps()
        after = {c: copy.deepcopy(wm.get_category(c)) for c in wm.get_categories()}
        assert before == after

    def test_run_cycle_reports_no_mutation_and_no_stage2(self):
        with patch("core.services.world_gap_detector.stage2_expand", new_callable=AsyncMock) as mock_expand:
            result = run_world_gap_cycle(apply_stage2=False)
        mock_expand.assert_not_called()
        assert result["stage2_applied"] is False
        assert result["stage2_results"] == []
        assert isinstance(result["report"], WorldGapReport)
        assert result["report"].mutated is False
        assert result["note"]


# ─────────────────────────────────────────────────────────────────
# Интеграция со Stage 2 (только через моки, без записи)
# ─────────────────────────────────────────────────────────────────


class TestStage2Integration:
    @pytest.mark.asyncio
    async def test_expand_gap_refused_when_not_auto_closeable(self):
        gap = WorldGap(
            entity_id="x",
            entity_name="X",
            category="geography",
            gap_type=GapType.UNKNOWN_PROVENANCE.value,
            severity=GapSeverity.HIGH.value,
            description="d",
            reason="r",
            can_auto_stage2=False,
        )
        with patch("core.services.world_gap_detector.stage2_expand", new_callable=AsyncMock) as mock_expand:
            result = await expand_gap_via_stage2(gap)
        mock_expand.assert_not_called()
        assert result is None

    @pytest.mark.asyncio
    async def test_expand_gap_calls_stage2_with_mocks(self):
        gap = WorldGap(
            entity_id="geo_1",
            entity_name="Аркаим",
            category="geography",
            gap_type=GapType.MISSING_DESCRIPTION.value,
            severity=GapSeverity.HIGH.value,
            description="d",
            reason="r",
            can_auto_stage2=True,
        )
        expected = object()
        with (
            patch(
                "core.services.world_gap_detector.stage2_expand",
                new_callable=AsyncMock,
                return_value=expected,
            ) as mock_expand,
            patch(
                "core.services.world_gap_detector.resolve_related_entities",
                return_value=([{"name": "Аркаим"}], {}),
            ),
            patch(
                "core.services.world_gap_detector.gather_knowledge_core_context",
                return_value=[{"chunk": "c1"}],
            ),
        ):
            result = await expand_gap_via_stage2(gap)
        assert result is expected
        kwargs = mock_expand.call_args.kwargs
        assert "Аркаим" in kwargs["question"]
        assert kwargs["related_entities"] == [{"name": "Аркаим"}]
        assert kwargs["knowledge_contexts"] == [{"chunk": "c1"}]

    @pytest.mark.asyncio
    async def test_expand_gap_survives_resolver_failures(self):
        """Падение резолверов не роняет вызов Stage 2."""
        gap = WorldGap(
            entity_id="geo_1",
            entity_name="Аркаим",
            category="geography",
            gap_type=GapType.MISSING_DESCRIPTION.value,
            severity=GapSeverity.HIGH.value,
            description="d",
            reason="r",
            can_auto_stage2=True,
        )
        expected = object()
        with (
            patch(
                "core.services.world_gap_detector.stage2_expand",
                new_callable=AsyncMock,
                return_value=expected,
            ),
            patch(
                "core.services.world_gap_detector.resolve_related_entities",
                side_effect=RuntimeError("boom"),
            ),
            patch(
                "core.services.world_gap_detector.gather_knowledge_core_context",
                side_effect=RuntimeError("boom"),
            ),
        ):
            result = await expand_gap_via_stage2(gap)
        assert result is expected

    def test_run_cycle_never_auto_applies_stage2_even_if_flag_true(self):
        """apply_stage2=True не приводит к неявной записи — только явный expand()."""
        with patch("core.services.world_gap_detector.stage2_expand", new_callable=AsyncMock) as mock_expand:
            result = run_world_gap_cycle(apply_stage2=True)
        mock_expand.assert_not_called()
        assert result["stage2_applied"] is False
        assert result["stage2_results"] == []


# ─────────────────────────────────────────────────────────────────
# Реальная структура модели
# ─────────────────────────────────────────────────────────────────


class TestRealWorldModel:
    def test_scan_real_model_produces_explainable_gaps(self):
        report = detect_world_gaps()
        assert report.total_entities_scanned > 0
        assert report.mutated is False
        for gap in report.gaps:
            # объяснимость: тип, описание, причина, снимок сущности
            assert gap.gap_type in {t.value for t in GapType}
            assert gap.severity in {s.value for s in GapSeverity}
            assert gap.description
            assert gap.reason
            assert gap.entity_id
            assert gap.entity_snapshot.get("id") == gap.entity_id
            assert isinstance(gap.provenance, dict)
            assert gap.candidate_sources

    def test_real_model_aggregates_consistent(self):
        report = detect_world_gaps()
        assert sum(report.by_type.values()) == len(report.gaps)
        assert sum(report.by_category.values()) == len(report.gaps)
        assert sum(report.by_severity.values()) == len(report.gaps)
        assert report.auto_closeable == sum(1 for g in report.gaps if g.can_auto_stage2)
