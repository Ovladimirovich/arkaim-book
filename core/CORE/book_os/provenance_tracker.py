"""ProvenanceTracker — трассировка происхождения каждого факта."""

import json
from pathlib import Path
from typing import List, Optional

from schemas.provenance import Provenance
from book_os.exceptions import OSInternalError

OS_DATA_DIR = Path(__file__).resolve().parents[2] / "OS_DATA"


class ProvenanceTracker:
    """Реестр происхождения фактов.

    Каждый Fact имеет соответствующую Provenance-запись,
    которая описывает откуда факт взялся и какова его достоверность.

    Данные: OS_DATA/provenance/registry.json
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or OS_DATA_DIR
        self._path = self.data_dir / "provenance" / "registry.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._registry: dict = {}
        self._load()

    def register(self, fact_id: str, provenance: Provenance) -> None:
        """Зарегистрировать происхождение для факта."""
        if provenance.fact_id != fact_id:
            provenance.fact_id = fact_id
        self._registry[fact_id] = provenance
        self._save()

    def get(self, fact_id: str) -> Provenance:
        """Вернуть происхождение факта по ID."""
        prov = self._registry.get(fact_id)
        if prov is None:
            raise OSInternalError(f"Provenance not found for fact: {fact_id}")
        return prov

    def get_by_document(self, doc_id: str) -> List[Provenance]:
        """Все записи provenance для фактов из документа."""
        return [
            p for p in self._registry.values()
            if p.doc_id == doc_id
        ]

    def delete_by_document(self, doc_id: str) -> int:
        """Удалить все записи provenance для фактов из документа. Возвращает кол-во."""
        ids = [fid for fid, p in self._registry.items() if p.doc_id == doc_id]
        for fid in ids:
            del self._registry[fid]
        if ids:
            self._save()
        return len(ids)

    def get_by_entity(self, entity_id: str,
                      fact_store) -> List[Provenance]:
        """Все записи provenance для фактов о сущности.

        Принимает FactStore (или объект с get_by_entity), чтобы
        найти факты о сущности и вернуть их provenance.
        """
        facts = fact_store.get_by_entity(entity_id)
        result = []
        for fact in facts:
            prov = self._registry.get(fact.id)
            if prov:
                result.append(prov)
        return result

    def verify(self, fact_id: str, fact_store=None) -> bool:
        """Проверить цепочку происхождения факта.

        source — всегда валиден.
        derived — требует source-фактов в цепочке.
        interpretation, external, hypothesis — всегда валидны (но маркированы).
        """
        prov = self.get(fact_id)
        if prov.type == "source":
            return prov.doc_id is not None
        if prov.type == "derived":
            if fact_store is None:
                return True
            fact = fact_store.get(fact_id)
            sources = fact_store.get_by_entity(fact.entity_id, provenance="source")
            return len(sources) > 0
        return True

    def get_chain(self, fact_id: str, fact_store=None,
                  depth: int = 5) -> List[dict]:
        """Получить цепочку происхождения: от факта к source.

        Возвращает список dict: {fact_id, statement, provenance_type, label}
        Поднимается по derived → source, максимум depth шагов.
        """
        chain = []
        current_id = fact_id
        visited = set()

        for _ in range(depth):
            if current_id in visited:
                break
            visited.add(current_id)

            prov = self._registry.get(current_id)
            if prov is None:
                break

            if fact_store:
                try:
                    fact = fact_store.get(current_id)
                    statement = fact.statement[:100]
                except Exception:
                    statement = ""
            else:
                statement = ""

            entry = {
                "fact_id": current_id,
                "statement": statement,
                "provenance_type": prov.type,
                "label": prov.label,
            }
            chain.append(entry)

            if prov.type == "source":
                break

            if prov.type == "derived" and fact_store:
                fact = fact_store.get(current_id)
                sources = fact_store.get_by_entity(fact.entity_id, provenance="source")
                if sources:
                    current_id = sources[0].id
                else:
                    break
            else:
                break

        return chain

    def get_stats(self) -> dict:
        """Статистика реестра."""
        by_type = {}
        for prov in self._registry.values():
            by_type[prov.type] = by_type.get(prov.type, 0) + 1
        return {
            "total": len(self._registry),
            "by_type": by_type,
        }

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._registry = {}
            for item in data:
                prov = Provenance(**item)
                self._registry[prov.fact_id] = prov
        except Exception:
            self._registry = {}

    def _save(self) -> None:
        data = [p.model_dump(mode="json") for p in self._registry.values()]
        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
