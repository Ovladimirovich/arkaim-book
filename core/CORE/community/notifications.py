"""Notifications — персональные уведомления для пользователей."""

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger("hermes.notifications")

DATA_DIR = Path(__file__).resolve().parents[2] / "OS_DATA" / "notifications"
DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Notification:
    """Персональное уведомление."""
    id: str
    user_id: str
    type: str  # comment_liked, comment_added, interpretation_approved, interpretation_rejected,
               # artifact_approved, artifact_rejected, question_answered, system
    title: str
    message: str
    link: str = ""  # ссылка на相关内容
    read: bool = False
    created_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Notification":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class NotificationStore:
    """Хранилище уведомлений (JSON-based)."""

    def __init__(self, data_dir: Optional[Path] = None):
        self._dir = data_dir or DATA_DIR
        self._file = self._dir / "notifications.json"
        self._items: list[Notification] = []
        self._load()

    def _load(self):
        if self._file.exists():
            try:
                data = json.loads(self._file.read_text(encoding="utf-8-sig"))
                self._items = [Notification.from_dict(d) for d in data]
            except Exception as e:
                log.error("notifications_load_error error=%s", e)
                self._items = []

    def _save(self):
        try:
            self._file.write_text(
                json.dumps([n.to_dict() for n in self._items], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            log.error("notifications_save_error error=%s", e)

    async def create(
        self,
        user_id: str,
        type: str,
        title: str,
        message: str,
        link: str = "",
    ) -> Notification:
        """Создать уведомление."""
        notification = Notification(
            id=uuid.uuid4().hex[:12],
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            link=link,
            created_at=datetime.now(tz=timezone.utc).isoformat(),
        )
        self._items.append(notification)
        self._save()
        log.info("notification_created id=%s user=%s type=%s", notification.id, user_id, type)
        return notification

    async def get_for_user(self, user_id: str, unread_only: bool = False) -> list[Notification]:
        """Получить уведомления пользователя."""
        items = [n for n in self._items if n.user_id == user_id]
        if unread_only:
            items = [n for n in items if not n.read]
        items.sort(key=lambda n: n.created_at, reverse=True)
        return items

    async def mark_read(self, notification_id: str) -> bool:
        """Отметить уведомление как прочитанное."""
        for item in self._items:
            if item.id == notification_id:
                item.read = True
                self._save()
                return True
        return False

    async def mark_all_read(self, user_id: str) -> int:
        """Отметить все уведомления пользователя как прочитанные."""
        count = 0
        for item in self._items:
            if item.user_id == user_id and not item.read:
                item.read = True
                count += 1
        if count > 0:
            self._save()
        return count

    async def delete(self, notification_id: str) -> bool:
        """Удалить уведомление."""
        before = len(self._items)
        self._items = [n for n in self._items if n.id != notification_id]
        if len(self._items) < before:
            self._save()
            return True
        return False

    def get_unread_count(self, user_id: str) -> int:
        """Количество непрочитанных уведомлений."""
        return sum(1 for n in self._items if n.user_id == user_id and not n.read)

    def get_stats(self) -> dict:
        """Статистика уведомлений."""
        total = len(self._items)
        unread = sum(1 for n in self._items if not n.read)
        by_type = {}
        for n in self._items:
            by_type[n.type] = by_type.get(n.type, 0) + 1
        return {"total": total, "unread": unread, "by_type": by_type}
