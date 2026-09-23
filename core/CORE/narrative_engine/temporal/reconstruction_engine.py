"""TemporalReconstructionEngine — анализ temporal graph и поиск путей.

M3: Engine реконструкции временных цепочек.
Не создаёт новые узлы. Не заполняет пробелы автоматически.
Работает только с существующими данными.

Принцип:
  existing evidence → existing temporal graph → candidate traversal → ReconstructionPath
  НЕ: gap → invented node → historical fact
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from narrative_engine.source_levels import (
    ProvenanceCategory,
    ProvenanceTag,
    SourceLevel,
    canonical_provenance,
    hypothesis_provenance,
    external_provenance,
)
from narrative_engine.temporal.node import TemporalNode
from narrative_engine.temporal.relation import (
    TemporalRelation,
    TemporalRelationType,
)
from narrative_engine.temporal.chain import TemporalChain, ChainDirection
from narrative_engine.temporal.gap import TemporalGap, EvidenceStatus
from narrative_engine.temporal.reconstruction_path import ReconstructionPath
from narrative_engine.temporal.graph import TemporalGraph
from narrative_engine.temporal.path_validator import PathValidator, PathValidationResult

log = logging.getLogger("hermes.narrative.temporal_reconstruction")

# ── Paths ────────────────────────────────────────────────────────────

DEFAULT_RECONSTRUCTIONS_DIR = Path("runtime/runtime_data/temporal/reconstructions")


@dataclass
class ReconstructionResult:
    """Результат реконструкции."""
    path: ReconstructionPath
    validation: PathValidationResult
    gap_handled: bool = False
    gap_id: Optional[str] = None
    discovered_paths: int = 0
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "path": self.path.to_dict(),
            "validation": {
                "is_valid": self.validation.is_valid,
                "is_hard_valid": self.validation.is_hard_valid,
                "score": self.validation.score,
                "violations": [
                    {"rule": v.rule_id, "severity": v.severity, "description": v.description}
                    for v in self.validation.violations
                ],
                "warnings": [
                    {"rule": v.rule_id, "severity": v.severity, "description": v.description}
                    for v in self.validation.warnings
                ],
            },
            "gap_handled": self.gap_handled,
            "gap_id": self.gap_id,
            "discovered_paths": self.discovered_paths,
            "notes": self.notes,
        }


class TemporalReconstructionEngine:
    """Engine реконструкции temporal paths.

    Поддерживает:
      - BACKWARD: TODAY → HISTORY → ARKAIM
      - FORWARD: ARKAIM → DEVELOPMENT → TODAY
      - Gap detection и candidate bridge finding
      - Path validation
      - Provenance preservation
    """

    def __init__(self):
        self._graph = TemporalGraph()
        self._validator = PathValidator()
        self._reconstruction_dir = DEFAULT_RECONSTRUCTIONS_DIR
        self._loaded = False
        self._reconstruction_counter = 0

    # ── Node / Relation management ───────────────────────────────────

    def add_node(self, node: TemporalNode) -> None:
        """Добавить узел в граф."""
        self._graph.add_node(node)

    def add_relation(self, rel: TemporalRelation) -> None:
        """Добавить relation в граф."""
        self._graph.add_relation(rel)

    def remove_node(self, node_id: str) -> bool:
        """Удалить узел из графа."""
        if node_id in self._graph._nodes:
            del self._graph._nodes[node_id]
            # Clean up relations
            for key in list(self._graph._outgoing.keys()):
                self._graph._outgoing[key] = [
                    r for r in self._graph._outgoing[key]
                    if r.source_id != node_id and r.target_id != node_id
                ]
            for key in list(self._graph._incoming.keys()):
                self._graph._incoming[key] = [
                    r for r in self._graph._incoming[key]
                    if r.source_id != node_id and r.target_id != node_id
                ]
            return True
        return False

    def get_node(self, node_id: str) -> Optional[TemporalNode]:
        return self._graph.get_node(node_id)

    def bfs_path(self, source_id: str, target_id: str, max_depth: int = 10) -> Optional[list[str]]:
        """Delegate BFS path to underlying graph."""
        return self._graph.bfs_path(source_id, target_id, max_depth)

    def all_paths(self, source_id: str, target_id: str, max_depth: int = 10) -> list[list[str]]:
        """Delegate all-paths to underlying graph."""
        return self._graph.all_paths(source_id, target_id, max_depth)

    def get_all_nodes(self) -> list[TemporalNode]:
        return list(self._graph._nodes.values())

    def get_all_relations(self) -> list[TemporalRelation]:
        all_rels: list[TemporalRelation] = []
        seen = set()
        for rels in self._graph._outgoing.values():
            for r in rels:
                if r.id not in seen:
                    seen.add(r.id)
                    all_rels.append(r)
        return all_rels

    # ── Path Finding ─────────────────────────────────────────────────

    def find_paths(
        self,
        source_id: str,
        target_id: str,
        direction: ChainDirection = ChainDirection.BACKWARD,
        max_depth: int = 10,
    ) -> list[ReconstructionResult]:
        """Найти все пути между source и target.

        Возвращает список ReconstructionResult для каждого найденного пути.
        """
        results: list[ReconstructionResult] = []

        # BFS для нахождения всех путей
        raw_paths = self._graph.all_paths(source_id, target_id, max_depth=max_depth)

        if not raw_paths:
            # Проверим, существуют ли узлы
            src_node = self._graph.get_node(source_id)
            tgt_node = self._graph.get_node(target_id)
            if not src_node:
                log.warning("source_node_not_found id=%s", source_id)
            if not tgt_node:
                log.warning("target_node_not_found id=%s", target_id)
            return results

        for path_node_ids in raw_paths:
            path = self._build_path_result(
                path_node_ids, direction, source_id, target_id
            )
            if path:
                results.append(path)

        return results

    def find_shortest_path(
        self,
        source_id: str,
        target_id: str,
        direction: ChainDirection = ChainDirection.BACKWARD,
    ) -> Optional[ReconstructionResult]:
        """Найти кратчайший путь (BFS)."""
        path_ids = self._graph.bfs_path(source_id, target_id)
        if not path_ids:
            return None
        return self._build_path_result(path_ids, direction, source_id, target_id)

    # ── Gap Reconstruction ───────────────────────────────────────────

    def reconstruct_gap(
        self,
        gap: TemporalGap,
        max_candidates: int = 5,
    ) -> list[ReconstructionResult]:
        """Попробовать реконструировать gap через candidate_bridges.

        Если candidate_bridges пуст — возвращаем пустой список (не заполняем автоматически).
        """
        results: list[ReconstructionResult] = []

        # Проверяем, существуют ли узлы gap
        from_node = self._graph.get_node(gap.from_node)
        to_node = self._graph.get_node(gap.to_node)

        if not from_node:
            log.warning("gap_from_node_missing id=%s", gap.from_node)
            return results
        if not to_node:
            log.warning("gap_to_node_missing id=%s", gap.to_node)
            return results

        # Если есть candidate_bridges — проверяем их
        if gap.candidate_bridges:
            for bridge_id in gap.candidate_bridges[:max_candidates]:
                bridge_node = self._graph.get_node(bridge_id)
                if not bridge_node:
                    log.info("candidate_bridge_not_found id=%s", bridge_id)
                    continue

                # Проверяем путь from_node → bridge → to_node
                path1 = self._graph.bfs_path(gap.from_node, bridge_id, max_depth=5)
                path2 = self._graph.bfs_path(bridge_id, gap.to_node, max_depth=5)

                if path1 and path2:
                    full_path = path1 + path2[1:]  # union
                    result = self._build_path_result(
                        full_path,
                        ChainDirection.BACKWARD,
                        gap.from_node,
                        gap.to_node,
                    )
                    if result:
                        result.gap_handled = True
                        result.gap_id = gap.id
                        result.notes = f"Candidate bridge: {bridge_id}"
                        results.append(result)
        else:
            # Нет candidate_bridges — gap не может быть реконструирован
            log.info("gap_no_candidates id=%s from=%s to=%s", gap.id, gap.from_node, gap.to_node)
            # Возвращаем результат с информацией о невозможности реконструкции
            empty_path = ReconstructionPath(
                id=f"gap_{gap.id}_unresolved",
                direction=ChainDirection.BACKWARD,
                nodes=[from_node, to_node],
                provenance=[hypothesis_provenance(confidence=0.0)],
                description=f"Gap {gap.id}: no candidate bridges, reconstruction impossible",
            )
            results.append(ReconstructionResult(
                path=empty_path,
                validation=PathValidationResult(is_valid=True),
                gap_handled=False,
                gap_id=gap.id,
                notes="No candidate bridges available",
            ))

        return results

    def detect_gaps(
        self,
        chain: TemporalChain,
    ) -> list[TemporalGap]:
        """Обнаружить gaps в существующей chain."""
        gaps: list[TemporalGap] = []

        # Сортируем узлы по direction
        nodes_by_id = {n.id: n for n in chain.nodes}

        for rel in chain.relations:
            src = nodes_by_id.get(rel.source_id)
            tgt = nodes_by_id.get(rel.target_id)
            if not src or not tgt:
                continue

            # Если relation имеет HYPOTHESIS provenance и не имеет явной temporal связи
            # между nodes — это кандидат в gap
            has_temporal_link = any(
                r.relation_type in (
                    TemporalRelationType.PRECEDES,
                    TemporalRelationType.BEFORE,
                    TemporalRelationType.AFTER,
                    TemporalRelationType.FOLLOWS,
                )
                for r in chain.relations
                if (r.source_id == rel.source_id and r.target_id == rel.target_id) or
                   (r.source_id == rel.target_id and r.target_id == rel.source_id)
            )

            if not has_temporal_link and rel.relation_type in (
                TemporalRelationType.DEVELOPS_FROM,
                TemporalRelationType.TRANSFORMS_INTO,
            ):
                # Developmental relation without temporal anchor — potential gap
                gap = TemporalGap(
                    id=f"gap_{rel.source_id}_{rel.target_id}",
                    from_node=rel.source_id,
                    to_node=rel.target_id,
                    reason=f"Developmental relation without temporal anchor: {rel.relation_type.value}",
                    evidence_status=EvidenceStatus.INSUFFICIENT_DATA,
                )
                gaps.append(gap)

        return gaps

    # ── Chain Reconstruction ─────────────────────────────────────────

    def reconstruct_chain(
        self,
        anchor_id: str,
        direction: ChainDirection = ChainDirection.BACKWARD,
        max_depth: int = 10,
    ) -> Optional[ReconstructionPath]:
        """Построить chain от anchor в указанном направлении."""
        anchor = self._graph.get_node(anchor_id)
        if not anchor:
            log.warning("anchor_node_not_found id=%s", anchor_id)
            return None

        # BFS в нужном направлении
        if direction == ChainDirection.BACKWARD:
            # Ищем узлы, которые ведут К anchor (incoming)
            path_ids = self._trace_backward(anchor_id, max_depth)
        else:
            # Ищем узлы, которые ведут ОТ anchor (outgoing)
            path_ids = self._trace_forward(anchor_id, max_depth)

        if not path_ids:
            log.info("no_path_found anchor=%s direction=%s", anchor_id, direction.value)
            return None

        return self._build_chain_result(path_ids, direction)

    # ── Provenance Helpers ───────────────────────────────────────────

    @staticmethod
    def compute_path_provenance(
        nodes: list[TemporalNode],
        relations: list[TemporalRelation],
    ) -> list[ProvenanceTag]:
        """Compute provenance for a path — lowest common denominator.

        Rule: if ANY node/relation is HYPOTHESIS, result is HYPOTHESIS.
        Rule: if ANY is EXTERNAL_SOURCE, result is at most RECONSTRUCTION.
        Rule: AUTHOR_CANON only if ALL are AUTHOR_CANON.
        """
        categories = set()
        for node in nodes:
            for tag in node.provenance:
                categories.add(tag.category)
        for rel in relations:
            for tag in rel.provenance:
                categories.add(tag.category)

        tags: list[ProvenanceTag] = []

        if categories == {ProvenanceCategory.AUTHOR_CANON}:
            tags.append(canonical_provenance())
        elif categories == {ProvenanceCategory.EXTERNAL_SOURCE}:
            tags.append(external_provenance(confidence=0.7))
        elif ProvenanceCategory.HYPOTHESIS in categories:
            tags.append(hypothesis_provenance(confidence=0.5))
        elif ProvenanceCategory.RECONSTRUCTION in categories:
            tags.append(ProvenanceTag(
                source_level=SourceLevel.SCIENTIFIC,
                category=ProvenanceCategory.RECONSTRUCTION,
                confidence=0.6,
                notes="path contains reconstruction — not historical fact",
            ))
        else:
            # Mixed or unknown
            tags.append(ProvenanceTag(
                source_level=SourceLevel.SYSTEM_INTERPRETATION,
                category=ProvenanceCategory.HYPOTHESIS,
                confidence=0.4,
                notes="mixed provenance — treated as hypothesis",
            ))

        return tags

    @staticmethod
    def compute_path_confidence(
        nodes: list[TemporalNode],
        relations: list[TemporalRelation],
    ) -> float:
        """Compute path confidence — minimum of all components.

        Confidence does NOT upgrade provenance.
        """
        confidences = [n.confidence for n in nodes]
        confidences += [r.confidence for r in relations]
        return min(confidences) if confidences else 0.0

    # ── Internal Methods ─────────────────────────────────────────────

    def _build_path_result(
        self,
        node_ids: list[str],
        direction: ChainDirection,
        source_id: str,
        target_id: str,
    ) -> Optional[ReconstructionResult]:
        """Build ReconstructionResult from path node IDs."""
        nodes = []
        relations = []
        prev_id = None

        for nid in node_ids:
            node = self._graph.get_node(nid)
            if node:
                nodes.append(node)
            if prev_id:
                # Find relation between prev and current
                for rel in self._graph.get_outgoing(prev_id):
                    if rel.target_id == nid:
                        relations.append(rel)
                        break
                else:
                    for rel in self._graph.get_incoming(prev_id):
                        if rel.source_id == nid:
                            relations.append(rel)
                            break
            prev_id = nid

        if not nodes:
            return None

        provenance = self.compute_path_provenance(nodes, relations)
        confidence = self.compute_path_confidence(nodes, relations)

        path = ReconstructionPath(
            id=f"rp_{source_id}_{target_id}",
            direction=direction,
            nodes=nodes,
            relations=relations,
            provenance=provenance,
            confidence=confidence,
            description=f"Path: {' → '.join(node_ids)}",
        )

        validation = self._validator.validate(nodes, relations, direction)

        return ReconstructionResult(
            path=path,
            validation=validation,
            discovered_paths=1,
        )

    def _build_chain_result(
        self,
        node_ids: list[str],
        direction: ChainDirection,
    ) -> ReconstructionPath:
        """Build ReconstructionPath from chain node IDs."""
        nodes = [n for n in self._graph._nodes.values() if n.id in node_ids]
        relations = []
        prev_id = None
        for nid in node_ids:
            if prev_id:
                for rel in self._graph.get_outgoing(prev_id):
                    if rel.target_id == nid:
                        relations.append(rel)
                        break
                else:
                    for rel in self._graph.get_incoming(prev_id):
                        if rel.source_id == nid:
                            relations.append(rel)
                            break
            prev_id = nid

        provenance = self.compute_path_provenance(nodes, relations)
        confidence = self.compute_path_confidence(nodes, relations)

        return ReconstructionPath(
            id=f"chain_{direction.value.lower()}_{'_'.join(node_ids)}",
            direction=direction,
            nodes=nodes,
            relations=relations,
            provenance=provenance,
            confidence=confidence,
            description=f"Chain ({direction.value}): {' → '.join(node_ids)}",
        )

    def _trace_backward(self, anchor_id: str, max_depth: int) -> list[str]:
        """Trace backward from anchor (collect all reachable predecessors)."""
        visited: set[str] = {anchor_id}
        result: list[str] = [anchor_id]
        queue = [(anchor_id, 0)]

        for _ in range(max_depth):
            next_queue = []
            for current_id, depth in queue:
                # Incoming relations (predecessors)
                for rel in self._graph.get_incoming(current_id):
                    nid = rel.source_id
                    if nid not in visited:
                        visited.add(nid)
                        result.append(nid)
                        next_queue.append((nid, depth + 1))
                # Also check outgoing that point backward (AFTER, FOLLOWS)
                for rel in self._graph.get_outgoing(current_id):
                    if rel.relation_type in (
                        TemporalRelationType.AFTER,
                        TemporalRelationType.FOLLOWS,
                        TemporalRelationType.TRANSFORMS_INTO,
                    ):
                        nid = rel.target_id
                        if nid not in visited:
                            visited.add(nid)
                            result.append(nid)
                            next_queue.append((nid, depth + 1))
            queue = next_queue
            if not queue:
                break

        return result

    def _trace_forward(self, anchor_id: str, max_depth: int) -> list[str]:
        """Trace forward from anchor (collect all reachable successors)."""
        visited: set[str] = {anchor_id}
        result: list[str] = [anchor_id]
        queue = [(anchor_id, 0)]

        for _ in range(max_depth):
            next_queue = []
            for current_id, depth in queue:
                # Outgoing relations (successors)
                for rel in self._graph.get_outgoing(current_id):
                    nid = rel.target_id
                    if nid not in visited:
                        visited.add(nid)
                        result.append(nid)
                        next_queue.append((nid, depth + 1))
                # Also check incoming that point forward (BEFORE, PRECEDES)
                for rel in self._graph.get_incoming(current_id):
                    if rel.relation_type in (
                        TemporalRelationType.BEFORE,
                        TemporalRelationType.PRECEDES,
                        TemporalRelationType.DEVELOPS_FROM,
                    ):
                        nid = rel.source_id
                        if nid not in visited:
                            visited.add(nid)
                            result.append(nid)
                            next_queue.append((nid, depth + 1))
            queue = next_queue
            if not queue:
                break

        return result

    # ── Factory: from WorldModel ─────────────────────────────────────

    @classmethod
    def from_world_model(cls, world_model) -> "TemporalReconstructionEngine":
        """Create engine populated with WorldModel data.

        M4: мост между WorldModel и TemporalReconstructionEngine.
        M8.1: добавляет temporal_today (методологический anchor),
              enriches temporal_arkaim_era provenance из ArkaimAnchor,
              убирает orphan temporal_arkaim_anchor.
        НЕ создаёт relation PRESENT→ARKAIM — это computed path.
        """
        from narrative_engine.temporal.arkaim_anchor import ArkaimAnchor
        from narrative_engine.temporal.node import TemporalNode
        from narrative_engine.source_levels import ProvenanceCategory, ProvenanceTag, SourceLevel

        engine = cls()

        # Collect ArkaimAnchor provenance for enrichment
        arkaim_anchor = ArkaimAnchor.from_existing_data()
        arkaim_provenance = arkaim_anchor.provenance  # [AUTHOR_CANON, EXTERNAL_SOURCE]

        # Add all epochs as temporal nodes
        for epoch in world_model.get_epochs():
            node_data = world_model.get_temporal_node(epoch.id)
            if node_data:
                node = TemporalNode.from_dict(node_data)

                # M8.1: enrich arkaim_era provenance from ArkaimAnchor
                if epoch.id == "arkaim_era" and arkaim_provenance:
                    existing_cats = {p.category for p in node.provenance}
                    for tag in arkaim_provenance:
                        if tag.category not in existing_cats:
                            node.provenance.append(tag)
                    node.confidence = 0.85  # combined confidence

                engine.add_node(node)

        # Add temporal relations between consecutive epochs
        epochs = world_model.get_epochs()
        for i in range(len(epochs) - 1):
            src = f"temporal_{epochs[i].id}"
            tgt = f"temporal_{epochs[i+1].id}"
            engine.add_relation(TemporalRelation.precedes(src, tgt))

        # M8.1: Add temporal_today as methodological anchor (NO relations)
        today_node = TemporalNode.present_anchor()
        engine.add_node(today_node)

        # M8.1: Remove orphan temporal_arkaim_anchor (was created by old ArkaimAnchor.add_node)
        # It has no relations and duplicates temporal_arkaim_era
        if engine._graph.get_node("temporal_arkaim_anchor"):
            engine.remove_node("temporal_arkaim_anchor")
            log.info("removed_orphan_arkaim_anchor id=temporal_arkaim_anchor")

        log.info(
            "reconstruction_engine_loaded_from_world_model epochs=%d nodes=%d",
            len(epochs),
            len(engine.get_all_nodes()),
        )
        return engine

    # ── Persistence ──────────────────────────────────────────────────

    def save_reconstruction(
        self,
        result: ReconstructionResult,
        output_path: Optional[Path] = None,
    ) -> Path:
        """Save reconstruction result to JSON."""
        path = output_path or (
            self._reconstruction_dir / f"reconstruction_{datetime.now().isoformat()}.json"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        data = result.to_dict()
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info("reconstruction_saved path=%s", path)
        return path

    def load_reconstruction(self, path: Path) -> Optional[ReconstructionResult]:
        """Load reconstruction result from JSON."""
        if not path.exists():
            log.warning("reconstruction_not_found path=%s", path)
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        from narrative_engine.temporal.reconstruction_path import ReconstructionPath as RP
        from narrative_engine.temporal.node import TemporalNode as TN
        from narrative_engine.temporal.relation import TemporalRelation as TR
        from narrative_engine.temporal.path_validator import PathValidationResult as PVR
        from narrative_engine.source_levels import ProvenanceTag as PT

        nodes = [TN.from_dict(n) for n in data.get("path", {}).get("nodes", [])]
        relations = [TR.from_dict(r) for r in data.get("path", {}).get("relations", [])]
        provenance = [PT.from_dict(p) for p in data.get("path", {}).get("provenance", [])]

        # Rebuild path
        rp_data = data.get("path", {})
        rp = RP(
            id=rp_data.get("id", ""),
            direction=ChainDirection(rp_data.get("direction", "BACKWARD")),
            nodes=nodes,
            relations=relations,
            provenance=provenance,
            confidence=data.get("path", {}).get("confidence", 0.5),
            description=rp_data.get("description", ""),
        )

        val_data = data.get("validation", {})
        validation = PVR(
            is_valid=val_data.get("is_valid", True),
            violations=[],  # reconstructed
            warnings=[],
            score=val_data.get("score", 1.0),
        )

        return ReconstructionResult(
            path=rp,
            validation=validation,
            gap_handled=data.get("gap_handled", False),
            gap_id=data.get("gap_id"),
            discovered_paths=data.get("discovered_paths", 0),
            notes=data.get("notes", ""),
        )

    # ── Stats ────────────────────────────────────────────────────────

    def stats(self) -> dict:
        return {
            **self._graph.stats(),
            "reconstruction_dir": str(self._reconstruction_dir),
        }
