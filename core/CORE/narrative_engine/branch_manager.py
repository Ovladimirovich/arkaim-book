"""Branch Manager — управление ветвями развития.

Реализует архитектуру World Explorer: Exploration Core → Branch Manager (Этап 3).

Управляет деревом ветвей:
- Хранит историю исследований
- Позволяет навигировать по ветвям
- Сохраняет оценки качества
- Позволяет продолжать исследование от любой ветви
"""

import json
import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from narrative_engine.world_model import WorldModel
from narrative_engine.hypothesis_generator import Hypothesis, HypothesisGraph
from narrative_engine.scenario_modeler import ScenarioTree, ScenarioBranch

log = logging.getLogger("hermes.narrative.branch_manager")


class BranchNode(BaseModel):
    """Узел ветви — одна точка в дереве исследований."""
    id: str
    parent_id: str = ""
    hypothesis_id: str = ""
    scenario_branch_id: str = ""
    title: str = ""
    title_ru: str = ""
    depth: int = 0
    quality_score: float = 0.5
    is_explored: bool = False
    children: list[str] = Field(default_factory=list)


class ExplorationTree(BaseModel):
    """Дерево исследований — полная история навигации."""
    root_id: str = ""
    nodes: dict[str, BranchNode] = Field(default_factory=dict)
    current_id: str = ""
    total_nodes: int = 0
    max_depth: int = 0
    summary: str = ""


