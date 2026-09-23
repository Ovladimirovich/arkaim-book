"""World Explorer WebSocket — real-time прогресс исследования.

Реализует архитектура World Explorer: Этап 7 — WebSocket Real-time.

Отправляет события через WebSocket при каждом этапе pipeline:
1. exploration_started — начало исследования
2. exploration_progress — прогресс этапа (0-7)
3. exploration_complete — завершение с результатом
4. exploration_error — ошибка

Использует ConnectionManager из runtime/core/websocket.py.
"""

import logging
from typing import Optional

log = logging.getLogger("hermes.narrative.exploration_ws")


# События WebSocket
EXPLORATION_EVENTS = {
    "started": "exploration_started",
    "progress": "exploration_progress",
    "complete": "exploration_complete",
    "error": "exploration_error",
}

# Этапы pipeline
PIPELINE_STEPS = [
    "Проверка совместимости",
    "Генерация гипотез",
    "Моделирование сценариев",
    "Оценка влияния",
    "Обнаружение противоречий",
    "Расчёт изменений мира",
    "Оценка качества",
    "Ранжирование",
]


def _get_connection_manager():
    """Получить ConnectionManager из runtime. Ленивый импорт чтобы избежать циклических зависимостей."""
    try:
        from core.websocket import manager
        return manager
    except ImportError:
        log.debug("websocket_manager_not_available")
        return None


class ExplorationNotifier:
    """Отправляет real-time уведомления о прогрессе исследования через WebSocket."""

    def __init__(self):
        self._exploration_id: Optional[str] = None

    async def notify_started(
        self,
        exploration_id: str,
        prompt: str,
        epoch: Optional[str] = None,
        branch_count: int = 3,
    ):
        """Уведомить о начале исследования."""
        self._exploration_id = exploration_id
        await self._send(EXPLORATION_EVENTS["started"], {
            "exploration_id": exploration_id,
            "prompt": prompt[:200],
            "epoch": epoch,
            "branch_count": branch_count,
            "total_steps": len(PIPELINE_STEPS),
        })

    async def notify_progress(self, step: int, detail: str = ""):
        """Уведомить о прогрессе этапа."""
        if step < 0 or step >= len(PIPELINE_STEPS):
            return

        await self._send(EXPLORATION_EVENTS["progress"], {
            "exploration_id": self._exploration_id,
            "step": step,
            "total_steps": len(PIPELINE_STEPS),
            "step_name": PIPELINE_STEPS[step],
            "detail": detail,
            "percent": round(((step + 1) / len(PIPELINE_STEPS)) * 100),
        })

    async def notify_complete(
        self,
        result_summary: str = "",
        branch_count: int = 0,
        best_score: float = 0.0,
        duration_ms: float = 0.0,
    ):
        """Уведомить о завершении исследования."""
        await self._send(EXPLORATION_EVENTS["complete"], {
            "exploration_id": self._exploration_id,
            "summary": result_summary,
            "branch_count": branch_count,
            "best_score": best_score,
            "duration_ms": duration_ms,
        })

    async def notify_error(self, error: str):
        """Уведомить об ошибке."""
        await self._send(EXPLORATION_EVENTS["error"], {
            "exploration_id": self._exploration_id,
            "error": error,
        })

    async def _send(self, event: str, data: dict):
        """Отправить событие через ConnectionManager."""
        cm = _get_connection_manager()
        if cm:
            try:
                await cm.broadcast(event, data)
                log.debug("ws_sent event=%s step=%s", event, data.get("step", ""))
            except Exception as e:
                log.warning("ws_send_error event=%s error=%s", event, e)
        else:
            log.debug("ws_no_manager event=%s", event)


# Глобальный экземпляр — используется world_explorer.py
exploration_notifier = ExplorationNotifier()
