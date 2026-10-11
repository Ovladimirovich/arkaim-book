"""M2 tests: TemporalNode, TemporalRelation, TemporalChain, TemporalGap, ReconstructionPath,
PresentAnchor, ArkaimAnchor, TemporalPrecision.
"""

from __future__ import annotations


from narrative_engine.temporal.precision import (
    TemporalPrecision,
    resolve_precision,
    is_known_precision,
    precision_label,
)
from narrative_engine.temporal.node import TemporalNode, TemporalBounds
from narrative_engine.temporal.relation import (
    TemporalRelationType,
    TemporalRelation,
    REVERSE_RELATIONS,
)
from narrative_engine.temporal.chain import TemporalChain, ChainDirection
from narrative_engine.temporal.gap import TemporalGap, EvidenceStatus
from narrative_engine.temporal.reconstruction_path import ReconstructionPath
from narrative_engine.temporal.present_anchor import PresentAnchor
from narrative_engine.temporal.arkaim_anchor import ArkaimAnchor
from narrative_engine.source_levels import (
    ProvenanceCategory,
    ProvenanceTag,
    SourceLevel,
)


# ═══════════════════════════════════════════════════════════════
# TemporalPrecision
# ═══════════════════════════════════════════════════════════════


class TestTemporalPrecision:
    def test_all_precisions_exist(self):
        expected = {
            "EXACT",
            "YEAR",
            "YEAR_RANGE",
            "DECADE",
            "CENTURY",
            "MILLENNIUM",
            "ARCHAEOLOGICAL_PERIOD",
            "RELATIVE",
            "STRATIGRAPHIC",
            "UNKNOWN",
        }
        actual = {p.value for p in TemporalPrecision}
        assert actual == expected

    def test_resolve_precision_string(self):
        assert resolve_precision("EXACT") == TemporalPrecision.EXACT
        assert resolve_precision("UNKNOWN") == TemporalPrecision.UNKNOWN
        assert resolve_precision("century") == TemporalPrecision.CENTURY
        assert resolve_precision("archaeological_period") == TemporalPrecision.ARCHAEOLOGICAL_PERIOD

    def test_resolve_precision_unknown_value(self):
        assert resolve_precision("some_random_value") == TemporalPrecision.UNKNOWN

    def test_is_known_precision(self):
        assert is_known_precision(TemporalPrecision.EXACT) is True
        assert is_known_precision(TemporalPrecision.YEAR) is True
        assert is_known_precision(TemporalPrecision.UNKNOWN) is False
        assert is_known_precision(TemporalPrecision.RELATIVE) is True

    def test_precision_label(self):
        assert precision_label(TemporalPrecision.EXACT) == "Точная дата"
        assert precision_label(TemporalPrecision.UNKNOWN) == "Неизвестно"
        assert precision_label(TemporalPrecision.ARCHAEOLOGICAL_PERIOD) == "Археологический период"

    def test_precision_order(self):
        from narrative_engine.temporal.precision import PRECISION_ORDER

        assert PRECISION_ORDER[TemporalPrecision.EXACT] > PRECISION_ORDER[TemporalPrecision.UNKNOWN]
        assert PRECISION_ORDER[TemporalPrecision.CENTURY] > PRECISION_ORDER[TemporalPrecision.RELATIVE]


# ═══════════════════════════════════════════════════════════════
# TemporalNode
# ═══════════════════════════════════════════════════════════════


