"""Relation Model — граф связей между сущностями мира."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger("hermes.relation_model")


# ── Типы связей ────────────────────────────────────────────────

class RelationType(str, Enum):
    """8 типов связей в мире."""
    
    # Причинные
    CAUSAL = "causal"                    # A вызывает B
    
    # Исторические
    HISTORICAL = "historical"            # A предшествует B во времени
    
    # Географические
    GEOGRAPHIC = "geographic"            # A находится рядом с B
    
    # Философские
    PHILOSOPHICAL = "philosophical"      # A связано с B по смыслу
    
    # Мифологические
    MYTHOLOGICAL = "mythological"        # A связано с B через миф
    
    # Археологические
    ARCHAEOLOGICAL = "archaeological"    # A подтверждается через B
    
    # Символические
    SYMBOLIC = "symbolic"                # A символизирует B
    
    # Культурные
    CULTURAL = "cultural"                # A принадлежит культуре B


class RelationStrength(str, Enum):
    """Сила связи."""
    STRONG = "strong"        # 0.8-1.0
    MODERATE = "moderate"    # 0.5-0.7
    WEAK = "weak"            # 0.2-0.4
    INFERRED = "inferred"    # 0.1 (выведено, не явно)


@dataclass
class WorldRelation:
    """Связь между двумя сущностями мира."""
    id: str
    source_id: str
    target_id: str
    relation_type: RelationType
    description: str = ""
    strength: float = 1.0
    evidence: list[str] = field(default_factory=list)  # ID сущностей-доказательств
    epoch: str = ""
    bidirectional: bool = False
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "description": self.description,
            "strength": self.strength,
            "evidence": self.evidence,
            "epoch": self.epoch,
            "bidirectional": self.bidirectional,
        }


@dataclass
class RelationPath:
    """Путь связей между двумя сущностями."""
    source_id: str
    target_id: str
    relations: list[WorldRelation]
    total_strength: float = 0.0
    path_length: int = 0
    
    def __post_init__(self):
        self.path_length = len(self.relations)
        if self.relations:
            self.total_strength = sum(r.strength for r in self.relations) / len(self.relations)


# ── Граф связей ────────────────────────────────────────────────

class RelationGraph:
    """Граф связей между сущностями мира.
    
    Хранит:
    - 8 типов связей
    - Индексы для быстрого поиска
    - Методы поиска путей
    """
    
    def __init__(self):
        self._relations: dict[str, WorldRelation] = {}
        self._by_source: dict[str, list[str]] = {}  # source_id → [relation_ids]
        self._by_target: dict[str, list[str]] = {}  # target_id → [relation_ids]
        self._by_type: dict[str, list[str]] = {}    # relation_type → [relation_ids]
    
    def add_relation(self, relation: WorldRelation):
        """Добавить связь в граф."""
        self._relations[relation.id] = relation
        
        # Индекс по источнику
        if relation.source_id not in self._by_source:
            self._by_source[relation.source_id] = []
        self._by_source[relation.source_id].append(relation.id)
        
        # Индекс по цели
        if relation.target_id not in self._by_target:
            self._by_target[relation.target_id] = []
        self._by_target[relation.target_id].append(relation.id)
        
        # Если двунаправленная — добавляем и обратный индекс
        if relation.bidirectional:
            if relation.target_id not in self._by_source:
                self._by_source[relation.target_id] = []
            self._by_source[relation.target_id].append(relation.id)
            
            if relation.source_id not in self._by_target:
                self._by_target[relation.source_id] = []
            self._by_target[relation.source_id].append(relation.id)
        
        # Индекс по типу
        rt = relation.relation_type.value
        if rt not in self._by_type:
            self._by_type[rt] = []
        self._by_type[rt].append(relation.id)
    
    def get_relation(self, relation_id: str) -> Optional[WorldRelation]:
        """Получить связь по ID."""
        return self._relations.get(relation_id)
    
    def get_relations_from(self, entity_id: str) -> list[WorldRelation]:
        """Получить все связи от сущности."""
        ids = self._by_source.get(entity_id, [])
        return [self._relations[rid] for rid in ids if rid in self._relations]
    
    def get_relations_to(self, entity_id: str) -> list[WorldRelation]:
        """Получить все связи к сущности."""
        ids = self._by_target.get(entity_id, [])
        return [self._relations[rid] for rid in ids if rid in self._relations]
    
    def get_relations_of_type(self, relation_type: RelationType) -> list[WorldRelation]:
        """Получить все связи определённого типа."""
        ids = self._by_type.get(relation_type.value, [])
        return [self._relations[rid] for rid in ids if rid in self._relations]
    
    def get_neighbors(self, entity_id: str, max_depth: int = 1) -> dict[str, list[WorldRelation]]:
        """Получить соседей сущности с глубиной."""
        neighbors = {}
        visited = set()
        
        def _dfs(current_id: str, depth: int):
            if depth > max_depth or current_id in visited:
                return
            visited.add(current_id)
            
            # Связи от текущей сущности
            for rel in self.get_relations_from(current_id):
                neighbor_id = rel.target_id
                if neighbor_id not in neighbors:
                    neighbors[neighbor_id] = []
                neighbors[neighbor_id].append(rel)
                _dfs(neighbor_id, depth + 1)
            
            # Связи к текущей сущности
            for rel in self.get_relations_to(current_id):
                neighbor_id = rel.source_id
                if neighbor_id not in neighbors:
                    neighbors[neighbor_id] = []
                neighbors[neighbor_id].append(rel)
                _dfs(neighbor_id, depth + 1)
        
        _dfs(entity_id, 1)
        return neighbors
    
    def find_path(self, source_id: str, target_id: str, max_depth: int = 5) -> Optional[RelationPath]:
        """Найти путь между двумя сущностями (BFS)."""
        if source_id == target_id:
            return RelationPath(source_id, target_id, [])
        
        queue = [(source_id, [])]
        visited = {source_id}
        
        for _ in range(max_depth):
            next_queue = []
            for current_id, path in queue:
                # Проверяем связи от текущей
                for rel in self.get_relations_from(current_id):
                    if rel.target_id == target_id:
                        return RelationPath(source_id, target_id, path + [rel])
                    if rel.target_id not in visited:
                        visited.add(rel.target_id)
                        next_queue.append((rel.target_id, path + [rel]))
                
                # Проверяем связи к текущей
                for rel in self.get_relations_to(current_id):
                    if rel.source_id == target_id:
                        return RelationPath(source_id, target_id, path + [rel])
                    if rel.source_id not in visited:
                        visited.add(rel.source_id)
                        next_queue.append((rel.source_id, path + [rel]))
            
            queue = next_queue
        
        return None
    
    def get_entity_context(self, entity_id: str) -> dict:
        """Получить контекст сущности — все её связи."""
        from_relations = self.get_relations_from(entity_id)
        to_relations = self.get_relations_to(entity_id)
        
        return {
            "entity_id": entity_id,
            "outgoing": [r.to_dict() for r in from_relations],
            "incoming": [r.to_dict() for r in to_relations],
            "outgoing_count": len(from_relations),
            "incoming_count": len(to_relations),
        }
    
    def get_stats(self) -> dict:
        """Статистика графа."""
        return {
            "total_relations": len(self._relations),
            "by_type": {rt: len(ids) for rt, ids in self._by_type.items()},
            "entities_with_relations": len(set(
                list(self._by_source.keys()) + list(self._by_target.keys())
            )),
        }
    
    def summary(self) -> str:
        """Текстовая сводка."""
        stats = self.get_stats()
        parts = [f"{count} {rt}" for rt, count in stats["by_type"].items()]
        return (
            f"Граф связей: {stats['total_relations']} связей "
            f"({', '.join(parts)})"
        )
    
    def save(self, path: Path):
        """Сохранить граф в JSON."""
        data = {
            "relations": [r.to_dict() for r in self._relations.values()],
            "stats": self.get_stats(),
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    @classmethod
    def load(cls, path: Path) -> "RelationGraph":
        """Загрузить граф из JSON."""
        graph = cls()
        if not path.exists():
            return graph
        
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            for rel_data in data.get("relations", []):
                relation = WorldRelation(
                    id=rel_data["id"],
                    source_id=rel_data["source_id"],
                    target_id=rel_data["target_id"],
                    relation_type=RelationType(rel_data["relation_type"]),
                    description=rel_data.get("description", ""),
                    strength=rel_data.get("strength", 1.0),
                    evidence=rel_data.get("evidence", []),
                    epoch=rel_data.get("epoch", ""),
                    bidirectional=rel_data.get("bidirectional", False),
                )
                graph.add_relation(relation)
        except Exception as e:
            log.error("relation_graph_load_error: %s", e)
        
        return graph
