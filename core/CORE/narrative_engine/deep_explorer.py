"""Deep Explorer — многоуровневое исследование мира.

Реализует архитектура World Explorer: Этап 11 — Глубокое исследование.

Расширяет существующую систему Exploration Core:
- Ветвление от ветвей (branch-from-branch)
- Каскадные гипотезы (cascading hypotheses)
- Многоуровневое исследование (multi-level exploration)
- Автоматическое обнаружение «свободных точек» мира
"""

import logging
from typing import Optional
from pydantic import BaseModel, Field

from narrative_engine.world_model import WorldModel
from narrative_engine.hypothesis_generator import (
    HypothesisGenerator, Hypothesis, HypothesisType,
)
from narrative_engine.scenario_modeler import ScenarioModeler, ScenarioTree
from narrative_engine.quality_evaluator import QualityEvaluator, QualityReport
from narrative_engine.branch_manager import BranchManager, BranchNode

log = logging.getLogger("hermes.narrative.deep_explorer")


class DeepExplorationRequest(BaseModel):
    """Запрос на глубокое исследование."""
    prompt: str
    epoch: Optional[str] = None
    parent_branch_id: Optional[str] = None  # Ветвь, от которой продолжаем
    max_depth: int = Field(default=3, ge=1, le=5)
    branches_per_level: int = Field(default=3, ge=1, le=5)
    explore_from_branch: bool = False  # Продолжить от конкретной ветви


class DeepExplorationNode(BaseModel):
    """Узел дерева глубокого исследования."""
    id: str
    hypothesis: Hypothesis
    scenario: Optional[ScenarioTree] = None
    quality_report: Optional[QualityReport] = None
    children: list[str] = Field(default_factory=list)
    parent_id: str = ""
    depth: int = 0
    quality_score: float = 0.0


class DeepExplorationTree(BaseModel):
    """Дерево глубокого исследования."""
    root_node: Optional[DeepExplorationNode] = None
    nodes: dict[str, DeepExplorationNode] = Field(default_factory=dict)
    total_nodes: int = 0
    max_depth_reached: int = 0
    summary: str = ""


