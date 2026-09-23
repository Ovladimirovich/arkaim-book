"""
websocket — real-time уведомления для дашборда.

Через WebSocket приходят:
- Новые вопросы читателей
- Новые предложения Presence
- Статус сервисов
- Pulse-бит (каждые 5 минут)
- Краудфандинговые майлстоуны
"""
import json
import logging
from typing import Set, Optional

from fastapi import WebSocket, WebSocketDisconnect

log = logging.getLogger("hermes.websocket")


class ConnectionManager:
    """Управляет WebSocket-соединениями с поддержкой user_id."""

    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()
        self._user_connections: dict[str, Set[WebSocket]] = {}  # user_id -> connections

    async def connect(self, ws: WebSocket, user_id: str = "") -> None:
        await ws.accept()
        self._connections.add(ws)
        if user_id:
            if user_id not in self._user_connections:
                self._user_connections[user_id] = set()
            self._user_connections[user_id].add(ws)
        ws.state.user_id = user_id
        log.info("ws_connected user_id=%s total=%d", user_id or "anon", len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        user_id = getattr(ws.state, "user_id", "")
        self._connections.discard(ws)
        if user_id and user_id in self._user_connections:
            self._user_connections[user_id].discard(ws)
            if not self._user_connections[user_id]:
                del self._user_connections[user_id]
        log.info("ws_disconnected user_id=%s total=%d", user_id or "anon", len(self._connections))

    async def broadcast(self, event: str, data: dict) -> None:
        """Разослать событие всем подключённым клиентам."""
        message = json.dumps({"event": event, "data": data}, ensure_ascii=False)
        dead = set()
        for ws in self._connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.disconnect(ws)

    async def send_to_user(self, user_id: str, event: str, data: dict) -> None:
        """Отправить событие конкретному пользователю."""
        if user_id not in self._user_connections:
            return
        message = json.dumps({"event": event, "data": data}, ensure_ascii=False)
        dead = set()
        for ws in self._user_connections.get(user_id, set()):
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.disconnect(ws)

    @property
    def count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()


async def ws_endpoint(ws: WebSocket) -> None:
    """WebSocket эндпоинт для дашборда. Аутентификация через query param token."""
    # Попытка аутентификации из query params
    user_id = ""
    token = ws.query_params.get("token", "")
    if token:
        try:
            from auth.tokens import decode_access_token
            payload = decode_access_token(token)
            if payload:
                user_id = payload.sub
        except Exception as e:
            log.warning("caught_exception: %s", e)

    await manager.connect(ws, user_id)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)


# ── Фоновые уведомления ──────────────────────────

async def notify_pulse_beat(pulse_state: dict) -> None:
    """Разослать информацию о Pulse-бите."""
    await manager.broadcast("pulse_beat", pulse_state)


async def notify_new_suggestion(suggestion: dict) -> None:
    """Уведомить о новом предложении Presence."""
    await manager.broadcast("new_suggestion", suggestion)


async def notify_service_status(statuses: dict) -> None:
    """Уведомить об изменении статуса сервисов."""
    await manager.broadcast("service_status", statuses)


async def notify_new_question(question: str, topic: str, user_id: str = "") -> None:
    """Уведомить о новом вопросе читателя."""
    await manager.broadcast("new_question", {
        "question": question[:100],
        "topic": topic,
        "count": 0,
    })
    # Также отправить конкретному пользователю (если он онлайн)
    if user_id:
        await manager.send_to_user(user_id, "your_question_answered", {
            "question": question[:100],
            "topic": topic,
        })


async def notify_crowdfunding_milestone(alert: dict) -> None:
    """Уведомить о достижении майлстоуна краудфандинга."""
    await manager.broadcast("crowdfunding_milestone", alert)


async def notify_chat_response(user_id: str, question: str, answer: str) -> None:
    """Уведомить пользователя о ответе на его вопрос."""
    await manager.send_to_user(user_id, "chat_response", {
        "question": question[:100],
        "answer": answer[:200],
    })


__all__ = [
    "manager", "ws_endpoint",
    "notify_pulse_beat", "notify_new_suggestion",
    "notify_service_status", "notify_new_question",
    "notify_chat_response",
]