class TestTemporalNode:
    def test_create_basic_node(self):
        node = TemporalNode(id="n1", label="Test Node")
        assert node.id == "n1"
        assert node.label == "Test Node"
        assert node.precision == TemporalPrecision.UNKNOWN
        assert node.is_anchor is False

    def test_create_node_with_bounds(self):
        bounds = TemporalBounds(start="2500 BCE", end="2000 BCE", uncertainty="±200 лет")
        node = TemporalNode(id="n1", label="Ancient", precision=TemporalPrecision.CENTURY, bounds=bounds)
        assert node.has_bounds is True
        assert node.is_known_temporal is True
        assert node.bounds.duration_label() == "2500 BCE — 2000 BCE"

    def test_create_node_with_unknown_precision(self):
        """UNKNOWN precision — валидное состояние, не ошибка."""
        node = TemporalNode(id="n_unknown", label="Мифическая эпоха", precision=TemporalPrecision.UNKNOWN)
        assert node.is_known_temporal is False
        assert node.precision == TemporalPrecision.UNKNOWN

    def test_from_epoch(self):
        node = TemporalNode.from_epoch(
            epoch_id="arkaim_era",
            epoch_name_ru="Эпоха Аркаима",
            epoch_order=5,
            precision=TemporalPrecision.RELATIVE,
        )
        assert node.era_id == "arkaim_era"
        assert node.label == "Эпоха Аркаима"
        assert node.precision == TemporalPrecision.RELATIVE

    def test_present_anchor(self):
        node = TemporalNode.present_anchor()
        assert node.id == "temporal_today"
        assert node.precision == TemporalPrecision.EXACT
        assert node.bounds.start == "2025 CE"
        # M8.1: present is HYPOTHESIS, not AUTHOR_CANON
        assert node.is_canon is False
        assert any(p.category == ProvenanceCategory.HYPOTHESIS for p in node.provenance)

    def test_gap_node(self):
        node = TemporalNode.gap_node("gap_1", "Неизвестный пробел")
        assert node.is_gap is True
        assert node.precision == TemporalPrecision.UNKNOWN
        assert node.era_id == ""

    def test_canon_property(self):
        canon_tag = ProvenanceTag(
            source_level=SourceLevel.CANON,
            category=ProvenanceCategory.AUTHOR_CANON,
            confidence=1.0,
        )
        node = TemporalNode(id="n1", label="Test", provenance=[canon_tag])
        assert node.is_canon is True

    def test_external_property(self):
        ext_tag = ProvenanceTag(
            source_level=SourceLevel.HISTORICAL,
            category=ProvenanceCategory.EXTERNAL_SOURCE,
            confidence=0.7,
        )
        node = TemporalNode(id="n1", label="Test", provenance=[ext_tag])
        assert node.is_external is True
        assert node.is_canon is False

    def test_to_dict_roundtrip(self):
        node = TemporalNode(
            id="n1",
            label="Test",
            precision=TemporalPrecision.CENTURY,
            era_id="arkaim_era",
            entity_ids=["arkaim_location"],
            confidence=0.8,
            bounds=TemporalBounds(start="2000 BCE", end="1500 BCE"),
        )
        d = node.to_dict()
        restored = TemporalNode.from_dict(d)
        assert restored.id == node.id
        assert restored.precision == node.precision
        assert restored.era_id == node.era_id
        assert restored.entity_ids == node.entity_ids
        assert restored.confidence == node.confidence

    def test_unknown_date_not_error(self):
        """unknown date ≠ error"""
        node = TemporalNode(id="n1", label="Unknown Era", precision=TemporalPrecision.UNKNOWN)
        assert node.is_known_temporal is False
        # Это не ошибка, это честная оценка
        assert node.confidence >= 0.0

    def test_confidence_not_precision(self):
        """confidence ≠ precision"""
        # Низкая confidence, но точная precision
        node = TemporalNode(
            id="n1",
            label="Hypothetical Exact",
            precision=TemporalPrecision.EXACT,
            confidence=0.3,
        )
        assert node.precision == TemporalPrecision.EXACT
        assert node.confidence == 0.3

        # Высокая confidence, но unknown precision
        node2 = TemporalNode(
            id="n2",
            label="Unknown but trusted",
            precision=TemporalPrecision.UNKNOWN,
            confidence=0.95,
        )
        assert node2.precision == TemporalPrecision.UNKNOWN
        assert node2.confidence == 0.95


