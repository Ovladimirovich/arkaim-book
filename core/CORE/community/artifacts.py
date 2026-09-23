"""
artifacts — коллекция артефактов читателей.

Читатели делятся находками: археология, легенды, символы.
Каждый артефакт привязывается к тексту книги.
"""
import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger("hermes.artifacts")

DATA_DIR = Path(__file__).resolve().parents[2] / "OS_DATA" / "artifacts"
DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Artifact:
    """Артефакт — находка или связь, найденная читателем."""
    id: str
    reader_id: str
    reader_name: str
    title: str
    description: str
    category: str  # archaeology, legend, symbol, connection
    source: str  # откуда информация (книга, сайт, музей)
    connection_to_book: str  # как связно с книгой
    related_themes: list[str] = field(default_factory=list)
    related_characters: list[str] = field(default_factory=list)
    related_quotes: list[str] = field(default_factory=list)
    location: str = ""  # географическое местоположение (если есть)
    url: str = ""  # ссылка на источник
    created_at: str = ""
    status: str = "pending"  # pending, approved, rejected
    likes: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Artifact":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class ArtifactStore:
    """Хранилище артефактов (JSON-based)."""

    def __init__(self, data_dir: Optional[Path] = None):
        self._dir = data_dir or DATA_DIR
        self._file = self._dir / "artifacts.json"
        self._items: list[Artifact] = []
        self._load()

    def _load(self):
        if self._file.exists():
            try:
                data = json.loads(self._file.read_text(encoding="utf-8-sig"))
                self._items = [Artifact.from_dict(d) for d in data]
            except Exception as e:
                log.error("artifacts_load_error error=%s", e)
                self._items = []

    def _save(self):
        try:
            self._file.write_text(
                json.dumps([a.to_dict() for a in self._items], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            log.error("artifacts_save_error error=%s", e)

    async def submit(
        self,
        reader_id: str,
        reader_name: str,
        title: str,
        description: str,
        category: str,
        source: str,
        connection_to_book: str,
        related_themes: list[str] | None = None,
        related_characters: list[str] | None = None,
        related_quotes: list[str] | None = None,
        location: str = "",
        url: str = "",
    ) -> Artifact:
        """Читатель отправляет артефакт."""
        artifact = Artifact(
            id=uuid.uuid4().hex[:12],
            reader_id=reader_id,
            reader_name=reader_name,
            title=title,
            description=description,
            category=category,
            source=source,
            connection_to_book=connection_to_book,
            related_themes=related_themes or [],
            related_characters=related_characters or [],
            related_quotes=related_quotes or [],
            location=location,
            url=url,
            created_at=datetime.now(tz=timezone.utc).isoformat(),
            status="pending",
        )
        self._items.append(artifact)
        self._save()
        log.info("artifact_submitted id=%s reader=%s category=%s", artifact.id, reader_id, category)
        return artifact

    async def get_all(self, status: str | None = None, category: str | None = None) -> list[Artifact]:
        """Получить все артефакты."""
        result = self._items
        if status:
            result = [a for a in result if a.status == status]
        if category:
            result = [a for a in result if a.category == category]
        return result

    async def get_by_reader(self, reader_id: str) -> list[Artifact]:
        """Получить артефакты конкретного читателя."""
        return [a for a in self._items if a.reader_id == reader_id]

    async def approve(self, artifact_id: str) -> bool:
        """Одобрить артефакт."""
        for item in self._items:
            if item.id == artifact_id:
                item.status = "approved"
                self._save()
                log.info("artifact_approved id=%s", artifact_id)
                return True
        return False

    async def reject(self, artifact_id: str) -> bool:
        """Отклонить артефакт."""
        for item in self._items:
            if item.id == artifact_id:
                item.status = "rejected"
                self._save()
                log.info("artifact_rejected id=%s", artifact_id)
                return True
        return False

    async def like(self, artifact_id: str) -> bool:
        """Поставить лайк."""
        for item in self._items:
            if item.id == artifact_id:
                item.likes += 1
                self._save()
                return True
        return False

    async def delete(self, artifact_id: str) -> bool:
        """Удалить артефакт."""
        before = len(self._items)
        self._items = [a for a in self._items if a.id != artifact_id]
        if len(self._items) < before:
            self._save()
            log.info("artifact_deleted id=%s", artifact_id)
            return True
        return False

    def get_stats(self) -> dict:
        """Статистика артефактов."""
        total = len(self._items)
        categories = {}
        for a in self._items:
            categories[a.category] = categories.get(a.category, 0) + 1
        return {
            "total": total,
            "pending": sum(1 for a in self._items if a.status == "pending"),
            "approved": sum(1 for a in self._items if a.status == "approved"),
            "categories": categories,
        }

