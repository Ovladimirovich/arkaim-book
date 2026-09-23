"""EventLogger для обратной совместимости.

В кодовой базе ранее предполагался модуль `core_memory.logger`.
В репозитории такого пакета нет, поэтому тесты падали на импорте.

Этот модуль предоставляет минимальную реализацию `EventLogger`,
достаточную для использования в других частях проекта.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


logger = logging.getLogger("hermes.event_logger")


@dataclass
class EventLogger:
    """Простой логгер событий.

    Реализация преднамеренно минимальная: пишет событие в логгер.
    """

    sink: Optional[Any] = None

    def log_event(self, event: Dict[str, Any]) -> None:
        payload = dict(event)
        payload.setdefault("timestamp", datetime.now(tz=timezone.utc).isoformat())

        if self.sink is not None:
            try:
                self.sink(payload)
                return
            except Exception:
                # fallback to logging
                logger.exception("EventLogger sink failed")

        logger.info("%s", json.dumps(payload, ensure_ascii=False))

