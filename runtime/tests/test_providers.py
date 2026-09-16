"""Tests for providers (GigaChat, OpenRouter, HF) and ProviderRegistry."""
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.providers.base import BaseProvider
from core.provider_registry import ProviderRegistry, _CircuitBreakerState


# ── BaseProvider ──────────────────────────────────────────────


class TestBaseProvider:
    def test_health_returns_unknown(self):
        p = BaseProvider()
        result = asyncio.run(p.health())
        assert result["status"] == "unknown"

    def test_chat_raises(self):
        p = BaseProvider()
        with pytest.raises(NotImplementedError):
            asyncio.run(p.chat([{"role": "user", "content": "hi"}]))

    def test_stream_raises(self):
        p = BaseProvider()
        with pytest.raises(NotImplementedError):
            asyncio.run(p.stream([{"role": "user", "content": "hi"}]))

    def test_close_is_noop(self):
        p = BaseProvider()
        asyncio.run(p.close())


# ── CircuitBreakerState ───────────────────────────────────────


class TestCircuitBreakerState:
    def test_initial_state_not_open(self):
        s = _CircuitBreakerState()
        assert not s.is_open()

    def test_record_failure_below_threshold(self):
        s = _CircuitBreakerState()
        opened = s.record_failure(threshold=3, cooldown_seconds=60)
        assert not opened
        assert not s.is_open()

    def test_record_failure_at_threshold(self):
        s = _CircuitBreakerState()
        for _ in range(2):
            s.record_failure(threshold=3, cooldown_seconds=60)
        opened = s.record_failure(threshold=3, cooldown_seconds=60)
        assert opened
        assert s.is_open()

    def test_record_success_resets(self):
        s = _CircuitBreakerState()
        s.record_failure(threshold=3, cooldown_seconds=60)
        s.record_failure(threshold=3, cooldown_seconds=60)
        s.record_success()
        assert not s.is_open()
        assert s.failure_count == 0

    def test_cooldown_expires(self):
        s = _CircuitBreakerState()
        s.cooldown_until = time.time() - 1  # expired
        assert not s.is_open()


# ── ProviderRegistry ──────────────────────────────────────────


class _DummyProvider(BaseProvider):
    async def chat(self, messages, context=None, trace_id="", xray_headers=None):
        return "dummy response"

    async def health(self):
        return {"status": "ok", "provider": "dummy"}


class _AnotherProvider(BaseProvider):
    async def chat(self, messages, context=None, trace_id="", xray_headers=None):
        return "another response"

    async def health(self):
        return {"status": "ok", "provider": "another"}


@pytest.fixture(autouse=True)
def reset_registry():
    """Save and restore ProviderRegistry before each test."""
    saved = (dict(ProviderRegistry._providers), ProviderRegistry._frozen, dict(ProviderRegistry._health_state))
    ProviderRegistry.reset()
    yield
    ProviderRegistry._providers, ProviderRegistry._frozen, ProviderRegistry._health_state = saved


