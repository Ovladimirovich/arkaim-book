"""Provider reliability: retry chain, fallback, identity leak integration."""

import asyncio
import ssl

import httpx
import pytest

from core.retry import ErrorType, classify_error, with_retry
from core.provider_registry import ProviderRegistry
from core.providers.base import BaseProvider
from core.orchestrator import Orchestrator
from core.identity.sanitizer import sanitize_response


#
# ─── Mock providers ─────────────────────────────────────────────────────
#

class FailingProvider(BaseProvider):
    def __init__(self, fail_count: int = 1, error: Exception = httpx.HTTPStatusError("fail", request=None, response=httpx.Response(502))):
        self._fail_count = fail_count
        self._error = error
        self._call_count = 0

    async def chat(self, messages, context=None, trace_id="", **kwargs):
        self._call_count += 1
        if self._call_count <= self._fail_count:
            raise self._error
        return "fallback-success-response"

    async def health(self):
        return {"status": "ok"}


class LeakyProvider(BaseProvider):
    async def chat(self, messages, context=None, trace_id="", **kwargs):
        return "I am GigaChat, a language model. Here is some useful info."

    async def health(self):
        return {"status": "ok"}


class CleanProvider(BaseProvider):
    async def chat(self, messages, context=None, trace_id="", **kwargs):
        return "Hermes can help you with your request."

    async def health(self):
        return {"status": "ok"}


#
# ─── Error classification tests ─────────────────────────────────────────
#

class TestErrorClassification:
    """Verify every error type maps to the correct ErrorType."""

    @pytest.mark.parametrize("status,expected", [
        (401, ErrorType.AUTH),
        (403, ErrorType.AUTH),
        (429, ErrorType.RATE_LIMIT),
        (502, ErrorType.PROVIDER_UNAVAILABLE),
        (503, ErrorType.PROVIDER_UNAVAILABLE),
        (504, ErrorType.PROVIDER_UNAVAILABLE),
        (200, ErrorType.UNKNOWN),
    ])
    def test_classify_by_status_code(self, status, expected):
        exc = httpx.HTTPStatusError("err", request=None, response=httpx.Response(status))
        assert classify_error(exc, status) == expected

    def test_classify_ssl_error(self):
        exc = ssl.SSLError()
        assert classify_error(exc) == ErrorType.SSL

    def test_classify_timeout(self):
        exc = httpx.TimeoutException("timeout")
        assert classify_error(exc) == ErrorType.TIMEOUT

    def test_classify_asyncio_timeout(self):
        exc = asyncio.TimeoutError()
        assert classify_error(exc) == ErrorType.TIMEOUT

    def test_classify_request_error(self):
        exc = httpx.RequestError("conn failed")
        assert classify_error(exc) == ErrorType.PROVIDER_UNAVAILABLE

    def test_classify_unknown(self):
        exc = ValueError("weird")
        assert classify_error(exc) == ErrorType.UNKNOWN


#
# ─── Retry function tests ──────────────────────────────────────────────
#

class TestWithRetry:
    """Verify retry behaviour: success, retry-then-succeed, abort."""

    @pytest.mark.asyncio
    async def test_success_first_try(self):
        async def ok_fn():
            return "ok"
        result = await with_retry(ok_fn, context="test")
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_retry_then_succeed(self):
        fn = FailingProvider(fail_count=2, error=httpx.TimeoutException("timeout"))
        result = await with_retry(fn.chat, context="test_retry", messages=[{"role": "user", "content": "hi"}])
        assert result == "fallback-success-response"
        assert fn._call_count == 3

    @pytest.mark.asyncio
    async def test_abort_on_auth(self):
        fn = FailingProvider(fail_count=10, error=httpx.HTTPStatusError("auth", request=None, response=httpx.Response(401)))
        with pytest.raises(httpx.HTTPStatusError):
            await with_retry(fn.chat, context="test_auth", messages=[])
        assert fn._call_count == 1

    @pytest.mark.asyncio
    async def test_abort_on_ssl(self):
        fn = FailingProvider(fail_count=10, error=ssl.SSLError())
        with pytest.raises(ssl.SSLError):
            await with_retry(fn.chat, context="test_ssl", messages=[])
        assert fn._call_count == 1

    @pytest.mark.asyncio
    async def test_exhaust_retries(self):
        fn = FailingProvider(fail_count=10, error=httpx.TimeoutException("timeout"))
        with pytest.raises(httpx.TimeoutException):
            await with_retry(fn.chat, context="test_exhaust", messages=[])
        assert fn._call_count == 3


#
# ─── Provider fallback chain tests ─────────────────────────────────────
#