# ═══════════════════════════════════════════════════════════════
# TemporalRelation
# ═══════════════════════════════════════════════════════════════


class TestTemporalRelation:
    def test_all_relation_types_exist(self):
        expected = {
            "BEFORE",
            "AFTER",
            "OVERLAPS",
            "CONTAINS",
            "CONTAINED_BY",
            "CONTEMPORARY_WITH",
            "PRECEDES",
            "FOLLOWS",
            "DEVELOPS_FROM",
            "TRANSFORMS_INTO",
            "COEXISTS_WITH",
            "UNKNOWN",
            "CARRIES",
            "CARRIED_BY",
            "TRANSMITS_TO",
            "RECEIVES_FROM",
            "ECHOES",
        }
        actual = {r.value for r in TemporalRelationType}
        assert actual == expected

    def test_reverse_relations(self):
        assert REVERSE_RELATIONS[TemporalRelationType.BEFORE] == TemporalRelationType.AFTER
        assert REVERSE_RELATIONS[TemporalRelationType.CONTAINS] == TemporalRelationType.CONTAINED_BY
        assert REVERSE_RELATIONS[TemporalRelationType.DEVELOPS_FROM] == TemporalRelationType.TRANSFORMS_INTO
        assert REVERSE_RELATIONS[TemporalRelationType.CONTEMPORARY_WITH] == TemporalRelationType.CONTEMPORARY_WITH

    def test_develops_from(self):
        rel = TemporalRelation.develops_from("pre_arkaim", "arkaim_era", strength=0.8)
        assert rel.relation_type == TemporalRelationType.DEVELOPS_FROM
        assert rel.source_id == "pre_arkaim"
        assert rel.target_id == "arkaim_era"
        assert rel.is_developmental is True

    def test_transforms_into(self):
        rel = TemporalRelation.transforms_into("arkaim_era", "post_arkaim", strength=0.7)
        assert rel.relation_type == TemporalRelationType.TRANSFORMS_INTO
        assert rel.is_developmental is True

    def test_precedes(self):
        rel = TemporalRelation.precedes("satya_yuga", "treta_yuga")
        assert rel.relation_type == TemporalRelationType.PRECEDES
        assert rel.is_canon is False  # PRECEDES edges = DERIVED (ADR TEMPORAL §4)

    def test_contemporary_with(self):
        rel = TemporalRelation.contemporary_with("arkaim", "hyperborea")
        assert rel.relation_type == TemporalRelationType.CONTEMPORARY_WITH

    def test_to_dict_roundtrip(self):
        rel = TemporalRelation.develops_from("a", "b", strength=0.9)
        d = rel.to_dict()
        restored = TemporalRelation.from_dict(d)
        assert restored.relation_type == rel.relation_type
        assert restored.source_id == rel.source_id

    def test_developmental_vs_simple_order(self):
        """DEVELOPS_FROM ≠ просто PRECEDES. DEVELOPS_FROM — качественное развитие."""
        precedes = TemporalRelation.precedes("a", "b")
        develops = TemporalRelation.develops_from("a", "b")
        assert precedes.relation_type == TemporalRelationType.PRECEDES
        assert develops.relation_type == TemporalRelationType.DEVELOPS_FROM
        assert precedes.is_developmental is False
        assert develops.is_developmental is True


# ═══════════════════════════════════════════════════════════════
# TemporalChain
# ═══════════════════════════════════════════════════════════════