class BranchManager:
    """Управляет деревом ветвей развития.

    Позволяет:
    - Начать исследование от корня
    - Продолжить от любой ветви
    - Оценить качество ветвей
    - Найти лучшую ветвь
    - Получить историю исследований
    """

    def __init__(self, world_model: WorldModel):
        self._wm = world_model
        self._tree = ExplorationTree()
        self._node_counter = 0

    def start_exploration(
        self,
        epoch_id: str,
        hypothesis_graph: Optional[HypothesisGraph] = None,
    ) -> ExplorationTree:
        """Начать исследование эпохи."""
        # Создаём корневой узел
        root = self._create_node(
            title=f"Исследование эпохи: {epoch_id}",
            title_ru=f"Исследование эпохи: {epoch_id}",
            depth=0,
        )
        self._tree.root_id = root.id
        self._tree.current_id = root.id
        self._tree.nodes[root.id] = root

        # Если есть граф гипотез, добавляем узлы
        if hypothesis_graph:
            for hyp in hypothesis_graph.hypotheses[:10]:
                child = self._create_node(
                    title=hyp.title,
                    title_ru=hyp.title_ru,
                    parent_id=root.id,
                    depth=1,
                    hypothesis_id=hyp.id,
                )
                self._tree.nodes[root.id].children.append(child.id)
                self._tree.nodes[child.id] = child

        self._update_tree_stats()
        return self._tree

    def explore_branch(
        self,
        node_id: str,
        scenario_branch: Optional[ScenarioBranch] = None,
    ) -> ExplorationTree:
        """Продолжить исследование от конкретной ветви."""
        if node_id not in self._tree.nodes:
            log.warning("node_not_found node_id=%s", node_id)
            return self._tree

        parent = self._tree.nodes[node_id]

        # Создаём дочерний узел
        if scenario_branch:
            child = self._create_node(
                title=scenario_branch.title,
                title_ru=scenario_branch.title_ru,
                parent_id=node_id,
                depth=parent.depth + 1,
                scenario_branch_id=scenario_branch.id,
                quality_score=scenario_branch.quality_score,
            )
        else:
            child = self._create_node(
                title=f"Продолжение: {parent.title}",
                title_ru=f"Продолжение: {parent.title_ru}",
                parent_id=node_id,
                depth=parent.depth + 1,
            )

        parent.children.append(child.id)
        parent.is_explored = True
        self._tree.nodes[child.id] = child
        self._tree.current_id = child.id

        self._update_tree_stats()
        return self._tree

    def get_current_branch(self) -> Optional[BranchNode]:
        """Получить текущую ветвь."""
        if self._tree.current_id:
            return self._tree.nodes.get(self._tree.current_id)
        return None

    def go_to_branch(self, node_id: str) -> bool:
        """Перейти к конкретной ветви."""
        if node_id in self._tree.nodes:
            self._tree.current_id = node_id
            return True
        return False

    def go_up(self) -> bool:
        """Перейти к родительской ветви."""
        current = self.get_current_branch()
        if current and current.parent_id:
            self._tree.current_id = current.parent_id
            return True
        return False

    def get_best_branch(self) -> Optional[BranchNode]:
        """Найти ветвь с наивысшим качеством."""
        if not self._tree.nodes:
            return None

        return max(self._tree.nodes.values(), key=lambda n: n.quality_score)

    def get_branches_by_depth(self, depth: int) -> list[BranchNode]:
        """Получить все ветви на определённой глубине."""
        return [n for n in self._tree.nodes.values() if n.depth == depth]

    def get_explored_count(self) -> int:
        """Количество исследованных ветвей."""
        return sum(1 for n in self._tree.nodes.values() if n.is_explored)

    def get_unexplored_count(self) -> int:
        """Количество неисследованных ветвей."""
        return sum(1 for n in self._tree.nodes.values() if not n.is_explored)

    def get_path_to_root(self, node_id: str) -> list[str]:
        """Получить путь от узла до корня."""
        path = []
        current_id = node_id

        while current_id:
            node = self._tree.nodes.get(current_id)
            if node:
                path.append(node.id)
                current_id = node.parent_id
            else:
                break

        return list(reversed(path))

    def get_subtree(self, node_id: str) -> list[BranchNode]:
        """Получить поддерево от узла."""
        result = []

        def collect(nid: str):
            node = self._tree.nodes.get(nid)
            if node:
                result.append(node)
                for child_id in node.children:
                    collect(child_id)

        collect(node_id)
        return result

    def to_dict(self) -> dict:
        """Экспорт дерева в словарь."""
        return {
            "root_id": self._tree.root_id,
            "current_id": self._tree.current_id,
            "nodes": {
                nid: {
                    "id": n.id,
                    "parent_id": n.parent_id,
                    "title": n.title,
                    "depth": n.depth,
                    "quality_score": n.quality_score,
                    "is_explored": n.is_explored,
                    "children": n.children,
                }
                for nid, n in self._tree.nodes.items()
            },
            "total_nodes": self._tree.total_nodes,
            "max_depth": self._tree.max_depth,
        }

    def save(self, path: str):
        """Сохранить дерево в файл."""
        data = self.to_dict()
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self, path: str):
        """Загрузить дерево из файла."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self._tree.root_id = data.get("root_id", "")
        self._tree.current_id = data.get("current_id", "")
        self._tree.total_nodes = data.get("total_nodes", 0)
        self._tree.max_depth = data.get("max_depth", 0)

        for nid, ndata in data.get("nodes", {}).items():
            self._tree.nodes[nid] = BranchNode(**ndata)

    def _create_node(
        self,
        title: str,
        title_ru: str,
        parent_id: str = "",
        depth: int = 0,
        hypothesis_id: str = "",
        scenario_branch_id: str = "",
        quality_score: float = 0.5,
    ) -> BranchNode:
        """Создать узел с уникальным ID."""
        self._node_counter += 1
        node_id = f"branch_{self._node_counter:04d}"

        return BranchNode(
            id=node_id,
            parent_id=parent_id,
            hypothesis_id=hypothesis_id,
            scenario_branch_id=scenario_branch_id,
            title=title,
            title_ru=title_ru,
            depth=depth,
            quality_score=quality_score,
        )

    def _update_tree_stats(self):
        """Обновить статистику дерева."""
        self._tree.total_nodes = len(self._tree.nodes)
        if self._tree.nodes:
            self._tree.max_depth = max(n.depth for n in self._tree.nodes.values())

        explored = self.get_explored_count()
        total = self._tree.total_nodes
        self._tree.summary = (
            f"Дерево: {total} узлов, "
            f"глубина {self._tree.max_depth}, "
            f"исследовано {explored}/{total}"
        )
