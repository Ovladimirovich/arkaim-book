"""
interpretations — интерпретации читателей.

Читатели делятся своим пониманием книги.
Каждая интерпретация привязывается к темам, персонажам, цитатам.
"""
import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger("hermes.interpretations")

DATA_DIR = Path(__file__).resolve().parents[2] / "OS_DATA" / "interpretations"
DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Interpretation:
    """Интерпретация читателя."""
    id: str
    reader_id: str
    reader_name: str
    text: str
    themes: list[str] = field(default_factory=list)
    characters: list[str] = field(default_factory=list)
    quotes: list[str] = field(default_factory=list)
    created_at: str = ""
    status: str = "pending"  # pending, approved, rejected
    likes: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Interpretation":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class InterpretationStore:
    """Хранилище интерпретаций (JSON-based)."""

    def __init__(self, data_dir: Optional[Path] = None):
        self._dir = data_dir or DATA_DIR
        self._file = self._dir / "interpretations.json"
        self._items: list[Interpretation] = []
        self._load()

    def _load(self):
        if self._file.exists():
            try:
                data = json.loads(self._file.read_text(encoding="utf-8-sig"))
                self._items = [Interpretation.from_dict(d) for d in data]
            except Exception as e:
                log.error("interpretations_load_error error=%s", e)
                self._items = []

    def _save(self):
        try:
            self._file.write_text(
                json.dumps([i.to_dict() for i in self._items], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            log.error("interpretations_save_error error=%s", e)

    async def submit(
        self,
        reader_id: str,
        reader_name: str,
        text: str,
        themes: list[str] | None = None,
        characters: list[str] | None = None,
        quotes: list[str] | None = None,
    ) -> Interpretation:
        """Читатель отправляет интерпретацию."""
        interp = Interpretation(
            id=uuid.uuid4().hex[:12],
            reader_id=reader_id,
            reader_name=reader_name,
            text=text,
            themes=themes or [],
            characters=characters or [],
            quotes=quotes or [],
            created_at=datetime.now(tz=timezone.utc).isoformat(),
            status="pending",
        )
        self._items.append(interp)
        self._save()
        log.info("interpretation_submitted id=%s reader=%s", interp.id, reader_id)
        return interp

    async def get_all(self, status: str | None = None) -> list[Interpretation]:
        """Получить все интерпретации (опционально по статусу)."""
        if status:
            return [i for i in self._items if i.status == status]
        return list(self._items)

    async def get_by_reader(self, reader_id: str) -> list[Interpretation]:
        """Получить интерпретации конкретного читателя."""
        return [i for i in self._items if i.reader_id == reader_id]

    async def approve(self, interp_id: str) -> bool:
        """Одобрить интерпретацию."""
        for item in self._items:
            if item.id == interp_id:
                item.status = "approved"
                self._save()
                log.info("interpretation_approved id=%s", interp_id)
                return True
        return False

    async def reject(self, interp_id: str) -> bool:
        """Отклонить интерпретацию."""
        for item in self._items:
            if item.id == interp_id:
                item.status = "rejected"
                self._save()
                log.info("interpretation_rejected id=%s", interp_id)
                return True
        return False

    async def like(self, interp_id: str) -> bool:
        """Поставить лайк интерпретации."""
        for item in self._items:
            if item.id == interp_id:
                item.likes += 1
                self._save()
                return True
        return False

    async def delete(self, interp_id: str) -> bool:
        """Удалить интерпретацию."""
        before = len(self._items)
        self._items = [i for i in self._items if i.id != interp_id]
        if len(self._items) < before:
            self._save()
            log.info("interpretation_deleted id=%s", interp_id)
            return True
        return False

    def get_stats(self) -> dict:
        """Статистика интерпретаций."""
        total = len(self._items)
        pending = sum(1 for i in self._items if i.status == "pending")
        approved = sum(1 for i in self._items if i.status == "approved")
        rejected = sum(1 for i in self._items if i.status == "rejected")
        return {
            "total": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
        }

