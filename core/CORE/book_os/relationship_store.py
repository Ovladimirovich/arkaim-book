"""RelationshipStore — хранилище связей между сущностями."""

import json
from pathlib import Path
from typing import List, Optional

from schemas.relationship import Relationship
from book_os.exceptions import OSInternalError

OS_DATA_DIR = Path(__file__).resolve().parents[2] / "OS_DATA"


class RelationshipStore:
    """Хранилище связей.

    Данные: OS_DATA/graph/relationships.json
    Индексы: source_id, target_id, type.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or OS_DATA_DIR
        self._path = self.data_dir / "graph" / "relationships.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._relationships: dict = {}
        self._load()

    def add(self, rel: Relationship) -> Relationship:
        """Добавить связь. Если ID существует — перезаписать."""
        self._relationships[rel.id] = rel
        self._save()
        return rel

    def get(self, rel_id: str) -> Relationship:
        """Получить связь по ID."""
        rel = self._relationships.get(rel_id)
        if rel is None:
            raise OSInternalError(f"Relationship not found: {rel_id}")
        return rel

    def get_by_entity(self, entity_id: str,
                      rel_type: Optional[str] = None) -> List[Relationship]:
        """Все связи сущности (с фильтром по типу)."""
        matches = []
        for rel in self._relationships.values():
            if rel.source_id != entity_id and rel.target_id != entity_id:
                continue
            if rel_type and rel.type != rel_type:
                continue
            matches.append(rel)
        return matches

    def get_between(self, source_id: str, target_id: str) -> Optional[Relationship]:
        """Связь между двумя сущностями (если есть)."""
        for rel in self._relationships.values():
            if rel.source_id == source_id and rel.target_id == target_id:
                return rel
            if rel.source_id == target_id and rel.target_id == source_id:
                return rel
        return None

    def get_by_document(self, doc_id: str) -> List[Relationship]:
        """Все связи из документа."""
        return [
            r for r in self._relationships.values()
            if r.doc_id == doc_id
        ]

    def list(self) -> List[Relationship]:
        """Все связи."""
        return list(self._relationships.values())

    def delete(self, rel_id: str) -> None:
        """Удалить связь по ID."""
        if rel_id not in self._relationships:
            raise OSInternalError(f"Relationship not found: {rel_id}")
        del self._relationships[rel_id]
        self._save()

    def delete_by_entity(self, entity_id: str) -> int:
        """Удалить все связи сущности. Возвращает количество."""
        ids = [
            rid for rid, r in self._relationships.items()
            if r.source_id == entity_id or r.target_id == entity_id
        ]
        for rid in ids:
            del self._relationships[rid]
        if ids:
            self._save()
        return len(ids)

    def get_stats(self) -> dict:
        """Статистика хранилища."""
        by_type = {}
        for rel in self._relationships.values():
            by_type[rel.type] = by_type.get(rel.type, 0) + 1
        return {
            "total": len(self._relationships),
            "by_type": by_type,
        }

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._relationships = {}
            for item in data:
                rel = Relationship(**item)
                self._relationships[rel.id] = rel
        except Exception:
            self._relationships = {}

    def _save(self) -> None:
        data = [r.model_dump(mode="json") for r in self._relationships.values()]
        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
