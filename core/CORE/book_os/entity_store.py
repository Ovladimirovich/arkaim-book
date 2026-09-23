"""EntityStore — реестр сущностей мира книги."""

import json
from pathlib import Path
from typing import List, Optional, Set

from schemas.entity import Entity
from book_os.exceptions import EntityNotFoundError

OS_DATA_DIR = Path(__file__).resolve().parents[2] / "OS_DATA"
CANONICAL_MAP: dict = {}


class EntityStore:
    """Хранилище сущностей с разрешением алиасов.

    Данные: OS_DATA/graph/entities.json
    Алиасы загружаются из NameResolver через set_canonical_map().
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or OS_DATA_DIR
        self._path = self.data_dir / "graph" / "entities.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._entities: dict = {}
        self._alias_to_canonical: dict = {}
        self._canonical_to_aliases: dict = {}
        self._load()

    # ── Управление алиасами ──────────────────────

    def set_canonical_map(self, alias_map: dict, alias_reverse: dict) -> None:
        """Загрузить карту алиасов из NameResolver.

        Принимает:
          alias_map:       {alias_lower: canonical_name}
          alias_reverse:   {canonical_name: [alias_lower, ...]}
        """
        self._alias_to_canonical = alias_map
        self._canonical_to_aliases = alias_reverse

    def resolve(self, name: str) -> str:
        """Привести любое имя/алиас к канонической форме."""
        canonical = self._alias_to_canonical.get(name.lower())
        if canonical:
            return canonical
        return name

    def get_all_aliases(self, canonical: str) -> Set[str]:
        """Все алиасы для канонического имени."""
        return self._canonical_to_aliases.get(canonical, {canonical})

    # ── CRUD ─────────────────────────────────────

    def add(self, entity: Entity) -> Entity:
        """Добавить сущность. Если ID существует — перезаписать."""
        self._entities[entity.id] = entity
        self._save()
        return entity

    def get(self, name: str) -> Entity:
        """Получить сущность по имени (с разрешением алиасов)."""
        canonical = self.resolve(name)
        for entity in self._entities.values():
            if entity.name == canonical:
                return entity
        raise EntityNotFoundError(f"Entity not found: {name}")

    def get_by_id(self, entity_id: str) -> Entity:
        """Получить сущность по UUID."""
        entity = self._entities.get(entity_id)
        if entity is None:
            raise EntityNotFoundError(f"Entity not found by id: {entity_id}")
        return entity

    def search(self, query: str, entity_type: Optional[str] = None) -> List[Entity]:
        """Поиск сущностей по имени/алиасу (частичное совпадение)."""
        query_lower = query.lower()
        matches = []
        for entity in self._entities.values():
            if entity_type and entity.type != entity_type:
                continue
            if query_lower in entity.name.lower():
                matches.append(entity)
                continue
            for alias in entity.aliases:
                if query_lower in alias.lower():
                    matches.append(entity)
                    break
        return matches

    def list(self, entity_type: Optional[str] = None) -> List[Entity]:
        """Список всех сущностей (с фильтром по типу)."""
        if entity_type:
            return [e for e in self._entities.values() if e.type == entity_type]
        return list(self._entities.values())

    def delete(self, entity_id: str) -> None:
        """Удалить сущность по ID."""
        if entity_id not in self._entities:
            raise EntityNotFoundError(f"Entity not found: {entity_id}")
        del self._entities[entity_id]
        self._save()

    def get_stats(self) -> dict:
        """Статистика хранилища."""
        by_type = {}
        for entity in self._entities.values():
            by_type[entity.type] = by_type.get(entity.type, 0) + 1
        return {
            "total": len(self._entities),
            "by_type": by_type,
        }

    # ── Персистентность ──────────────────────────

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._entities = {}
            for item in data:
                entity = Entity(**item)
                self._entities[entity.id] = entity
        except Exception:
            self._entities = {}

    def _save(self) -> None:
        data = [e.model_dump(mode="json") for e in self._entities.values()]
        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
