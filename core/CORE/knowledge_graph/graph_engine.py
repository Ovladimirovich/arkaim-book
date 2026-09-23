"""
GraphEngine — ядро графовых запросов.
Строит граф из хранилищ BOOK OS и генома.
Поддерживает: соседи, путь, подграф, контекст для RAG.
"""
from collections import deque
from typing import Optional

from book_os.entity_store import EntityStore
from book_os.relationship_store import RelationshipStore
from book_os.fact_store import FactStore


class GraphEngine:
    def __init__(self, entity_store: EntityStore, rel_store: RelationshipStore, fact_store: FactStore):
        self._entity_store = entity_store
        self._rel_store = rel_store
        self._fact_store = fact_store
        self._adjacency: dict[str, list[dict]] = {}
        self._node_types: dict[str, str] = {}
        self._node_names: dict[str, str] = {}
        self._built = False

    def build(self):
        """Построить граф из всех хранилищ."""
        self._adjacency.clear()
        self._node_types.clear()
        self._node_names.clear()

        for entity in self._entity_store.list():
            nid = entity.id
            self._node_types[nid] = entity.type
            self._node_names[nid] = entity.name
            if nid not in self._adjacency:
                self._adjacency[nid] = []

        for rel in self._rel_store.list():
            src = rel.source_id
            tgt = rel.target_id
            if src not in self._adjacency:
                self._adjacency[src] = []
            if tgt not in self._adjacency:
                self._adjacency[tgt] = []
            self._adjacency[src].append({
                "target_id": tgt,
                "type": rel.type,
                "rel_id": rel.id,
                "direction": "outgoing",
            })
            self._adjacency[tgt].append({
                "target_id": src,
                "type": rel.type,
                "rel_id": rel.id,
                "direction": "incoming",
            })

        self._built = True

    def get_neighbors(self, entity_id: str, rel_type: Optional[str] = None, max_depth: int = 1) -> list[dict]:
        """Получить соседей сущности (BFS до max_depth)."""
        if not self._built:
            self.build()
        if max_depth == 1:
            edges = self._adjacency.get(entity_id, [])
            if rel_type:
                edges = [e for e in edges if e["type"] == rel_type]
            result = []
            seen_ids = set()
            for e in edges:
                nid = e["target_id"]
                if nid in seen_ids:
                    continue
                seen_ids.add(nid)
                entity = self._entity_store.get_by_id(nid)
                result.append({
                    "entity_id": nid,
                    "name": entity.name if entity else nid,
                    "type": self._node_types.get(nid, "unknown"),
                    "relationship_type": e["type"],
                    "direction": e["direction"],
                })
            return result

        visited = {entity_id: 0}
        queue = deque([entity_id])
        result = []
        while queue:
            current = queue.popleft()
            depth = visited[current]
            if depth > 0:
                entity = self._entity_store.get_by_id(current)
                result.append({
                    "entity_id": current,
                    "name": entity.name if entity else current,
                    "type": self._node_types.get(current, "unknown"),
                    "depth": depth,
                })
            if depth >= max_depth:
                continue
            for edge in self._adjacency.get(current, []):
                nid = edge["target_id"]
                if nid not in visited:
                    visited[nid] = depth + 1
                    queue.append(nid)
        return result

    def shortest_path(self, from_id: str, to_id: str) -> list[dict]:
        """BFS кратчайший путь между двумя сущностями."""
        if not self._built:
            self.build()
        visited = {from_id: (None, None)}
        queue = deque([from_id])
        while queue:
            current = queue.popleft()
            if current == to_id:
                path = []
                node = current
                while node is not None:
                    prev, edge_type = visited[node]
                    entry = {"entity_id": node, "name": self._node_names.get(node, node), "type": self._node_types.get(node, "unknown")}
                    if edge_type:
                        entry["via"] = edge_type
                    path.append(entry)
                    node = prev
                path.reverse()
                return path
            for edge in self._adjacency.get(current, []):
                nid = edge["target_id"]
                if nid not in visited:
                    visited[nid] = (current, edge["type"])
                    queue.append(nid)
        return []

    def subgraph(self, entity_ids: list[str], depth: int = 1) -> dict:
        """Извлечь подграф вокруг заданных сущностей."""
        if not self._built:
            self.build()
        nodes = {}
        edges = []
        seen_edges = set()

        for eid in entity_ids:
            entity = self._entity_store.get_by_id(eid)
            if entity:
                nodes[eid] = {"id": eid, "name": entity.name, "type": entity.type}

        for eid in entity_ids:
            for edge in self._adjacency.get(eid, []):
                ekey = f"{eid}-{edge['target_id']}-{edge['type']}"
                if ekey in seen_edges:
                    continue
                seen_edges.add(ekey)
                edges.append({
                    "source_id": eid,
                    "target_id": edge["target_id"],
                    "type": edge["type"],
                })
                tnid = edge["target_id"]
                if tnid not in nodes and depth > 0:
                    tentity = self._entity_store.get_by_id(tnid)
                    if tentity:
                        nodes[tnid] = {"id": tnid, "name": tentity.name, "type": tentity.type}

        return {"nodes": list(nodes.values()), "edges": edges}

    def context_for_entities(self, entity_ids: list[str], max_neighbors: int = 5) -> str:
        """Сформировать текстовый контекст для RAG о сущностях и их окружении."""
        if not self._built:
            self.build()
        lines = []
        for eid in entity_ids:
            entity = self._entity_store.get_by_id(eid)
            if not entity:
                continue
            lines.append(f"Сущность: {entity.name} ({entity.type})")
            if entity.description:
                lines.append(f"  Описание: {entity.description}")
            if entity.aliases:
                lines.append(f"  Алиасы: {', '.join(entity.aliases)}")

            facts = self._fact_store.get_by_entity(entity_id=eid)[:5]
            for f in facts:
                lines.append(f"  Факт: {f.statement} (достоверность: {f.confidence})")

            neighbors = self.get_neighbors(eid, max_depth=1)
            if neighbors:
                lines.append("  Связи:")
                for nb in neighbors[:max_neighbors]:
                    lines.append(f"    - [{nb['relationship_type']}] → {nb['name']} ({nb['type']})")

            lines.append("")
        return "\n".join(lines)

    def stats(self) -> dict:
        if not self._built:
            self.build()
        node_types = {}
        rel_types = {}
        for nid, ntype in self._node_types.items():
            node_types[ntype] = node_types.get(ntype, 0) + 1
        for nid, edges in self._adjacency.items():
            for e in edges:
                rel_types[e["type"]] = rel_types.get(e["type"], 0) + 1
        return {
            "nodes": len(self._node_types),
            "edges": sum(len(e) for e in self._adjacency.values()) // 2,
            "node_types": node_types,
            "relationship_types": rel_types,
        }