class TestTemporalChain:
    def test_create_backward_chain(self):
        today = TemporalNode.present_anchor()
        chain = TemporalChain.backward_from_today([today])
        assert chain.direction == ChainDirection.BACKWARD
        assert len(chain.nodes) == 1
        assert chain.id == "backward_chain"

    def test_create_forward_chain(self):
        arkaim = TemporalNode(id="temporal_arkaim", label="Эпоха Аркаима", era_id="arkaim_era")
        chain = TemporalChain.forward_from_arkaim([arkaim])
        assert chain.direction == ChainDirection.FORWARD
        assert len(chain.nodes) == 1

    def test_add_node_and_relation(self):
        a = TemporalNode(id="a", label="A")
        b = TemporalNode(id="b", label="B")
        chain = TemporalChain(id="c1", label="Test", direction=ChainDirection.FORWARD)
        chain.add_node(a)
        chain.add_node(b)
        chain.add_relation(TemporalRelation.precedes("a", "b"))
        assert len(chain.nodes) == 2
        assert len(chain.relations) == 1

    def test_get_node(self):
        a = TemporalNode(id="node_a", label="A")
        chain = TemporalChain(id="c1", label="Test", direction=ChainDirection.FORWARD)
        chain.add_node(a)
        assert chain.get_node("node_a") is a
        assert chain.get_node("nonexistent") is None

    def test_has_gap_between(self):
        a = TemporalNode(id="a", label="A")
        b = TemporalNode(id="b", label="B")
        chain = TemporalChain(id="c1", label="Test", direction=ChainDirection.FORWARD)
        chain.add_node(a)
        chain.add_node(b)
        chain.add_gap(TemporalGap.unknown_gap("g1", "a", "b"))
        assert chain.has_gap_between("a", "b") is True
        assert chain.has_gap_between("a", "a") is False

    def test_is_continuous_with_gap(self):
        a = TemporalNode(id="a", label="A")
        b = TemporalNode(id="b", label="B")
        chain = TemporalChain(id="c1", label="Test", direction=ChainDirection.FORWARD)
        chain.add_node(a)
        chain.add_node(b)
        chain.add_gap(TemporalGap.unknown_gap("g1", "a", "b"))
        assert chain.is_continuous() is False

    def test_non_continuous_chain_is_valid(self):
        """Непрерывная chain — не требование, допустимы gaps."""
        a = TemporalNode(id="a", label="A")
        b = TemporalNode(id="b", label="B")
        gap = TemporalGap.unknown_gap("g1", "a", "b")
        chain = TemporalChain(id="c1", label="Test", direction=ChainDirection.FORWARD)
        chain.add_node(a)
        chain.add_node(b)
        chain.add_gap(gap)
        # Chain валидна, просто не непрерывна
        assert chain.stats()["continuous"] is False

    def test_stats(self):
        a = TemporalNode(id="a", label="A")
        chain = TemporalChain(id="c1", label="Test", direction=ChainDirection.FORWARD)
        chain.add_node(a)
        stats = chain.stats()
        assert stats["nodes"] == 1
        assert stats["direction"] == "FORWARD"

    def test_to_dict_roundtrip(self):
        today = TemporalNode.present_anchor()
        chain = TemporalChain.backward_from_today([today])
        d = chain.to_dict()
        restored = TemporalChain.from_dict(d)
        assert restored.direction == chain.direction
        assert len(restored.nodes) == len(chain.nodes)

    def test_unknown_gap_not_error(self):
        """unknown gap ≠ error."""
        a = TemporalNode(id="a", label="A")
        b = TemporalNode(id="b", label="B")
        gap = TemporalGap.unknown_gap("g1", "a", "b")
        assert gap.has_insufficient_data is True
        # Gap валиден
        chain = TemporalChain(id="c1", label="Test", direction=ChainDirection.FORWARD)
        chain.add_node(a)
        chain.add_node(b)
        chain.add_gap(gap)
        assert chain.gap_count == 1
        assert chain.stats()["continuous"] is False


# ═══════════════════════════════════════════════════════════════
# TemporalGap
# ═══════════════════════════════════════════════════════════════


