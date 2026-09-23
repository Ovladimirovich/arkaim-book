"""Comments — комментарии к интерпретациям и артефактам."""

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger("hermes.comments")

DATA_DIR = Path(__file__).resolve().parents[2] / "OS_DATA" / "comments"
DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Comment:
    """Комментарий к элементу сообщества."""
    id: str
    parent_id: str  # ID интерпретации или артефакта
    parent_type: str  # interpretation / artifact
    reader_id: str
    reader_name: str
    text: str
    created_at: str = ""
    likes: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Comment":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class CommentStore:
    """Хранилище комментариев (JSON-based)."""

    def __init__(self, data_dir: Optional[Path] = None):
        self._dir = data_dir or DATA_DIR
        self._file = self._dir / "comments.json"
        self._items: list[Comment] = []
        self._load()

    def _load(self):
        if self._file.exists():
            try:
                data = json.loads(self._file.read_text(encoding="utf-8-sig"))
                self._items = [Comment.from_dict(d) for d in data]
            except Exception as e:
                log.error("comments_load_error error=%s", e)
                self._items = []

    def _save(self):
        try:
            self._file.write_text(
                json.dumps([c.to_dict() for c in self._items], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            log.error("comments_save_error error=%s", e)

    async def add(
        self,
        parent_id: str,
        parent_type: str,
        reader_id: str,
        reader_name: str,
        text: str,
    ) -> Comment:
        """Добавить комментарий."""
        comment = Comment(
            id=uuid.uuid4().hex[:12],
            parent_id=parent_id,
            parent_type=parent_type,
            reader_id=reader_id,
            reader_name=reader_name,
            text=text,
            created_at=datetime.now(tz=timezone.utc).isoformat(),
        )
        self._items.append(comment)
        self._save()
        log.info("comment_added id=%s parent=%s/%s", comment.id, parent_type, parent_id)
        return comment

    async def get_for_parent(self, parent_id: str) -> list[Comment]:
        """Получить комментарии к элементу."""
        comments = [c for c in self._items if c.parent_id == parent_id]
        comments.sort(key=lambda c: c.created_at)
        return comments

    async def get_by_reader(self, reader_id: str) -> list[Comment]:
        """Получить комментарии читателя."""
        return [c for c in self._items if c.reader_id == reader_id]

    async def delete(self, comment_id: str) -> bool:
        """Удалить комментарий."""
        before = len(self._items)
        self._items = [c for c in self._items if c.id != comment_id]
        if len(self._items) < before:
            self._save()
            log.info("comment_deleted id=%s", comment_id)
            return True
        return False

    async def like(self, comment_id: str) -> bool:
        """Поставить лайк комментарию."""
        for item in self._items:
            if item.id == comment_id:
                item.likes += 1
                self._save()
                return True
        return False

    def get_stats(self) -> dict:
        """Статистика комментариев."""
        total = len(self._items)
        by_type = {}
        for c in self._items:
            by_type[c.parent_type] = by_type.get(c.parent_type, 0) + 1
        return {"total": total, "by_type": by_type}
