"""FactStore — хранилище атомарных утверждений о сущностях."""

import json
from pathlib import Path
from typing import List, Optional

from schemas.fact import Fact
from book_os.exceptions import OSInternalError

OS_DATA_DIR = Path(__file__).resolve().parents[2] / "OS_DATA"


class FactStore:
    """Хранилище фактов.

    Данные: OS_DATA/graph/facts.json
    Индексы: entity_id, doc_id.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or OS_DATA_DIR
        self._path = self.data_dir / "graph" / "facts.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._facts: dict = {}
        self._load()

    def add(self, fact: Fact) -> Fact:
        """Добавить факт. Если ID существует — перезаписать."""
        self._facts[fact.id] = fact
        self._save()
        return fact

    def get(self, fact_id: str) -> Fact:
        """Получить факт по ID."""
        fact = self._facts.get(fact_id)
        if fact is None:
            raise OSInternalError(f"Fact not found: {fact_id}")
        return fact

    def get_by_entity(self, entity_id: str,
                      provenance: Optional[str] = None) -> List[Fact]:
        """Все факты о сущности (с фильтром по provenance)."""
        matches = []
        for fact in self._facts.values():
            if fact.entity_id != entity_id:
                continue
            if provenance and fact.provenance != provenance:
                continue
            matches.append(fact)
        return matches

    def get_by_document(self, doc_id: str) -> List[Fact]:
        """Все факты из документа."""
        return [
            f for f in self._facts.values()
            if f.doc_id == doc_id
        ]

    def search(self, statement: str) -> List[Fact]:
        """Поиск фактов по тексту утверждения (частичное совпадение)."""
        query = statement.lower()
        return [
            f for f in self._facts.values()
            if query in f.statement.lower()
        ]

    def list(self) -> List[Fact]:
        """Все факты."""
        return list(self._facts.values())

    def delete(self, fact_id: str) -> None:
        """Удалить факт по ID."""
        if fact_id not in self._facts:
            raise OSInternalError(f"Fact not found: {fact_id}")
        del self._facts[fact_id]
        self._save()

    def delete_by_entity(self, entity_id: str) -> int:
        """Удалить все факты о сущности. Возвращает количество."""
        ids = [fid for fid, f in self._facts.items() if f.entity_id == entity_id]
        for fid in ids:
            del self._facts[fid]
        if ids:
            self._save()
        return len(ids)

    def get_stats(self) -> dict:
        """Статистика хранилища."""
        by_provenance = {}
        by_entity = {}
        for fact in self._facts.values():
            by_provenance[fact.provenance] = by_provenance.get(fact.provenance, 0) + 1
            by_entity[fact.entity_id] = by_entity.get(fact.entity_id, 0) + 1
        return {
            "total": len(self._facts),
            "by_provenance": by_provenance,
            "entities_with_facts": len(by_entity),
        }

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._facts = {}
            for item in data:
                fact = Fact(**item)
                self._facts[fact.id] = fact
        except Exception:
            self._facts = {}

    def _save(self) -> None:
        data = [f.model_dump(mode="json") for f in self._facts.values()]
        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