class DeepExplorer:
    """Многоуровневый исследователь мира.

    Расширяет Exploration Core:
    - Ветвление от ветвей (branch-from-branch)
    - Каскадные гипотезы (cascading hypotheses)
    - Автоматическое обнаружение «свободных точек» мира
    """

    def __init__(self, world_model: WorldModel):
        self._wm = world_model
        self._hypothesis_gen = HypothesisGenerator(world_model)
        self._scenario_modeler = ScenarioModeler(world_model)
        self._quality_evaluator = QualityEvaluator(world_model)
        self._branch_manager = BranchManager(world_model)

    def explore_deep(self, request: DeepExplorationRequest) -> DeepExplorationTree:
        """Многоуровневое исследование мира."""
        # Генерируем базовые гипотезы
        if request.epoch:
            base_hypotheses = self._hypothesis_gen.generate_for_epoch(
                request.epoch, limit=request.branches_per_level
            )
        else:
            base_hypotheses = self._hypothesis_gen.generate_proactive(
                limit=request.branches_per_level
            )

        if not base_hypotheses:
            return DeepExplorationTree(summary="Гипотезы не сгенерированы")

        # Создаём корневой узел
        root_hyp = base_hypotheses[0]
        root_scenario = self._scenario_modeler.model_scenario(
            root_hyp, branch_count=request.branches_per_level
        )
        root_quality = self._quality_evaluator.evaluate_branches(
            root_scenario.branches
        )

        root_node = DeepExplorationNode(
            id="root",
            hypothesis=root_hyp,
            scenario=root_scenario,
            quality_report=root_quality[0] if root_quality else None,
            depth=0,
            quality_score=root_quality[0].overall_score if root_quality else 0.0,
        )

        tree = DeepExplorationTree(
            root_node=root_node,
            nodes={"root": root_node},
        )

        # Рекурсивно исследуем deeper levels
        if request.max_depth > 1:
            self._explore_deeper(
                tree=tree,
                parent_id="root",
                depth=1,
                max_depth=request.max_depth,
                branches_per_level=request.branches_per_level,
                epoch=request.epoch,
            )

        tree.total_nodes = len(tree.nodes)
        tree.max_depth_reached = max(n.depth for n in tree.nodes.values()) if tree.nodes else 0
        tree.summary = (
            f"Глубокое исследование: {tree.total_nodes} узлов, "
            f"максимальная глубина {tree.max_depth_reached}"
        )

        return tree

    def explore_from_branch(
        self,
        branch_id: str,
        tree: DeepExplorationTree,
        branches_per_level: int = 3,
    ) -> DeepExplorationTree:
        """Продолжить исследование от конкретной ветви."""
        if branch_id not in tree.nodes:
            log.warning("branch_not_found branch_id=%s", branch_id)
            return tree

        parent_node = tree.nodes[branch_id]
        parent_depth = parent_node.depth

        # Генерируем производные гипотезы от родительской
        derivatives = self._hypothesis_gen.generate_for_hypothesis(
            parent_node.hypothesis, limit=branches_per_level
        )

        for i, hyp in enumerate(derivatives):
            node_id = f"{branch_id}_d{i}"
            scenario = self._scenario_modeler.model_scenario(
                hyp, branch_count=branches_per_level
            )
            quality = self._quality_evaluator.evaluate_branches(scenario.branches)

            child_node = DeepExplorationNode(
                id=node_id,
                hypothesis=hyp,
                scenario=scenario,
                quality_report=quality[0] if quality else None,
                parent_id=branch_id,
                depth=parent_depth + 1,
                quality_score=quality[0].overall_score if quality else 0.0,
            )

            tree.nodes[node_id] = child_node
            parent_node.children.append(node_id)

        tree.total_nodes = len(tree.nodes)
        tree.max_depth_reached = max(n.depth for n in tree.nodes.values())

        return tree

    def find_free_points(self, epoch_id: Optional[str] = None) -> list[dict]:
        """Обнаружить «свободные точки» мира — где есть потенциал для развития.

        Свободные точки:
        - События без последствий
        - Персонажи без завершённых арок
        - Локации без описания
        - Технологии без применения
        """
        free_points = []

        if epoch_id:
            # Персонажи без завершённых арок
            chars = self._wm.get_characters_alive(epoch_id)
            for char in chars:
                free_points.append({
                    "type": "character",
                    "id": char.character_name,
                    "title": f"Арка: {char.character_name}",
                    "description": f"Развитие пути {char.character_name} ({char.status})",
                    "potential": 0.7,
                })

            # События без последствий
            events = self._wm.get_events(epoch_id)
            for event in events[:5]:
                free_points.append({
                    "type": "event",
                    "id": event.id,
                    "title": f"Последствия: {event.title_ru}",
                    "description": f"Что произойдёт после '{event.title_ru}'?",
                    "potential": 0.6,
                })

            # Технологии без применения
            techs = self._wm.get_technologies(epoch_id)
            for tech in techs[:3]:
                free_points.append({
                    "type": "technology",
                    "id": tech.id,
                    "title": f"Применение: {tech.name_ru}",
                    "description": f"Как технология {tech.name_ru} может изменить мир?",
                    "potential": 0.5,
                })

        else:
            # Для всех эпох
            for epoch in self._wm.get_epochs()[:3]:
                chars = self._wm.get_characters_alive(epoch.id)
                if chars:
                    free_points.append({
                        "type": "epoch_character",
                        "id": f"{epoch.id}_chars",
                        "title": f"Персонажи {epoch.name_ru}",
                        "description": f"Арки {len(chars)} персонажей в {epoch.name_ru}",
                        "potential": 0.6,
                    })

        return free_points

    def _explore_deeper(
        self,
        tree: DeepExplorationTree,
        parent_id: str,
        depth: int,
        max_depth: int,
        branches_per_level: int,
        epoch: Optional[str],
    ):
        """Рекурсивно исследовать deeper levels."""
        if depth >= max_depth:
            return

        parent_node = tree.nodes.get(parent_id)
        if not parent_node or not parent_node.hypothesis:
            return

        # Генерируем производные гипотезы
        derivatives = self._hypothesis_gen.generate_for_hypothesis(
            parent_node.hypothesis, limit=branches_per_level
        )

        for i, hyp in enumerate(derivatives):
            node_id = f"{parent_id}_l{depth}_{i}"

            scenario = self._scenario_modeler.model_scenario(
                hyp, branch_count=min(branches_per_level, 2)  # Меньше ветвей на глубоких уровнях
            )
            quality = self._quality_evaluator.evaluate_branches(scenario.branches)

            child_node = DeepExplorationNode(
                id=node_id,
                hypothesis=hyp,
                scenario=scenario,
                quality_report=quality[0] if quality else None,
                parent_id=parent_id,
                depth=depth,
                quality_score=quality[0].overall_score if quality else 0.0,
            )

            tree.nodes[node_id] = child_node
            parent_node.children.append(node_id)

            # Рекурсия для следующего уровня
            if depth + 1 < max_depth and quality and quality[0].overall_score > 0.5:
                self._explore_deeper(
                    tree=tree,
                    parent_id=node_id,
                    depth=depth + 1,
                    max_depth=max_depth,
                    branches_per_level=max(1, branches_per_level - 1),  # Уменьшаем на глубоких уровнях
                    epoch=epoch,
                )

    def get_best_paths(
        self,
        tree: DeepExplorationTree,
        top_n: int = 3,
    ) -> list[list[str]]:
        """Найти лучшие пути в дереве (от корня к листьям)."""
        if not tree.root_node:
            return []

        paths = []
        self._find_paths(tree, "root", [], paths)

        # Сортируем по суммарному качеству
        paths_with_score = []
        for path in paths:
            total_score = sum(
                tree.nodes[nid].quality_score
                for nid in path
                if nid in tree.nodes
            )
            paths_with_score.append((total_score, path))

        paths_with_score.sort(key=lambda x: x[0], reverse=True)
        return [path for _, path in paths_with_score[:top_n]]

    def _find_paths(
        self,
        tree: DeepExplorationTree,
        node_id: str,
        current_path: list[str],
        all_paths: list[list[str]],
    ):
        """Найти все пути от узла до листьев."""
        node = tree.nodes.get(node_id)
        if not node:
            return

        current_path = current_path + [node_id]

        if not node.children:
            all_paths.append(current_path)
        else:
            for child_id in node.children:
                self._find_paths(tree, child_id, current_path, all_paths)