class TestTemporalGap:
    def test_insufficient_data_is_valid(self):
        """INSUFFICIENT_DATA — валидный результат, не ошибка."""
        gap = TemporalGap.unknown_gap("g1", "a", "b")
        assert gap.has_insufficient_data is True
        assert gap.evidence_status == EvidenceStatus.INSUFFICIENT_DATA

    def test_all_evidence_statuses_exist(self):
        expected = {
            "DOCUMENTED",
            "PARTIALLY_DOCUMENTED",
            "INSUFFICIENT_DATA",
            "RECONSTRUCTABLE",
            "HYPOTHETICAL",
            "UNKNOWN",
        }
        actual = {s.value for s in EvidenceStatus}
        assert actual == expected

    def test_reconstructable_gap(self):
        gap = TemporalGap.reconstructable_gap("g1", "a", "b", ["bridge_x", "bridge_y"])
        assert gap.is_reconstructable is True
        assert gap.bridge_count == 2

    def test_documented_gap(self):
        gap = TemporalGap(
            id="g1",
            from_node="a",
            to_node="b",
            evidence_status=EvidenceStatus.DOCUMENTED,
        )
        assert gap.is_documented is True

    def test_to_dict_roundtrip(self):
        gap = TemporalGap.unknown_gap("g1", "a", "b", reason="no data")
        d = gap.to_dict()
        restored = TemporalGap.from_dict(d)
        assert restored.from_node == gap.from_node
        assert restored.to_node == gap.to_node
        assert restored.evidence_status == gap.evidence_status

    def test_unknown_gap_reason_is_meaningful(self):
        gap = TemporalGap.unknown_gap("g1", "a", "b", reason="Археологические данные недостаточны")
        assert gap.reason == "Археологические данные недостаточны"


# ═══════════════════════════════════════════════════════════════
# ReconstructionPath
# ═══════════════════════════════════════════════════════════════


class TestReconstructionPath:
    def test_create_path(self):
        path = ReconstructionPath(
            id="rp1",
            direction=ChainDirection.BACKWARD,
            description="TODAY → ARKAIM",
        )
        assert path.id == "rp1"
        assert path.direction == ChainDirection.BACKWARD
        assert path.is_complete is True  # без gaps — complete

    def test_path_with_gap(self):
        path = ReconstructionPath(id="rp1", direction=ChainDirection.BACKWARD)
        path.add_gap(TemporalGap.unknown_gap("g1", "a", "b"))
        assert path.is_complete is False
        assert path.unknown_gap_count == 1

    def test_add_node_relation_gap(self):
        a = TemporalNode(id="a", label="A")
        b = TemporalNode(id="b", label="B")
        path = ReconstructionPath(id="rp1", direction=ChainDirection.FORWARD)
        path.add_node(a)
        path.add_node(b)
        path.add_relation(TemporalRelation.precedes("a", "b"))
        path.add_gap(TemporalGap.unknown_gap("g1", "a", "b"))
        assert path.node_count == 2
        assert len(path.relations) == 1
        assert path.gap_count == 1
        assert path.is_complete is False

    def test_get_node_at(self):
        a = TemporalNode(id="a", label="A")
        b = TemporalNode(id="b", label="B")
        path = ReconstructionPath(id="rp1", direction=ChainDirection.FORWARD)
        path.add_node(a)
        path.add_node(b)
        assert path.get_node_at(0) is a
        assert path.get_node_at(1) is b
        assert path.get_node_at(5) is None

    def test_stats(self):
        a = TemporalNode(id="a", label="A")
        path = ReconstructionPath(id="rp1", direction=ChainDirection.FORWARD)
        path.add_node(a)
        s = path.stats()
        assert s["nodes"] == 1
        assert s["is_complete"] is True

    def test_to_dict_roundtrip(self):
        a = TemporalNode(id="a", label="A")
        path = ReconstructionPath(id="rp1", direction=ChainDirection.FORWARD)
        path.add_node(a)
        d = path.to_dict()
        restored = ReconstructionPath.from_dict(d)
        assert restored.direction == path.direction
        assert len(restored.nodes) == 1
        # Проверяем импорт внутри from_dict работает
        assert restored.id == "rp1"


# ═══════════════════════════════════════════════════════════════
# PresentAnchor
# ═══════════════════════════════════════════════════════════════


