"""Telegram adapter stability: thin layer, no forbidden knowledge, error handling."""

import asyncio
import json

import httpx
import pytest

try:
    from integrations.telegram.adapter import TelegramAdapter, _exponential_backoff
    from integrations.telegram.config import TelegramConfig
    from integrations.telegram.normalize import normalize_update
    from integrations.telegram.formatter import split_message
    HAS_TELEGRAM_ADAPTER = True
except ImportError:
    HAS_TELEGRAM_ADAPTER = False

pytestmark = pytest.mark.skipif(not HAS_TELEGRAM_ADAPTER, reason="integrations.telegram module not found")


# ─── Normalize ──────────────────────────────────────────


class TestNormalize:
    """Normalize MUST produce correct NormalizedRequest from Telegram update."""

    def _update(self, text="hello", chat_id=123, user_id=456, update_id=1):
        return {
            "update_id": update_id,
            "message": {
                "message_id": 10,
                "from": {"id": user_id, "is_bot": False, "first_name": "Test"},
                "chat": {"id": chat_id, "type": "private"},
                "text": text,
            },
        }

    def test_basic_message(self):
        upd = self._update("hello", chat_id=999, user_id=888)
        result = normalize_update(upd)
        assert result is not None
        assert result["messages"] == [{"role": "user", "content": "hello"}]
        assert result["session_id"] == "tg:999"
        assert result["provider"] == ""
        assert result["metadata"]["user_id"] == "tg:888"
        assert result["metadata"]["chat_id"] == 999

    def test_empty_message(self):
        upd = self._update("", chat_id=1, user_id=2)
        result = normalize_update(upd)
        assert result is None or result["messages"] == []

    def test_no_message_field(self):
        upd = {"update_id": 1}
        result = normalize_update(upd)
        assert result is None

    def test_group_chat(self):
        upd = self._update("hi", chat_id=100, user_id=200)
        upd["message"]["chat"]["type"] = "group"
        result = normalize_update(upd)
        assert result["metadata"]["chat_id"] == 100


# ─── Formatter ──────────────────────────────────────────


class TestFormatter:
    """split_message MUST respect Telegram limits."""

    def test_short_message_not_split(self):
        result = split_message("Hello world")
        assert len(result) == 1
        assert result[0] == "Hello world"

    def test_long_message_split(self):
        long_text = "x" * 5000
        result = split_message(long_text)
        assert len(result) > 1
        for part in result:
            assert len(part) <= 4096

    def test_empty_message(self):
        result = split_message("")
        assert result == [""] or result == []


# ─── Exponential Backoff ────────────────────────────────


class TestBackoff:
    """_exponential_backoff MUST return increasing delays."""

    def test_backoff_increases(self):
        delays = [_exponential_backoff(i) for i in range(5)]
        for i in range(1, len(delays)):
            assert delays[i] >= delays[i - 1]

    def test_backoff_bounded(self):
        delays = [_exponential_backoff(i) for i in range(10)]
        for d in delays:
            assert d <= 60  # max 60 seconds
