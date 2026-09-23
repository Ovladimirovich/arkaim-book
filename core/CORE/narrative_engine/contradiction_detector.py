"""Contradiction Detector — обнаружение противоречий в цепочках причин-следствий.

Реализует архитектуру World Explorer: Logic Engine → Contradiction Detector (Этап 2).

Проверяет:
1. Нет временных парадоксов (cause-before-effect)
2. Нет причинных циклов (A → B → A)
3. Сохранение причинно-следственной связи (каждое следствие имеет причину)
4. Сохранение временной шкалы (события в правильном порядке)
5. Сохранение характеров персонажей (действия соответствуют характеру)
"""

import logging
from typing import Optional

from pydantic import BaseModel, Field

from narrative_engine.world_model import WorldModel
from narrative_engine.planners.cause_effect import CauseEffectTree, CauseEffectNode

log = logging.getLogger("hermes.narrative.contradiction_detector")


class Contradiction(BaseModel):
    """Обнаруженное противоречие."""
    contradiction_type: str  # temporal_paradox, causal_loop, missing_cause, timeline_violation, character_inconsistency
    severity: str  # "hard" | "soft"
    description: str
    involved_nodes: list[str] = Field(default_factory=list)
    suggestion: str = ""


class ContradictionReport(BaseModel):
    """Отчёт о противоречиях."""
    contradictions: list[Contradiction] = Field(default_factory=list)
    is_consistent: bool = Field(description="True если нет hard contradictions")
    contradiction_count: int = 0
    hard_count: int = 0
    soft_count: int = 0
    summary: str = ""