class TestPresentAnchor:
    def test_create_anchor(self):
        anchor = PresentAnchor.for_entity("modern_urban", "Современная инфраструктура")
        assert anchor.id == "present_modern_urban"
        assert anchor.modern_entity_id == "modern_urban"
        assert anchor.is_canon is True

    def test_add_temporal_nodes(self):
        anchor = PresentAnchor.for_entity("e1", "Test")
        anchor.temporal_nodes = ["temporal_today", "temporal_historical"]
        assert anchor.node_count == 2

    def test_to_dict_roundtrip(self):
        anchor = PresentAnchor.for_entity("e1", "Test")
        anchor.temporal_nodes = ["n1", "n2"]
        d = anchor.to_dict()
        restored = PresentAnchor.from_dict(d)
        assert restored.modern_entity_id == anchor.modern_entity_id
        assert restored.temporal_nodes == anchor.temporal_nodes


# ═══════════════════════════════════════════════════════════════
# ArkaimAnchor
# ═══════════════════════════════════════════════════════════════


class TestArkaimAnchor:
    def test_create_from_existing_data(self):
        anchor = ArkaimAnchor.from_existing_data()
        assert anchor.id == "arkaim_anchor"
        assert anchor.epoch_id == "arkaim_era"
        assert anchor.location_id == "arkaim"
        assert anchor.is_canon_anchor is True
        assert anchor.has_archaeological_support is True
        assert len(anchor.provenance) == 2

    def test_node_representation(self):
        anchor = ArkaimAnchor.from_existing_data()
        node = anchor.node
        assert node.id == "temporal_arkaim_anchor"
        assert node.era_id == "arkaim_era"
        assert node.is_anchor is True
        assert node.precision == TemporalPrecision.RELATIVE

    def test_no_new_canon_created(self):
        """ArkaimAnchor НЕ создаёт новых авторских утверждений."""
        anchor = ArkaimAnchor.from_existing_data()
        # Провенанс — только существующие данные
        canon_count = sum(1 for p in anchor.provenance if p.category == ProvenanceCategory.AUTHOR_CANON)
        external_count = sum(1 for p in anchor.provenance if p.category == ProvenanceCategory.EXTERNAL_SOURCE)
        assert canon_count >= 1  # только существующий канон
        assert external_count >= 1  # археологические данные

    def test_to_dict_roundtrip(self):
        anchor = ArkaimAnchor.from_existing_data()
        d = anchor.to_dict()
        restored = ArkaimAnchor.from_dict(d)
        assert restored.epoch_id == anchor.epoch_id
        assert restored.location_id == anchor.location_id
        assert restored.precision == anchor.precision

    def test_arkaim_as_temporal_anchor_not_historical_fact(self):
        """ArkaimAnchor — temporal anchor, не исторический факт."""
        anchor = ArkaimAnchor.from_existing_data()
        # provenance показывает mixed источники
        categories = {p.category for p in anchor.provenance}
        assert ProvenanceCategory.AUTHOR_CANON in categories
        assert ProvenanceCategory.EXTERNAL_SOURCE in categories
        # Не все данные — канон


# ═══════════════════════════════════════════════════════════════
# Critical M2 Rules
# ═══════════════════════════════════════════════════════════════


