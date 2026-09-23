"""Path validation for temporal reconstruction.

M3: Validates candidate paths for consistency.
Does NOT modify paths — only checks and flags issues.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from narrative_engine.source_levels import ProvenanceCategory
from narrative_engine.temporal.node import TemporalNode
from narrative_engine.temporal.relation import TemporalRelation, TemporalRelationType
from narrative_engine.temporal.chain import ChainDirection


@dataclass
class PathViolation:
    """Нарушение консистентности пути."""
    rule_id: str
    severity: str  # "hard" | "soft" | "info"
    description: str
    involved_nodes: list[str] = field(default_factory=list)
    involved_relations: list[str] = field(default_factory=list)


@dataclass
class PathValidationResult:
    """Результат валидации пути."""
    is_valid: bool
    violations: list[PathViolation] = field(default_factory=list)
    warnings: list[PathViolation] = field(default_factory=list)
    score: float = 1.0

    def add_violation(self, v: PathViolation) -> None:
        if v.severity == "hard":
            self.violations.append(v)
        else:
            self.warnings.append(v)
        self.score = max(0.0, self.score - (0.1 if v.severity == "soft" else 0.2))

    @property
    def is_hard_valid(self) -> bool:
        return len(self.violations) == 0

    def summary(self) -> str:
        if self.is_hard_valid:
            return f"Valid (score: {self.score:.2f}, warnings: {len(self.warnings)})"
        return f"Invalid (score: {self.score:.2f}, violations: {len(self.violations)}, warnings: {len(self.warnings)})"


class PathValidator:
    """Валидатор путей реконструкции.

    Проверяет:
    1. Node consistency — все узлы существуют
    2. Relation consistency — связи действительны
    3. Direction consistency — направление не противоречит
    4. Temporal consistency — нет противоречивых temporal relations
    5. Provenance safety — provenance не понижается
    """

    # Rules
    RULE_NODE_MISSING = "node_missing"
    RULE_RELATION_MISSING = "relation_missing"
    RULE_DIRECTION_CONFLICT = "direction_conflict"
    RULE_TEMPORAL_CONFLICT = "temporal_conflict"
    RULE_PROVENANCE_DOWNGRADE = "provenance_downgrade"
    RULE_SELF_LOOP = "self_loop"
    RULE_CYCLE = "cycle"

    def validate(
        self,
        nodes: list[TemporalNode],
        relations: list[TemporalRelation],
        direction: ChainDirection,
        node_store: Optional[dict[str, TemporalNode]] = None,
        rel_store: Optional[dict[str, TemporalRelation]] = None,
    ) -> PathValidationResult:
        """Validate a reconstruction path."""
        result = PathValidationResult(is_valid=True)

        # 1. Node consistency
        store = node_store or {n.id: n for n in nodes}
        for node in nodes:
            if node.id not in store:
                result.add_violation(PathViolation(
                    rule_id=self.RULE_NODE_MISSING,
                    severity="hard",
                    description=f"Node '{node.id}' not found in store",
                    involved_nodes=[node.id],
                ))

        # 2. Relation consistency
        rel_map = {r.id: r for r in relations}
        for rel in relations:
            if rel.source_id not in store:
                result.add_violation(PathViolation(
                    rule_id=self.RULE_RELATION_MISSING,
                    severity="hard",
                    description=f"Relation '{rel.id}' source '{rel.source_id}' not in path",
                    involved_nodes=[rel.source_id],
                    involved_relations=[rel.id],
                ))
            if rel.target_id not in store:
                result.add_violation(PathViolation(
                    rule_id=self.RULE_RELATION_MISSING,
                    severity="hard",
                    description=f"Relation '{rel.id}' target '{rel.target_id}' not in path",
                    involved_nodes=[rel.target_id],
                    involved_relations=[rel.id],
                ))

        # 3. Direction consistency
        if len(nodes) >= 2:
            for i in range(len(nodes) - 1):
                src = nodes[i]
                dst = nodes[i + 1]
                matching_rel = self._find_relation(relations, src.id, dst.id)
                if matching_rel:
                    if direction == ChainDirection.BACKWARD:
                        # BACKWARD: we expect PRECEDES (A before B means A is earlier)
                        if matching_rel.relation_type in (
                            TemporalRelationType.AFTER,
                            TemporalRelationType.TRANSFORMS_INTO,
                        ):
                            result.add_violation(PathViolation(
                                rule_id=self.RULE_DIRECTION_CONFLICT,
                                severity="soft",
                                description=f"Relation '{matching_rel.id}' direction conflicts with BACKWARD traversal",
                                involved_nodes=[src.id, dst.id],
                                involved_relations=[matching_rel.id],
                            ))
                    elif direction == ChainDirection.FORWARD:
                        if matching_rel.relation_type in (
                            TemporalRelationType.BEFORE,
                            TemporalRelationType.DEVELOPS_FROM,
                        ):
                            result.add_violation(PathViolation(
                                rule_id=self.RULE_DIRECTION_CONFLICT,
                                severity="soft",
                                description=f"Relation '{matching_rel.id}' direction conflicts with FORWARD traversal",
                                involved_nodes=[src.id, dst.id],
                                involved_relations=[matching_rel.id],
                            ))

        # 4. Temporal consistency — check for contradictory relations
        for i in range(len(nodes) - 1):
            for j in range(i + 1, len(nodes) - 1):
                src = nodes[i]
                mid = nodes[j]
                dst = nodes[i + 1]
                # Check if mid contradicts the direct src→dst path
                mid_rel = self._find_relation(relations, src.id, mid.id)
                dst_rel = self._find_relation(relations, mid.id, dst.id)
                if mid_rel and dst_rel:
                    if (mid_rel.relation_type == TemporalRelationType.BEFORE
                            and dst_rel.relation_type == TemporalRelationType.AFTER):
                        result.add_violation(PathViolation(
                            rule_id=self.RULE_TEMPORAL_CONFLICT,
                            severity="hard",
                            description=f"Temporal conflict: {src.id} BEFORE {mid.id} AND {mid.id} AFTER {dst.id}",
                            involved_nodes=[src.id, mid.id, dst.id],
                        ))

        # 5. Provenance safety — check for downgrade
        for rel in relations:
            for tag in rel.provenance:
                if tag.category == ProvenanceCategory.AUTHOR_CANON:
                    # Can't downgrade canon
                    pass  # Canon is safe, it stays canon
                elif tag.category == ProvenanceCategory.HYPOTHESIS:
                    # Hypothesis can stay hypothesis, but warn if mixed with canon
                    for other_rel in relations:
                        if other_rel is not rel:
                            for other_tag in other_rel.provenance:
                                if other_tag.category == ProvenanceCategory.AUTHOR_CANON:
                                    result.add_violation(PathViolation(
                                        rule_id=self.RULE_PROVENANCE_DOWNGRADE,
                                        severity="soft",
                                        description=f"Path mixes HYPOTHESIS and AUTHOR_CANON — result cannot be FACT",
                                        involved_relations=[rel.id, other_rel.id],
                                    ))

        # 6. Self-loops
        for rel in relations:
            if rel.source_id == rel.target_id:
                result.add_violation(PathViolation(
                    rule_id=self.RULE_SELF_LOOP,
                    severity="soft",
                    description=f"Self-loop detected: {rel.source_id} → {rel.target_id}",
                    involved_nodes=[rel.source_id],
                    involved_relations=[rel.id],
                ))

        # 7. Cycles detection (simple check)
        if self._has_cycle(nodes, relations):
            result.add_violation(PathViolation(
                rule_id=self.RULE_CYCLE,
                severity="hard",
                description="Cycle detected in temporal path — invalid for linear reconstruction",
                involved_nodes=[n.id for n in nodes],
            ))

        result.is_valid = result.is_hard_valid
        return result

    def _find_relation(
        self, relations: list[TemporalRelation], source_id: str, target_id: str
    ) -> Optional[TemporalRelation]:
        for rel in relations:
            if (rel.source_id == source_id and rel.target_id == target_id) or \
               (rel.source_id == target_id and rel.target_id == source_id and rel.bidirectional):
                return rel
        return None

    def _has_cycle(self, nodes: list[TemporalNode], relations: list[TemporalRelation]) -> bool:
        """Simple cycle detection using DFS."""
        adj: dict[str, list[str]] = {}
        for rel in relations:
            if rel.source_id not in adj:
                adj[rel.source_id] = []
            adj[rel.source_id].append(rel.target_id)
            if rel.bidirectional:
                if rel.target_id not in adj:
                    adj[rel.target_id] = []
                adj[rel.target_id].append(rel.source_id)

        visited = set()
        rec_stack = set()

        def _dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            for neighbor in adj.get(node_id, []):
                if neighbor not in visited:
                    if _dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.discard(node_id)
            return False

        for node in nodes:
            if node.id not in visited:
                if _dfs(node.id):
                    return True
        return False
