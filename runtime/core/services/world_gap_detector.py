# -*- coding: utf-8 -*-
"""
World Model Structural Gap Detection — Stage 3.

Read-only diagnostic over World Engine + WorldModelExt + RelationGraph.
Discovers structural gaps in world model entities (missing description,
empty properties, no relations, low confidence, unknown provenance,
missing temporal context) without mutating any store.

Does NOT launch Stage 2 automatically. expand_gap_via_stage2() exists
as a callable entry point but run_world_gap_cycle(apply_stage2=True)
is not part of any automatic cycle. Use with explicit await only.

Диагностика не изменяет World Model, Temporal, crosswalk или любые хранилища.
Обнаруженный пробел — это диагностический результат, а не новый факт о мире.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from narrative_engine.source_levels import ProvenanceCategory
from narrative_engine.relation_models import RelationGraph
from narrative_engine.world_engine import WorldEngine, get_world_engine
from narrative_engine.world_model_ext import WorldModelExt, get_world_model_ext

from core.services.ask_expansion_orchestrator import expand as stage2_expand
from core.services.knowledge_core_context import gather_knowledge_core_context
from core.services.related_entities import resolve_related_entities

log = logging.getLogger("hermes.world_gap_detector")

LOW_CONFIDENCE_THRESHOLD = 0.5

CATEGORY_REQUIRED_PROPERTIES: dict[str, list[str]] = {
    "geography": ["properties.coordinates"],
    "civilizations": ["properties.epoch"],
}

CATEGORY_NEEDS_TEMPORAL = {"civilizations", "events", "chronology"}


class GapType(str, Enum):
    MISSING_DESCRIPTION = "missing_description"
    EMPTY_PROPERTIES = "empty_properties"
    EMPTY_RELATIONSHIPS = "empty_relationships"
    ISOLATED_ENTITY = "isolated_entity"
    LOW_CONFIDENCE = "low_confidence"
    MISSING_TEMPORAL = "missing_temporal"
    UNKNOWN_PROVENANCE = "unknown_provenance"


class GapSeverity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class WorldGap:
    """Один обнаруженный структурный пробел в сущности World Model."""

    entity_id: str
    entity_name: str
    category: str
    gap_type: str
    severity: str
    description: str
    reason: str
    candidate_sources: list[str] = field(default_factory=list)
    can_auto_stage2: bool = False
    provenance: dict[str, Any] = field(default_factory=dict)
    entity_snapshot: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorldGapReport:
    """Агрегированный отчёт о пробелах World Model."""

    total_entities_scanned: int
    total_relations_in_graph: int
    gaps: list[WorldGap] = field(default_factory=list)
    by_category: dict[str, int] = field(default_factory=dict)
    by_type: dict[str, int] = field(default_factory=dict)
    by_severity: dict[str, int] = field(default_factory=dict)
    auto_closeable: int = 0
    mutated: bool = False


class WorldGapDetector:
    """Сканирует World Model и находит структурные пробелы сущностей."""

    def __init__(
        self,
        engine: Optional[WorldEngine] = None,
        wm: Optional[WorldModelExt] = None,
    ):
        self._engine = engine or get_world_engine()
        self._wm = wm or get_world_model_ext()
        self._graph: Optional[RelationGraph] = self._engine._relation_graph

    def _entity_in_graph(self, entity_id: str) -> bool:
        if self._graph is None:
            return False
        ctx = self._graph.get_entity_context(entity_id)
        return ctx.get("outgoing_count", 0) > 0 or ctx.get("incoming_count", 0) > 0

    def _graph_stats(self) -> dict[str, Any]:
        if self._graph is None:
            return {"total_relations": 0, "by_type": {}, "entities_with_relations": 0}
        return self._graph.get_stats()

    def _discover_knowledge_files(self) -> list[str]:
        try:
            repo_root = Path(__file__).resolve().parents[3]
            knowledge_dir = repo_root / "core" / "KNOWLEDGE"
            if knowledge_dir.exists():
                return sorted(f.name for f in knowledge_dir.glob("*.json"))
        except Exception:
            pass
        return []

    def _entity_snapshot(self, entity: dict[str, Any]) -> dict[str, Any]:
        properties = entity.get("properties", {}) or {}
        relationships = entity.get("relationships", []) or []
        return {
            "id": entity.get("id", ""),
            "name": entity.get("name", ""),
            "category": entity.get("category", ""),
            "description": (entity.get("description", "") or "")[:120],
            "properties_keys": sorted(properties.keys()) if isinstance(properties, dict) else [],
            "relationships_count": len(relationships) if isinstance(relationships, list) else 0,
            "source": entity.get("source", ""),
            "provenance_category": entity.get("provenance_category", ""),
            "source_level": entity.get("source_level", ""),
            "confidence": entity.get("confidence", None),
        }

    def _provenance_info(self, entity: dict[str, Any]) -> dict[str, Any]:
        return {
            "source": entity.get("source", ""),
            "provenance_category": entity.get("provenance_category", ""),
            "provenance_notes": entity.get("provenance_notes", ""),
            "source_level": entity.get("source_level", ""),
            "confidence": entity.get("confidence", None),
        }

    def _candidate_sources(self, entity: dict[str, Any], category: str) -> list[str]:
        sources: list[str] = []
        entity_source = entity.get("source")
        if entity_source:
            sources.append(f"entity_source:{entity_source}")
        sources.append(f"world_model_category:{category}")
        knowledge_files = self._discover_knowledge_files()
        relevant_files: list[str] = []
        cat_lower = category.lower()
        for fname in knowledge_files:
            name_lower = fname.lower()
            if cat_lower in name_lower or any(token in name_lower for token in cat_lower.split("_") if len(token) > 3):
                relevant_files.append(fname)
        if relevant_files:
            sources.append(f"knowledge_files:{','.join(relevant_files[:5])}")
        sources.append("search:world_engine_search")
        sources.append("search:related_entities")
        return sources

    def _check_entity(self, entity: dict[str, Any], category: str) -> list[WorldGap]:
        gaps: list[WorldGap] = []
        entity_id = str(entity.get("id", ""))
        entity_name = str(entity.get("name", ""))
        description = str(entity.get("description", "") or "").strip()
        properties = entity.get("properties", {}) or {}
        relationships = entity.get("relationships", []) or []
        confidence = entity.get("confidence", None)
        provenance_category = entity.get("provenance_category", "")
        snapshot = self._entity_snapshot(entity)
        provenance = self._provenance_info(entity)

        if not description:
            gaps.append(
                WorldGap(
                    entity_id=entity_id,
                    entity_name=entity_name,
                    category=category,
                    gap_type=GapType.MISSING_DESCRIPTION.value,
                    severity=GapSeverity.HIGH.value,
                    description="У сущности нет текстового описания (поле description пустое).",
                    reason=(f"description отсутствует или пустая для сущности '{entity_name}' ({entity_id}, категория {category})."),
                    candidate_sources=self._candidate_sources(entity, category),
                    can_auto_stage2=True,
                    provenance=provenance,
                    entity_snapshot=snapshot,
                )
            )

        required = CATEGORY_REQUIRED_PROPERTIES.get(category, [])
        missing_props: list[str] = []
        if isinstance(entity, dict):
            for req in required:
                parts = req.split(".")
                val: Any = entity  # путь задаётся от сущности
                found = True
                for part in parts:
                    if not isinstance(val, dict) or part not in val:
                        found = False
                        break
                    val = val[part]
                if not found:
                    missing_props.append(req)
        elif required:
            missing_props = list(required)

        if missing_props:
            gaps.append(
                WorldGap(
                    entity_id=entity_id,
                    entity_name=entity_name,
                    category=category,
                    gap_type=GapType.EMPTY_PROPERTIES.value,
                    severity=GapSeverity.MEDIUM.value,
                    description=(f"Отсутствуют требуемые свойства категории: {', '.join(missing_props)}."),
                    reason=(f"Для категории '{category}' ожидаются поля {required}, но в сущности '{entity_name}' отсутствуют: {missing_props}."),
                    candidate_sources=self._candidate_sources(entity, category),
                    can_auto_stage2=False,
                    provenance=provenance,
                    entity_snapshot=snapshot,
                )
            )

        if not relationships:
            gaps.append(
                WorldGap(
                    entity_id=entity_id,
                    entity_name=entity_name,
                    category=category,
                    gap_type=GapType.EMPTY_RELATIONSHIPS.value,
                    severity=GapSeverity.LOW.value,
                    description=("У сущности нет записанных связей (поле relationships пустое)."),
                    reason=(f"relationships пуст для '{entity_name}' ({entity_id}). Это может быть реальным пробелом или допустимым состоянием."),
                    candidate_sources=self._candidate_sources(entity, category),
                    can_auto_stage2=True,
                    provenance=provenance,
                    entity_snapshot=snapshot,
                )
            )

        if not self._entity_in_graph(entity_id):
            gaps.append(
                WorldGap(
                    entity_id=entity_id,
                    entity_name=entity_name,
                    category=category,
                    gap_type=GapType.ISOLATED_ENTITY.value,
                    severity=GapSeverity.MEDIUM.value,
                    description=("Сущность изолирована — нет связей ни входящих, ни исходящих в графе RelationGraph."),
                    reason=(f"Сущность '{entity_name}' ({entity_id}) не присутствует в RelationGraph ни как источник, ни как цель связи."),
                    candidate_sources=self._candidate_sources(entity, category),
                    can_auto_stage2=True,
                    provenance=provenance,
                    entity_snapshot=snapshot,
                )
            )

        if confidence is not None and isinstance(confidence, (int, float)) and confidence < LOW_CONFIDENCE_THRESHOLD:
            gaps.append(
                WorldGap(
                    entity_id=entity_id,
                    entity_name=entity_name,
                    category=category,
                    gap_type=GapType.LOW_CONFIDENCE.value,
                    severity=GapSeverity.MEDIUM.value,
                    description=(f"Низкая достоверность источника: confidence={confidence} (порог < {LOW_CONFIDENCE_THRESHOLD})."),
                    reason=(
                        f"Поле confidence явно задано значением {confidence}, "
                        "что ниже технического порога. Неизвестное (отсутствующее) "
                        "значение не считается низкой уверенностью."
                    ),
                    candidate_sources=self._candidate_sources(entity, category),
                    can_auto_stage2=False,
                    provenance=provenance,
                    entity_snapshot=snapshot,
                )
            )

        if category in CATEGORY_NEEDS_TEMPORAL:
            has_epoch = False
            if isinstance(properties, dict):
                has_epoch = bool(properties.get("epoch"))
            if not has_epoch:
                gaps.append(
                    WorldGap(
                        entity_id=entity_id,
                        entity_name=entity_name,
                        category=category,
                        gap_type=GapType.MISSING_TEMPORAL.value,
                        severity=GapSeverity.MEDIUM.value,
                        description=("Отсутствует временная привязка (epoch) в свойствах сущности."),
                        reason=(f"Для категории '{category}' ожидается properties.epoch, но в '{entity_name}' оно отсутствует."),
                        candidate_sources=self._candidate_sources(entity, category),
                        can_auto_stage2=True,
                        provenance=provenance,
                        entity_snapshot=snapshot,
                    )
                )

        if provenance_category is None or str(provenance_category).strip() == "" or str(provenance_category).upper() == ProvenanceCategory.UNKNOWN.value:
            gaps.append(
                WorldGap(
                    entity_id=entity_id,
                    entity_name=entity_name,
                    category=category,
                    gap_type=GapType.UNKNOWN_PROVENANCE.value,
                    severity=GapSeverity.HIGH.value,
                    description="Происхождение данных не определено (UNKNOWN или отсутствует).",
                    reason=(f"provenance_category='{provenance_category}' для '{entity_name}' ({entity_id}); traceability к источнику отсутствует."),
                    candidate_sources=self._candidate_sources(entity, category),
                    can_auto_stage2=False,
                    provenance=provenance,
                    entity_snapshot=snapshot,
                )
            )

        return gaps

    def detect_world_gaps(self) -> WorldGapReport:
        report = WorldGapReport(
            total_entities_scanned=0,
            total_relations_in_graph=self._graph_stats().get("total_relations", 0),
        )
        graph_stats = self._graph_stats()
        report.total_relations_in_graph = graph_stats.get("total_relations", 0)
        for category in self._wm.get_categories():
            items = self._wm.get_category(category)
            if not isinstance(items, list):
                continue
            for entity in items:
                if not isinstance(entity, dict):
                    continue
                report.total_entities_scanned += 1
                entity_gaps = self._check_entity(entity, category)
                report.gaps.extend(entity_gaps)
        by_category: dict[str, int] = {}
        by_type: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        auto_closeable = 0
        for gap in report.gaps:
            by_category[gap.category] = by_category.get(gap.category, 0) + 1
            by_type[gap.gap_type] = by_type.get(gap.gap_type, 0) + 1
            by_severity[gap.severity] = by_severity.get(gap.severity, 0) + 1
            if gap.can_auto_stage2:
                auto_closeable += 1
        report.by_category = by_category
        report.by_type = by_type
        report.by_severity = by_severity
        report.auto_closeable = auto_closeable
        report.mutated = False
        log.info(
            "world_gap_scan_done scanned=%d gaps=%d auto_closeable=%d",
            report.total_entities_scanned,
            len(report.gaps),
            auto_closeable,
        )
        return report


def detect_world_gaps() -> WorldGapReport:
    """Удобная обёртка: создать детектор и просканировать World Model."""
    detector = WorldGapDetector()
    return detector.detect_world_gaps()


async def expand_gap_via_stage2(gap: WorldGap) -> Any:
    """Сформировать запрос Stage 2 expansion для одного GAP.

    Вызывается только явно. Не запускается автоматически в циклах.
    Возвращает ExpansionResult (или None, если Stage 2 не применим).
    """
    if not gap.can_auto_stage2:
        log.warning(
            "stage2_not_applicable entity=%s gap_type=%s",
            gap.entity_id,
            gap.gap_type,
        )
        return None

    question = f"Расскажи о {gap.entity_name}"

    try:
        related_entities = resolve_related_entities({"question": question, "answer": ""})
    except Exception as exc:  # noqa: BLE001
        log.warning("stage2_related_entities_failed entity=%s error=%s", gap.entity_id, exc)
        related_entities = []

    try:
        knowledge_contexts = gather_knowledge_core_context(related_entities)
    except Exception as exc:  # noqa: BLE001
        log.warning("stage2_knowledge_context_failed entity=%s error=%s", gap.entity_id, exc)
        knowledge_contexts = []

    result = await stage2_expand(
        question=question,
        related_entities=related_entities,
        knowledge_contexts=knowledge_contexts,
    )
    return result


def run_world_gap_cycle(*, apply_stage2: bool = False) -> dict[str, Any]:
    """Синхронное read-only обнаружение пробелов.

    По умолчанию (apply_stage2=False) только обнаруживает и описывает пробелы.
    apply_stage2=True принимается для совместимости интерфейса, но не
    запускает расширение автоматически — для явного вызова Stage 2
    используйте expand_gap_via_stage2() с await.
    """
    report = detect_world_gaps()
    return {
        "report": report,
        "stage2_applied": False,
        "stage2_results": [],
        "note": ("Read-only detection only. Stage 2 expansion is not launched automatically. Call expand_gap_via_stage2() explicitly with await."),
    }