class TestCriticalRules:
    def test_unknown_date_not_error(self):
        """unknown date ≠ error."""
        node = TemporalNode(id="n1", label="Unknown", precision=TemporalPrecision.UNKNOWN)
        assert node.is_known_temporal is False
        # Но node валиден
        assert node.label == "Unknown"

    def test_unknown_gap_not_error(self):
        """unknown gap ≠ error."""
        gap = TemporalGap.unknown_gap("g1", "a", "b")
        assert gap.has_insufficient_data is True
        # Gap валиден
        assert gap.id == "gap_g1"

    def test_high_confidence_not_canon(self):
        """high confidence ≠ canon."""
        tag = ProvenanceTag(
            source_level=SourceLevel.USER_HYPOTHESIS,
            category=ProvenanceCategory.HYPOTHESIS,
            confidence=0.95,
        )
        node = TemporalNode(id="n1", label="Hypothesis", provenance=[tag], confidence=0.95)
        assert node.is_hypothesis is True
        assert node.is_canon is False
        assert node.confidence == 0.95

    def test_external_not_canon(self):
        """external source ≠ canon."""
        tag = ProvenanceTag(
            source_level=SourceLevel.HISTORICAL,
            category=ProvenanceCategory.EXTERNAL_SOURCE,
            confidence=1.0,
        )
        node = TemporalNode(id="n1", label="External", provenance=[tag])
        assert node.is_external is True
        assert node.is_canon is False

    def test_reconstruction_not_fact(self):
        """RECONSTRUCTION ≠ FACT."""
        tag = ProvenanceTag(
            source_level=SourceLevel.SCIENTIFIC,
            category=ProvenanceCategory.RECONSTRUCTION,
            confidence=0.85,
        )
        node = TemporalNode(id="n1", label="Reconstruction", provenance=[tag])
        assert node.is_reconstruction is True
        assert node.is_canon is False

    def test_arkaim_anchor_no_new_canon(self):
        """ArkaimAnchor не создаёт новых авторских утверждений."""
        anchor = ArkaimAnchor.from_existing_data()
        # Все provenance tags — из существующих источников
        for tag in anchor.provenance:
            assert tag.source_title in ("КНИГА.md", "ARCHAEOLOGY.json")

    def test_developmental_relation_requires_evidence(self):
        """DEVELOPS_FROM relation имеет HYPOTHESIS provenance."""
        rel = TemporalRelation.develops_from("a", "b")
        assert rel.is_developmental is True
        assert rel.provenance[0].category == ProvenanceCategory.HYPOTHESIS
        # Развитие — гипотеза, пока нет доказательств

    def test_precedes_is_derived_from_epoch_order(self):
        """PRECEDES relation из epoch ordering — DERIVED (не AUTHOR_CANON)."""
        rel = TemporalRelation.precedes("satya_yuga", "treta_yuga")
        assert rel.is_canon is False
        assert rel.provenance[0].category == ProvenanceCategory.DERIVED


# ── TEMPORAL_LEGACY_REFINEMENT: New Relation Types ────────────────


class TestCARRIESRelationType:
    """CARRIES: character → knowledge/teaching."""

    def test_carries_type_exists(self):
        assert TemporalRelationType.CARRIES.value == "CARRIES"

    def test_carried_by_type_exists(self):
        assert TemporalRelationType.CARRIED_BY.value == "CARRIED_BY"

    def test_carries_reverse_is_carried_by(self):
        assert REVERSE_RELATIONS[TemporalRelationType.CARRIES] == TemporalRelationType.CARRIED_BY

    def test_carried_by_reverse_is_carries(self):
        assert REVERSE_RELATIONS[TemporalRelationType.CARRIED_BY] == TemporalRelationType.CARRIES

    def test_carries_factory(self):
        rel = TemporalRelation.carries("char_teacher", "knowledge_teaching", description="Единое Учение")
        assert rel.relation_type == TemporalRelationType.CARRIES
        assert rel.source_id == "char_teacher"
        assert rel.target_id == "knowledge_teaching"
        assert rel.description == "Единое Учение"
        assert rel.provenance[0].category == ProvenanceCategory.AUTHOR_CANON
        assert rel.reverse_type == TemporalRelationType.CARRIED_BY

    def test_carries_is_contextual(self):
        rel = TemporalRelation.carries("a", "b")
        assert rel.is_contextual is True

    def test_carries_not_developmental(self):
        rel = TemporalRelation.carries("a", "b")
        assert rel.is_developmental is False

    def test_carries_roundtrip(self):
        rel = TemporalRelation.carries("velik", "teaching", description="Учение Истины")
        d = rel.to_dict()
        rel2 = TemporalRelation.from_dict(d)
        assert rel2.relation_type == TemporalRelationType.CARRIES
        assert rel2.description == "Учение Истины"