class TestProviderChain:
    """Orchestrator falls through providers correctly."""

    @pytest.fixture(autouse=True)
    def _restore_registry(self):
        """Save and restore ProviderRegistry state."""
        saved = (dict(ProviderRegistry._providers), ProviderRegistry._frozen, dict(ProviderRegistry._health_state))
        yield
        ProviderRegistry._providers, ProviderRegistry._frozen, ProviderRegistry._health_state = saved

    def setup_method(self):
        ProviderRegistry._providers = {}
        ProviderRegistry._frozen = False

    @pytest.mark.asyncio
    async def test_primary_succeeds(self):
        ProviderRegistry.register("primary", CleanProvider)
        ProviderRegistry.register("secondary", CleanProvider)
        ProviderRegistry.freeze()
        orch = Orchestrator()
        req = {"messages": [{"role": "user", "content": "hello"}], "provider": "primary", "metadata": {"session_id": "s1"}}
        result = await orch.chat(req, {"sub": "user1"})
        assert "error" not in result
        assert result["choices"][0]["message"]["content"] == "Hermes can help you with your request."

    @pytest.mark.asyncio
    async def test_fallback_to_secondary(self, monkeypatch):
        monkeypatch.setattr("core.config.settings.PROVIDER_CHAIN", ["gigachat", "openrouter"])
        ProviderRegistry.register("gigachat", lambda: FailingProvider(fail_count=1, error=httpx.HTTPStatusError("fail", request=None, response=httpx.Response(502))))
        ProviderRegistry.register("openrouter", CleanProvider)
        ProviderRegistry.freeze()
        orch = Orchestrator()
        req = {"messages": [{"role": "user", "content": "hello"}], "provider": "gigachat", "metadata": {"session_id": "s1"}}
        result = await orch.chat(req, {"sub": "user1"})
        assert "error" not in result
        assert result["choices"][0]["message"]["content"] == "Hermes can help you with your request."

    @pytest.mark.asyncio
    async def test_all_providers_fail(self):
        ProviderRegistry.register("p1", lambda: FailingProvider(fail_count=10, error=httpx.TimeoutException("timeout")))
        ProviderRegistry.register("p2", lambda: FailingProvider(fail_count=10, error=httpx.TimeoutException("timeout")))
        ProviderRegistry.freeze()
        orch = Orchestrator()
        req = {"messages": [{"role": "user", "content": "hello"}], "provider": "p1", "metadata": {"session_id": "s1"}}
        result = await orch.chat(req, {"sub": "user1"})
        assert "error" in result
        assert "All providers failed" in result["error"]


#
# ─── Identity leak integration tests ──────────────────────────────────
#

class TestIdentityLeakIntegration:
    """Full pipeline: provider returns leak → orchestrator sanitizes → clean response."""

    @pytest.fixture(autouse=True)
    def _restore_registry(self):
        """Save and restore ProviderRegistry state."""
        saved = (dict(ProviderRegistry._providers), ProviderRegistry._frozen, dict(ProviderRegistry._health_state))
        yield
        ProviderRegistry._providers, ProviderRegistry._frozen, ProviderRegistry._health_state = saved

    def setup_method(self):
        ProviderRegistry._providers = {}
        ProviderRegistry._frozen = False

    @pytest.mark.asyncio
    async def test_leak_is_sanitized_in_chat_response(self):
        ProviderRegistry.register("leaky", LeakyProvider)
        ProviderRegistry.freeze()
        orch = Orchestrator()
        req = {"messages": [{"role": "user", "content": "who are you?"}], "provider": "leaky", "metadata": {"session_id": "s1"}}
        result = await orch.chat(req, {"sub": "user1"})
        content = result["choices"][0]["message"]["content"]
        assert "I am GigaChat" not in content
        assert "language model" not in content
        assert "useful info" in content

    @pytest.mark.asyncio
    async def test_clean_provider_passes_through(self):
        ProviderRegistry.register("clean", CleanProvider)
        ProviderRegistry.freeze()
        orch = Orchestrator()
        req = {"messages": [{"role": "user", "content": "help"}], "provider": "clean", "metadata": {"session_id": "s1"}}
        result = await orch.chat(req, {"sub": "user1"})
        content = result["choices"][0]["message"]["content"]
        assert content == "Hermes can help you with your request."


#
# ─── Sanitizer standalone tests ────────────────────────────────────────
#

class TestSanitizerEdgeCases:
    """Verify identity sanitizer handles edge cases across providers."""

    @pytest.mark.parametrize("provider_name", ["gigachat", "openrouter"])
    def test_all_providers_are_sanitized(self, provider_name):
        text = "I am a language model and I can assist you."
        result = sanitize_response(text, provider=provider_name)
        assert "language model" not in result

    def test_no_false_positives_on_clean_text(self):
        texts = [
            "Hermes can help with ceilings",
            "I use GigaChat as my cognitive provider",
            "The measurement is free",
        ]
        for t in texts:
            assert sanitize_response(t) == t
