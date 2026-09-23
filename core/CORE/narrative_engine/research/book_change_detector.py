"""BookChangeDetector — обнаружение изменений текста книги.

M10: mtime → hash → snapshot паттерн (как Pulse.watch()).
Read-only: не изменяет книгу. Дёшев: mtime-проверка без чтения файла.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger("hermes.narrative.book_change_detector")

# Книга — первичный источник (ADR-0001)
# core/CORE/narrative_engine/research/ → parents[3] = core/
_CORE_DIR = Path(__file__).resolve().parents[3]
BOOK_PATH = _CORE_DIR / "SOURCE_OF_TRUTH" / "BOOK" / "КНИГА.md"


@dataclass
class BookChangeSnapshot:
    """Снимок изменённой книги."""
    path: Path
    mtime: float
    sha256: str
    size_bytes: int
    detected_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    content: str = ""  # полный текст (гранулярность M10: вся книга)


class BookChangeDetector:
    """Детектор изменений КНИГА.md по mtime+hash.

    Паттерн Pulse.watch(): сначала дешёвый mtime-чек,
    при изменении — точный hash-чек (ловит touch без правок).
    Polling-based: вызывающий код решает частоту.
    """

    def __init__(self, book_path: Optional[Path] = None):
        self._path = book_path or BOOK_PATH
        self._last_mtime: float = 0.0
        self._last_hash: str = ""
        self._initialized = False

    @property
    def book_path(self) -> Path:
        return self._path

    def _compute_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def initialize(self) -> None:
        """Зафиксировать базовое состояние (первый запуск).

        Не генерирует snapshot: baseline, от которого считаем diff.
        """
        if not self._path.exists():
            log.warning("book_not_found path=%s", self._path)
            return
        stat = self._path.stat()
        content = self._path.read_text(encoding="utf-8")
        self._last_mtime = stat.st_mtime
        self._last_hash = self._compute_hash(content)
        self._initialized = True
        log.info(
            "book_detector_initialized path=%s size=%d mtime=%s",
            self._path, stat.st_size, self._last_mtime,
        )

    def watch(self) -> Optional[BookChangeSnapshot]:
        """Проверить, изменилась ли книга.

        Returns:
            BookChangeSnapshot если книга реально изменилась (hash),
            None если не изменилась / touch без правок / файл отсутствует.
        """
        if not self._path.exists():
            log.warning("book_not_found path=%s", self._path)
            return None

        if not self._initialized:
            # Первый вызов без initialize() — делаем baseline сами
            self.initialize()
            return None

        try:
            current_mtime = self._path.stat().st_mtime
        except OSError as e:
            log.warning("book_stat_error error=%s", e)
            return None

        # Дешёвая проверка: mtime не изменился → точно нет изменений
        if current_mtime == self._last_mtime:
            return None

        # mtime изменился → точная проверка по hash
        try:
            content = self._path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            log.warning("book_read_error error=%s", e)
            return None

        current_hash = self._compute_hash(content)

        # Touch без правок: mtime другой, содержимое то же
        if current_hash == self._last_hash:
            self._last_mtime = current_mtime  # обновляем baseline mtime
            return None

        # Реальное изменение содержимого
        snapshot = BookChangeSnapshot(
            path=self._path,
            mtime=current_mtime,
            sha256=current_hash,
            size_bytes=len(content.encode("utf-8")),
            content=content,
        )
        self._last_mtime = current_mtime
        self._last_hash = current_hash
        log.info(
            "book_changed size=%d hash=%s...",
            snapshot.size_bytes, current_hash[:12],
        )
        return snapshot

    def current_state(self) -> dict:
        """Диагностическое состояние детектора (read-only)."""
        return {
            "initialized": self._initialized,
            "book_exists": self._path.exists(),
            "last_mtime": self._last_mtime,
            "last_hash": self._last_hash[:12] + "..." if self._last_hash else "",
        }