class TestProviderRegistry:
    def test_register_and_get(self):
        ProviderRegistry.register("dummy", _DummyProvider)
        p = ProviderRegistry.get("dummy")
        assert isinstance(p, _DummyProvider)

    def test_get_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            ProviderRegistry.get("nonexistent")

    def test_is_registered(self):
        ProviderRegistry.register("dummy", _DummyProvider)
        assert ProviderRegistry.is_registered("dummy")
        assert not ProviderRegistry.is_registered("other")

    def test_freeze_prevents_registration(self):
        ProviderRegistry.register("dummy", _DummyProvider)
        ProviderRegistry.freeze()
        with pytest.raises(RuntimeError, match="frozen"):
            ProviderRegistry.register("another", _AnotherProvider)

    def test_all_returns_copy(self):
        ProviderRegistry.register("dummy", _DummyProvider)
        all_p = ProviderRegistry.all()
        assert "dummy" in all_p
        all_p["new"] = _AnotherProvider  # shouldn't affect registry
        assert not ProviderRegistry.is_registered("new")

    def test_chain(self):
        with patch("core.provider_registry.settings") as mock_settings:
            mock_settings.PROVIDER_CHAIN = ["gigachat", "openrouter"]
            ProviderRegistry.register("gigachat", _DummyProvider)
            ProviderRegistry.register("openrouter", _AnotherProvider)
            chain = ProviderRegistry.chain("gigachat")
            assert chain == ["gigachat", "openrouter"]

    def test_chain_with_unknown(self):
        with patch("core.provider_registry.settings") as mock_settings:
            mock_settings.PROVIDER_CHAIN = ["gigachat"]
            ProviderRegistry.register("gigachat", _DummyProvider)
            chain = ProviderRegistry.chain("unknown")
            assert "gigachat" in chain

    def test_health(self):
        ProviderRegistry.register("dummy", _DummyProvider)
        results = asyncio.run(ProviderRegistry.health())
        assert len(results) == 1
        assert results[0]["name"] == "dummy"
        assert results[0]["status"] == "ok"

    def test_report_failure_and_success(self):
        ProviderRegistry.register("dummy", _DummyProvider)
        with patch("core.provider_registry.settings") as mock_settings:
            mock_settings.PROVIDER_FAILURE_THRESHOLD = 3
            mock_settings.PROVIDER_COOLDOWN_SECONDS = 60

            ProviderRegistry.report_failure("dummy")
            assert ProviderRegistry.is_healthy("dummy")

            ProviderRegistry.report_failure("dummy")
            ProviderRegistry.report_failure("dummy")
            assert not ProviderRegistry.is_healthy("dummy")

            ProviderRegistry.report_success("dummy")
            assert ProviderRegistry.is_healthy("dummy")

    def test_chain_healthy(self):
        ProviderRegistry.register("dummy", _DummyProvider)
        ProviderRegistry.register("another", _AnotherProvider)
        with patch("core.provider_registry.settings") as mock_settings:
            mock_settings.PROVIDER_CHAIN = ["dummy", "another"]
            mock_settings.PROVIDER_FAILURE_THRESHOLD = 3
            mock_settings.PROVIDER_COOLDOWN_SECONDS = 60

            # Make "dummy" unhealthy
            ProviderRegistry.report_failure("dummy")
            ProviderRegistry.report_failure("dummy")
            ProviderRegistry.report_failure("dummy")

            healthy = ProviderRegistry.chain_healthy("dummy")
            assert "dummy" not in healthy
            assert "another" in healthy

    def test_select_provider(self):
        ProviderRegistry.register("dummy", _DummyProvider)
        ProviderRegistry.register("another", _AnotherProvider)
        with patch("core.provider_registry.settings") as mock_settings:
            mock_settings.PROVIDER_CHAIN = ["dummy"]
            selected = ProviderRegistry.select_provider("dummy")
            assert selected == "dummy"

    def test_select_provider_default(self):
        ProviderRegistry.register("dummy", _DummyProvider)
        with patch("core.provider_registry.settings.PROVIDER_CHAIN", ["dummy"]):
            selected = ProviderRegistry.select_provider()
            assert selected == "dummy"


# ── GigaChatProvider ──────────────────────────────────────────


class TestGigaChatProvider:
    @patch("core.providers.gigachat.settings")
    def test_init(self, mock_settings):
        mock_settings.GIGACHAT_VERIFY_SSL = True
        mock_settings.GIGACHAT_TOKEN = "test-token"
        from core.providers.gigachat import GigaChatProvider
        p = GigaChatProvider()
        assert p.verify is True
        asyncio.run(p.close())

    @patch("core.providers.gigachat.settings")
    def test_acquire_token_from_config(self, mock_settings):
        mock_settings.GIGACHAT_VERIFY_SSL = True
        mock_settings.GIGACHAT_CLIENT_ID = ""
        mock_settings.GIGACHAT_CLIENT_SECRET = ""
        mock_settings.GIGACHAT_TOKEN = "my-static-token"
        from core.providers.gigachat import GigaChatProvider
        p = GigaChatProvider()
        token = asyncio.run(p._acquire_token())
        assert token == "my-static-token"
        asyncio.run(p.close())

    @patch("core.providers.gigachat.settings")
    def test_acquire_token_no_credentials_raises(self, mock_settings):
        mock_settings.GIGACHAT_VERIFY_SSL = True
        mock_settings.GIGACHAT_CLIENT_ID = ""
        mock_settings.GIGACHAT_CLIENT_SECRET = ""
        mock_settings.GIGACHAT_TOKEN = ""
        from core.providers.gigachat import GigaChatProvider
        p = GigaChatProvider()
        with pytest.raises(RuntimeError, match="No GigaChat credentials"):
            asyncio.run(p._acquire_token())
        asyncio.run(p.close())


# ── OpenRouterProvider ────────────────────────────────────────


class TestOpenRouterProvider:
    @patch("core.providers.openrouter.settings")
    def test_init(self, mock_settings):
        mock_settings.OPENROUTER_API_KEY = "test-key"
        mock_settings.OPENROUTER_MODEL = "test-model"
        from core.providers.openrouter import OpenRouterProvider
        p = OpenRouterProvider()
        assert p.base_url == "https://openrouter.ai/api/v1"
        asyncio.run(p.close())

    @patch("core.providers.openrouter.settings")
    @patch("httpx.AsyncClient.get")
    def test_health(self, mock_get, mock_settings):
        mock_settings.OPENROUTER_API_KEY = "test-key"
        mock_settings.OPENROUTER_MODEL = "test-model"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        from core.providers.openrouter import OpenRouterProvider
        p = OpenRouterProvider()
        result = asyncio.run(p.health())
        assert result["status"] == "ok"
        asyncio.run(p.close())
