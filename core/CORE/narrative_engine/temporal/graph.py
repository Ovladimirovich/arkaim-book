"""TemporalGraph — обёртка над TemporalNode + TemporalRelation для traversal.

M3: BFS/DFS traversal для поиска путей между temporal nodes.
Заимствует паттерн из RelationGraph.find_path() (BFS) и get_neighbors() (DFS).
"""

from __future__ import annotations

from collections import deque
from typing import Optional

from narrative_engine.temporal.node import TemporalNode
from narrative_engine.temporal.relation import TemporalRelation, TemporalRelationType
from narrative_engine.temporal.chain import TemporalChain, ChainDirection


class TemporalGraph:
    """Направленный граф для traversal temporal data.

    Минимальный API:
      - add_node(node)
      - add_relation(rel)
      - get_node(node_id) → Optional[TemporalNode]
      - get_outgoing(node_id) → list[TemporalRelation]
      - get_incoming(node_id) → list[TemporalRelation]
      - bfs_path(source_id, target_id, max_depth) → Optional[list[str]]
      - all_paths(source_id, target_id, max_depth) → list[list[str]]
    """

    def __init__(self):
        self._nodes: dict[str, TemporalNode] = {}
        self._outgoing: dict[str, list[TemporalRelation]] = {}
        self._incoming: dict[str, list[TemporalRelation]] = {}

    def add_node(self, node: TemporalNode) -> None:
        self._nodes[node.id] = node

    def add_relation(self, rel: TemporalRelation) -> None:
        # Outgoing
        if rel.source_id not in self._outgoing:
            self._outgoing[rel.source_id] = []
        self._outgoing[rel.source_id].append(rel)

        # Incoming
        if rel.target_id not in self._incoming:
            self._incoming[rel.target_id] = []
        self._incoming[rel.target_id].append(rel)

        # Bidirectional
        if rel.bidirectional:
            if rel.target_id not in self._outgoing:
                self._outgoing[rel.target_id] = []
            self._outgoing[rel.target_id].append(rel)
            if rel.source_id not in self._incoming:
                self._incoming[rel.source_id] = []
            self._incoming[rel.source_id].append(rel)

    def get_node(self, node_id: str) -> Optional[TemporalNode]:
        return self._nodes.get(node_id)

    def get_outgoing(self, node_id: str) -> list[TemporalRelation]:
        return self._outgoing.get(node_id, [])

    def get_incoming(self, node_id: str) -> list[TemporalRelation]:
        return self._incoming.get(node_id, [])

    def get_neighbors(self, node_id: str, max_depth: int = 3) -> dict[str, list[TemporalRelation]]:
        """DFS neighbors (pattern from RelationGraph.get_neighbors)."""
        neighbors: dict[str, list[TemporalRelation]] = {}
        visited: set[str] = set()

        def _dfs(current_id: str, depth: int):
            if depth > max_depth or current_id in visited:
                return
            visited.add(current_id)
            for rel in self._outgoing.get(current_id, []):
                nid = rel.target_id
                if nid not in neighbors:
                    neighbors[nid] = []
                neighbors[nid].append(rel)
                _dfs(nid, depth + 1)
            for rel in self._incoming.get(current_id, []):
                nid = rel.source_id
                if nid not in neighbors:
                    neighbors[nid] = []
                neighbors[nid].append(rel)
                _dfs(nid, depth + 1)

        _dfs(node_id, 1)
        return neighbors

    def bfs_path(self, source_id: str, target_id: str, max_depth: int = 10) -> Optional[list[str]]:
        """BFS path finding (pattern from RelationGraph.find_path).
        Returns list of node IDs forming the path, or None.
        """
        if source_id == target_id:
            return [source_id]

        queue = deque([(source_id, [source_id])])
        visited = {source_id}

        for _ in range(max_depth):
            next_queue = deque()
            while queue:
                current_id, path = queue.popleft()
                # Outgoing
                for rel in self._outgoing.get(current_id, []):
                    nid = rel.target_id
                    if nid == target_id:
                        return path + [nid]
                    if nid not in visited:
                        visited.add(nid)
                        next_queue.append((nid, path + [nid]))
                # Incoming (bidirectional traversal)
                for rel in self._incoming.get(current_id, []):
                    nid = rel.source_id
                    if nid == target_id:
                        return path + [nid]
                    if nid not in visited:
                        visited.add(nid)
                        next_queue.append((nid, path + [nid]))
            queue = next_queue

        return None

    def all_paths(self, source_id: str, target_id: str, max_depth: int = 10) -> list[list[str]]:
        """Find ALL paths between source and target (BFS, no early return)."""
        if source_id == target_id:
            return [[source_id]]

        results: list[list[str]] = []
        queue = deque([(source_id, [source_id])])
        visited_at_depth: dict[str, int] = {source_id: 0}

        for _ in range(max_depth):
            next_queue = deque()
            while queue:
                current_id, path = queue.popleft()
                for rel in self._outgoing.get(current_id, []):
                    nid = rel.target_id
                    if nid == target_id:
                        results.append(path + [nid])
                    elif nid not in visited_at_depth or visited_at_depth[nid] > len(path):
                        visited_at_depth[nid] = len(path)
                        next_queue.append((nid, path + [nid]))
                for rel in self._incoming.get(current_id, []):
                    nid = rel.source_id
                    if nid == target_id:
                        results.append(path + [nid])
                    elif nid not in visited_at_depth or visited_at_depth[nid] > len(path):
                        visited_at_depth[nid] = len(path)
                        next_queue.append((nid, path + [nid]))
            queue = next_queue
            if not queue:
                break

        return results

    def node_ids(self) -> list[str]:
        return list(self._nodes.keys())

    def relation_count(self) -> int:
        return sum(len(v) for v in self._outgoing.values())

    def stats(self) -> dict:
        return {
            "nodes": len(self._nodes),
            "relations": self.relation_count(),
            "outgoing_edges": sum(len(v) for v in self._outgoing.values()),
            "incoming_edges": sum(len(v) for v in self._incoming.values()),
        }
