"""Circuit breaker: failure threshold → cooldown, integration with orchestrator."""

import time

import httpx
import pytest

from core.provider_registry import ProviderRegistry
from core.providers.base import BaseProvider
from core.config import settings


class OkProvider(BaseProvider):
    async def chat(self, messages, context=None, trace_id="", xray_headers=None):
        return "ok"

    async def health(self):
        return {"status": "ok"}


class FailProvider(BaseProvider):
    async def chat(self, messages, context=None, trace_id="", xray_headers=None):
        raise httpx.ConnectError("fail")

    async def health(self):
        return {"status": "error"}


class TestCircuitBreakerCore:
    """Circuit breaker state management in ProviderRegistry."""

    @pytest.fixture(autouse=True)
    def _restore_registry(self):
        """Save and restore ProviderRegistry state."""
        saved = (dict(ProviderRegistry._providers), ProviderRegistry._frozen, dict(ProviderRegistry._health_state))
        yield
        ProviderRegistry._providers, ProviderRegistry._frozen, ProviderRegistry._health_state = saved

    def setup_method(self):
        ProviderRegistry._providers = {}
        ProviderRegistry._frozen = False
        ProviderRegistry._health_state = {}

    def test_initial_state_is_healthy(self):
        ProviderRegistry.register("p", OkProvider)
        assert ProviderRegistry.is_healthy("p") is True

    def test_threshold_opens_circuit(self):
        ProviderRegistry.register("p", OkProvider)
        for _ in range(settings.PROVIDER_FAILURE_THRESHOLD):
            ProviderRegistry.report_failure("p")
        assert ProviderRegistry.is_healthy("p") is False

    def test_below_threshold_stays_healthy(self):
        ProviderRegistry.register("p", OkProvider)
        ProviderRegistry.report_failure("p")
        ProviderRegistry.report_failure("p")
        assert ProviderRegistry.is_healthy("p") is True

    def test_success_resets_failure_count(self):
        ProviderRegistry.register("p", OkProvider)
        ProviderRegistry.report_failure("p")
        ProviderRegistry.report_success("p")
        assert ProviderRegistry.is_healthy("p") is True

    def test_success_after_cooldown_reopens(self):
        ProviderRegistry.register("p", OkProvider)
        for _ in range(settings.PROVIDER_FAILURE_THRESHOLD):
            ProviderRegistry.report_failure("p")
        assert ProviderRegistry.is_healthy("p") is False
        ProviderRegistry.report_success("p")
        assert ProviderRegistry.is_healthy("p") is True

    def test_chain_healthy_excludes_unhealthy(self):
        ProviderRegistry.register("a", OkProvider)
        ProviderRegistry.register("b", OkProvider)
        for _ in range(settings.PROVIDER_FAILURE_THRESHOLD):
            ProviderRegistry.report_failure("b")
        chain = ProviderRegistry.chain_healthy("a")
        assert "b" not in chain

    def test_chain_healthy_includes_requested(self):
        ProviderRegistry.register("a", OkProvider)
        chain = ProviderRegistry.chain_healthy("a")
        assert "a" in chain

    def test_chain_healthy_includes_all_when_all_healthy(self, monkeypatch):
        monkeypatch.setattr("core.config.settings.PROVIDER_CHAIN", ["a", "b"])
        ProviderRegistry.register("a", OkProvider)
        ProviderRegistry.register("b", OkProvider)
        chain = ProviderRegistry.chain_healthy("a")
        assert "a" in chain
        assert "b" in chain

    def test_unknown_provider_is_healthy(self):
        assert ProviderRegistry.is_healthy("nonexistent") is True

    def test_cooldown_expires(self):
        ProviderRegistry.register("p", OkProvider)
        for _ in range(settings.PROVIDER_FAILURE_THRESHOLD):
            ProviderRegistry.report_failure("p")
        assert ProviderRegistry.is_healthy("p") is False
        ProviderRegistry._health_state["p"].cooldown_until = time.time() - 1
        assert ProviderRegistry.is_healthy("p") is True


class TestCircuitBreakerIntegration:
    """Orchestrator reports failures/successes to circuit breaker."""

    def setup_method(self):
        ProviderRegistry._providers = {}
        ProviderRegistry._frozen = False
        ProviderRegistry._health_state = {}

    @pytest.mark.asyncio
    async def test_failure_triggers_report(self, monkeypatch):
        monkeypatch.setattr("core.config.settings.PROVIDER_CHAIN", ["fail"])
        ProviderRegistry.register("fail", FailProvider)
        from core.orchestrator import Orchestrator

        orch = Orchestrator()
        req = {"messages": [{"role": "user", "content": "hi"}], "provider": "fail", "metadata": {"session_id": "s1"}}
        await orch.chat(req, {"sub": "u1"})
        state = ProviderRegistry._health_state.get("fail")
        assert state is not None
        assert state.failure_count > 0

    @pytest.mark.asyncio
    async def test_success_resets_failures(self, monkeypatch):
        monkeypatch.setattr("core.config.settings.PROVIDER_CHAIN", ["ok"])
        ProviderRegistry.register("ok", OkProvider)
        ProviderRegistry._health_state["ok"].failure_count = 2
        ProviderRegistry._health_state["ok"].cooldown_until = 0.0
        from core.orchestrator import Orchestrator

        orch = Orchestrator()
        req = {"messages": [{"role": "user", "content": "hi"}], "provider": "ok", "metadata": {"session_id": "s1"}}
        await orch.chat(req, {"sub": "u1"})
        state = ProviderRegistry._health_state.get("ok")
        assert state is not None
        assert state.failure_count == 0

    @pytest.mark.asyncio
    async def test_unhealthy_provider_skipped_in_chain(self, monkeypatch):
        monkeypatch.setattr("core.config.settings.PROVIDER_CHAIN", ["bad", "good"])
        ProviderRegistry.register("bad", FailProvider)
        ProviderRegistry.register("good", OkProvider)
        for _ in range(settings.PROVIDER_FAILURE_THRESHOLD):
            ProviderRegistry.report_failure("bad")
        from core.orchestrator import Orchestrator

        orch = Orchestrator()
        req = {"messages": [{"role": "user", "content": "hi"}], "provider": "bad", "metadata": {"session_id": "s1"}}
        result = await orch.chat(req, {"sub": "u1"})
        assert "error" not in result
        assert result["choices"][0]["message"]["content"] == "ok"
