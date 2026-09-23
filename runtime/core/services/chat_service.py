"""Сервис чата — валидация, оркестрация, структурированные ответы."""
from __future__ import annotations

import logging

from core.dto.requests import ChatRequest
from core.orchestrator import Orchestrator

log = logging.getLogger("hermes.chat.service")


class ChatService:
    """Тонкая обёртка над Orchestrator с входящей валидацией."""

    def __init__(self, orchestrator: Orchestrator):
        self._orchestrator = orchestrator

    async def chat(self, req: ChatRequest, user: dict) -> dict:
        """Обработать запрос чата. Возвращает структурированный ответ."""
        raw = {
            "messages": [{"role": m.role, "content": m.content} for m in req.messages],
            "metadata": {"session_id": req.session_id or "default"},
            "provider": req.provider,
            "model": req.model,
        }
        return await self._orchestrator.chat(raw, user)

    async def stream(self, req: ChatRequest, user: dict):
        """Стриминг ответа. Yield токенов."""
        raw = {
            "messages": [{"role": m.role, "content": m.content} for m in req.messages],
            "metadata": {"session_id": req.session_id or "default"},
            "provider": req.provider,
            "model": req.model,
        }
        async for token in self._orchestrator.stream(raw, user):
            yield token

    async def health(self) -> dict:
        providers = await self._orchestrator.provider_health()
        memory = await self._orchestrator.memory_health()
        return {
            "providers": providers,
            "memory": memory,
        }

    async def close(self):
        await self._orchestrator.close()
