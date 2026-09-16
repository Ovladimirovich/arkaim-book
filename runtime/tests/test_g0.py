"""G0 tests: Model Discovery, OpenAI-compatible API, Provider Health, Rate Limiting."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import time

from core.providers.base import BaseProvider
from core.provider_registry import ProviderRegistry
from core.dto.openai import OpenAIChatCompletionRequest, OpenAIModel


# ── BaseProvider.list_models ────────────────────────────────────────


class TestBaseProviderListModels:
    def test_base_returns_empty_list(self):
        p = BaseProvider()
        import asyncio
        result = asyncio.run(p.list_models())
        assert result == []


# ── ProviderRegistry.list_all_models ───────────────────────────────


class DummyProvider(BaseProvider):
    async def chat(self, messages, context=None, trace_id="", xray_headers=None):
        return "dummy"

    async def health(self):
        return {"status": "ok", "provider": "dummy"}

    async def list_models(self):
        return [{"id": "dummy-v1", "object": "model", "owned_by": "test"}]


class TestProviderRegistryListModels:
    @pytest.fixture(autouse=True)
    def _restore_registry(self):
        saved = (dict(ProviderRegistry._providers), ProviderRegistry._frozen, dict(ProviderRegistry._health_state))
        yield
        ProviderRegistry._providers, ProviderRegistry._frozen, ProviderRegistry._health_state = saved

    def setup_method(self):
        ProviderRegistry._providers = {}
        ProviderRegistry._frozen = False

    @pytest.mark.asyncio
    async def test_list_all_models_aggregates(self):
        ProviderRegistry.register("dummy", DummyProvider)
        models = await ProviderRegistry.list_all_models()
        assert len(models) == 1
        assert models[0]["id"] == "dummy/dummy-v1"
        assert models[0]["provider"] == "dummy"

    @pytest.mark.asyncio
    async def test_list_all_models_empty_when_no_providers(self):
        models = await ProviderRegistry.list_all_models()
        assert models == []

    @pytest.mark.asyncio
    async def test_list_all_models_handles_error(self):
        class FailingProvider(BaseProvider):
            async def chat(self, messages, **kwargs):
                return "ok"
            async def list_models(self):
                raise RuntimeError("discovery_failed")

        ProviderRegistry.register("failing", FailingProvider)
        models = await ProviderRegistry.list_all_models()
        assert len(models) == 1
        assert models[0]["status"] == "unavailable"


# ── OpenAI Chat Completions ────────────────────────────────────────


class TestOpenAIChatCompletions:
    def test_request_validation_accepts_valid_fields(self):
        req = OpenAIChatCompletionRequest(model="gigachat", messages=[{"role": "user", "content": "hi"}])
        assert req.model == "gigachat"
        assert len(req.messages) == 1

    def test_request_validation_rejects_invalid_role(self):
        with pytest.raises(Exception):  # Pydantic validation
            OpenAIChatCompletionRequest(model="gigachat", messages=[{"role": "invalid", "content": "hi"}])


# ── Per-provider Rate Limiter ──────────────────────────────────────


class TestProviderRateLimiter:
    def test_provider_rate_limit_enforced(self):
        from core.main import check_provider_rate_limit, get_provider_rate_limit_info, _provider_rate_limits
        # Clear state
        _provider_rate_limits.clear()

        # Use low limit for test
        with patch("core.main.PROVIDER_RATE_LIMIT_MAX_REQUESTS", 2):
            assert check_provider_rate_limit("gigachat") is True
            assert check_provider_rate_limit("gigachat") is True
            assert check_provider_rate_limit("gigachat") is False  # Should be blocked

    def test_provider_rate_limit_independent_per_provider(self):
        from core.main import check_provider_rate_limit, _provider_rate_limits
        # Clear state
        _provider_rate_limits.clear()

        # Use low limit for test
        with patch("core.main.PROVIDER_RATE_LIMIT_MAX_REQUESTS", 1):
            # Exhaust limit for gigachat
            assert check_provider_rate_limit("gigachat") is True
            assert check_provider_rate_limit("gigachat") is False

            # OpenRouter should still be allowed
            assert check_provider_rate_limit("openrouter") is True

    def test_provider_rate_limit_info(self):
        from core.main import get_provider_rate_limit_info, _provider_rate_limits
        _provider_rate_limits.clear()
        
        info = get_provider_rate_limit_info("gigachat")
        assert info["rate"] > 0
        assert info["remaining"] >= 0


# ── Model Discovery ────────────────────────────────────────────────


class TestModelDiscovery:
    @pytest.mark.asyncio
    async def test_gigachat_list_models_default(self):
        from core.providers.gigachat import GigaChatProvider
        with patch.object(GigaChatProvider, '_acquire_token', new_callable=AsyncMock) as mock_token:
            mock_token.return_value = "test-token"
            with patch("httpx.AsyncClient.get") as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"data": [{"id": "GigaChat-Pro", "context_length": 32000}]}
                mock_get.return_value = mock_response

                provider = GigaChatProvider()
                models = await provider.list_models()
                assert len(models) >= 1
                assert any("GigaChat-Pro" in m.get("id", "") for m in models)
                await provider.close()

    @pytest.mark.asyncio
    async def test_openrouter_list_models_403(self):
        from core.providers.openrouter import OpenRouterProvider
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_get.return_value = mock_response

            provider = OpenRouterProvider()
            models = await provider.list_models()
            assert len(models) >= 1
            assert models[0].get("status") in ("unavailable", "unknown")
            await provider.close()

    @pytest.mark.asyncio
    async def test_openrouter_list_models_success(self):
        from core.providers.openrouter import OpenRouterProvider
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": "openai/gpt-4", "owned_by": "openai"}]}
            mock_get.return_value = mock_response

            provider = OpenRouterProvider()
            models = await provider.list_models()
            assert len(models) >= 1
            await provider.close()