class TestTRANSMITS_TO_TeRelationType:
    """TRANSMITS_TO: character → character (teacher → student)."""

    def test_transmits_to_type_exists(self):
        assert TemporalRelationType.TRANSMITS_TO.value == "TRANSMITS_TO"

    def test_receives_from_type_exists(self):
        assert TemporalRelationType.RECEIVES_FROM.value == "RECEIVES_FROM"

    def test_transmits_to_reverse(self):
        assert REVERSE_RELATIONS[TemporalRelationType.TRANSMITS_TO] == TemporalRelationType.RECEIVES_FROM

    def test_receives_from_reverse(self):
        assert REVERSE_RELATIONS[TemporalRelationType.RECEIVES_FROM] == TemporalRelationType.TRANSMITS_TO

    def test_transmits_to_factory(self):
        rel = TemporalRelation.transmits_to("teacher", "student", description="передача Учения")
        assert rel.relation_type == TemporalRelationType.TRANSMITS_TO
        assert rel.provenance[0].category == ProvenanceCategory.AUTHOR_CANON
        assert rel.description == "передача Учения"

    def test_transmits_to_is_contextual(self):
        rel = TemporalRelation.transmits_to("a", "b")
        assert rel.is_contextual is True


class TestECHOESRelationType:
    """ECHOES: epoch ↔ epoch (structural parallel, NOT causation)."""

    def test_echoes_type_exists(self):
        assert TemporalRelationType.ECHOES.value == "ECHOES"

    def test_echoes_is_self_reverse(self):
        assert REVERSE_RELATIONS[TemporalRelationType.ECHOES] == TemporalRelationType.ECHOES

    def test_echoes_factory(self):
        rel = TemporalRelation.echoes("epoch_atlantis", "epoch_today", description="технологии без духовности")
        assert rel.relation_type == TemporalRelationType.ECHOES
        assert rel.provenance[0].category == ProvenanceCategory.HYPOTHESIS
        assert rel.description == "технологии без духовности"
        assert "не историческая причинность" in rel.provenance[0].notes or "not historical causation" in rel.provenance[0].notes

    def test_echoes_not_developmental(self):
        rel = TemporalRelation.echoes("a", "b")
        assert rel.is_developmental is False

    def test_echoes_is_contextual(self):
        rel = TemporalRelation.echoes("a", "b")
        assert rel.is_contextual is True

    def test_echoes_provenance_is_hypothesis(self):
        rel = TemporalRelation.echoes("a", "b")
        assert rel.provenance[0].category == ProvenanceCategory.HYPOTHESIS

    def test_no_inherits_from(self):
        """INHERITS_FROM не существует — используется DEVELOPS_FROM."""
        assert not hasattr(TemporalRelationType, "INHERITS_FROM")


class TestNewReverseCompleteness:
    """Все новые типы имеют корректные обратные."""

    def test_all_new_types_in_reverse_map(self):
        new_types = [
            TemporalRelationType.CARRIES,
            TemporalRelationType.CARRIED_BY,
            TemporalRelationType.TRANSMITS_TO,
            TemporalRelationType.RECEIVES_FROM,
            TemporalRelationType.ECHOES,
        ]
        for rt in new_types:
            assert rt in REVERSE_RELATIONS, f"{rt} missing from REVERSE_RELATIONS"

    def test_reverse_of_reverse_is_original(self):
        """Обратное от обратного = оригинал."""
        pairs = [
            (TemporalRelationType.CARRIES, TemporalRelationType.CARRIED_BY),
            (TemporalRelationType.TRANSMITS_TO, TemporalRelationType.RECEIVES_FROM),
            (TemporalRelationType.ECHOES, TemporalRelationType.ECHOES),
        ]
        for a, b in pairs:
            assert REVERSE_RELATIONS[b] == a