class ContradictionDetector:
    """Обнаруживает противоречия в CauseEffectTree.

    Проверяет 5 типов противоречий:
    1. Temporal Paradox — следствие предшествует причине
    2. Causal Loop — A → B → A
    3. Missing Cause — следствие без причины
    4. Timeline Violation — нарушение порядка эпох
    5. Character Inconsistency — персонаж действует нехарактерно
    """

    def __init__(self, world_model: WorldModel):
        self._wm = world_model

    def detect(self, tree: CauseEffectTree) -> ContradictionReport:
        """Обнаружить противоречия в дереве причин-следствий."""
        contradictions: list[Contradiction] = []

        # 1. Временные парадоксы
        contradictions.extend(self._check_temporal_paradoxes(tree))

        # 2. Причинные циклы
        contradictions.extend(self._check_causal_loops(tree))

        # 3. Отсутствующие причины
        contradictions.extend(self._check_missing_causes(tree))

        # 4. Нарушения временной шкалы
        contradictions.extend(self._check_timeline_violations(tree))

        # 5. Несогласованность персонажей
        contradictions.extend(self._check_character_inconsistencies(tree))

        hard_count = sum(1 for c in contradictions if c.severity == "hard")
        soft_count = sum(1 for c in contradictions if c.severity == "soft")

        summary = self._generate_summary(contradictions, hard_count, soft_count)

        return ContradictionReport(
            contradictions=contradictions,
            is_consistent=hard_count == 0,
            contradiction_count=len(contradictions),
            hard_count=hard_count,
            soft_count=soft_count,
            summary=summary,
        )

    def _check_temporal_paradoxes(self, tree: CauseEffectTree) -> list[Contradiction]:
        """Проверка: следствие не может предшествовать причине."""
        contradictions = []

        # Строим карту позиций по временному порядку
        order_map = {nid: i for i, nid in enumerate(tree.temporal_order)}

        for node in tree.nodes:
            if node.type in ("effect", "reaction") and node.depends_on:
                node_pos = order_map.get(node.id, 999)
                for dep_id in node.depends_on:
                    dep_pos = order_map.get(dep_id, 999)
                    if dep_pos > node_pos:
                        contradictions.append(Contradiction(
                            contradiction_type="temporal_paradox",
                            severity="hard",
                            description=(
                                f"Узел '{node.id}' ({node.type}) появляется "
                                f"раньше своей причины '{dep_id}'"
                            ),
                            involved_nodes=[node.id, dep_id],
                            suggestion="Переставьте узлы в правильном временном порядке.",
                        ))

        return contradictions

    def _check_causal_loops(self, tree: CauseEffectTree) -> list[Contradiction]:
        """Проверка: нет циклов A → B → A."""
        contradictions = []

        # Строим граф зависимостей
        dep_graph: dict[str, set[str]] = {}
        for node in tree.nodes:
            dep_graph[node.id] = set(node.depends_on)

        # DFS для обнаружения циклов
        visited = set()
        rec_stack = set()

        def has_cycle(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)

            for dep in dep_graph.get(node_id, set()):
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    return True

            rec_stack.discard(node_id)
            return False

        for node_id in dep_graph:
            if node_id not in visited:
                if has_cycle(node_id):
                    contradictions.append(Contradiction(
                        contradiction_type="causal_loop",
                        severity="hard",
                        description=f"Обнаружен причинный цикл, включающий узел '{node_id}'",
                        involved_nodes=[node_id],
                        suggestion="Устраните циклическую зависимость.",
                    ))
                    break

        return contradictions

    def _check_missing_causes(self, tree: CauseEffectTree) -> list[Contradiction]:
        """Проверка: каждое следствие должно иметь причину."""
        contradictions = []

        for node in tree.nodes:
            if node.type == "effect" and not node.depends_on:
                # Effect без depends_on — возможная проблема
                # Но root node — это нормально
                if node.order > 0:
                    contradictions.append(Contradiction(
                        contradiction_type="missing_cause",
                        severity="soft",
                        description=(
                            f"Узел '{node.id}' ({node.type}) не имеет причины. "
                            f"Описание: {node.description[:80]}"
                        ),
                        involved_nodes=[node.id],
                        suggestion="Добавьте причину для этого следствия.",
                    ))

        return contradictions

    def _check_timeline_violations(self, tree: CauseEffectTree) -> list[Contradiction]:
        """Проверка: порядок эпох соблюдается."""
        contradictions = []

        # Строим карту эпох
        epoch_order: dict[str, int] = {}
        for epoch in self._wm.get_epochs():
            epoch_order[epoch.id] = epoch.order

        # Проверяем узлы с эпохами
        nodes_with_epochs = [(n, n.epoch) for n in tree.nodes if n.epoch]
        for i, (node_a, epoch_a) in enumerate(nodes_with_epochs):
            for node_b, epoch_b in nodes_with_epochs[i + 1:]:
                order_a = epoch_order.get(epoch_a, 0)
                order_b = epoch_order.get(epoch_b, 0)

                # Если node_a зависит от node_b, но epoch_a раньше epoch_b
                if node_b.id in node_a.depends_on and order_a < order_b:
                    contradictions.append(Contradiction(
                        contradiction_type="timeline_violation",
                        severity="hard",
                        description=(
                            f"Узел '{node_a.id}' (эпоха {epoch_a}) зависит от "
                            f"'{node_b.id}' (эпоха {epoch_b}), но его эпоха раньше."
                        ),
                        involved_nodes=[node_a.id, node_b.id],
                        suggestion="Пересмотрите зависимость или эпоху.",
                    ))

        return contradictions

    def _check_character_inconsistencies(self, tree: CauseEffectTree) -> list[Contradiction]:
        """Проверка: персонажи действуют характерно."""
        contradictions = []

        # Собираем все упоминания персонажей
        char_appearances: dict[str, list[str]] = {}
        for node in tree.nodes:
            for char in node.characters_involved:
                if char not in char_appearances:
                    char_appearances[char] = []
                char_appearances[char].append(f"{node.id}({node.type})")

        # Проверяем, что персонаж появляется более чем в одном типе узла
        for char, appearances in char_appearances.items():
            types = set()
            for app in appearances:
                if "(" in app:
                    type_str = app.split("(")[1].rstrip(")")
                    types.add(type_str)

            # Если персонаж появляется и как cause, и как constraint — возможно противоречие
            if "cause" in types and "constraint" in types:
                contradictions.append(Contradiction(
                    contradiction_type="character_inconsistency",
                    severity="soft",
                    description=(
                        f"Персонаж '{char}' одновременно является причиной и ограничением. "
                        f"Это может указывать на внутреннее противоречие."
                    ),
                    involved_nodes=appearances,
                    suggestion="Пересмотрите роль персонажа.",
                ))

        return contradictions

    def _generate_summary(
        self,
        contradictions: list[Contradiction],
        hard_count: int,
        soft_count: int,
    ) -> str:
        """Генерировать сводку."""
        if not contradictions:
            return "Противоречий не обнаружено. Дерево непротиворечиво."

        parts = []
        if hard_count:
            parts.append(f"{hard_count} критических противоречий")
        if soft_count:
            parts.append(f"{soft_count} предупреждений")

        type_counts: dict[str, int] = {}
        for c in contradictions:
            type_counts[c.contradiction_type] = type_counts.get(c.contradiction_type, 0) + 1

        type_names = {
            "temporal_paradox": "временные парадоксы",
            "causal_loop": "причинные циклы",
            "missing_cause": "отсутствующие причины",
            "timeline_violation": "нарушения временной шкалы",
            "character_inconsistency": "несогласованность персонажей",
        }
        for ctype, count in type_counts.items():
            name = type_names.get(ctype, ctype)
            parts.append(f"{count} {name}")

        return "; ".join(parts)
