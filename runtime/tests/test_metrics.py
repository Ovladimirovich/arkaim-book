"""X-RAY Lite: metrics counters, snapshot, /metrics endpoint."""

import pytest

from observability.metrics import metrics, Metrics


class TestMetricsCore:
    def setup_method(self):
        metrics.reset()

    def test_increment_and_snapshot(self):
        metrics.increment("chat_ok")
        assert metrics.snapshot() == {"chat_ok": 1}

    def test_increment_multiple(self):
        metrics.increment("chat_ok", count=5)
        assert metrics.snapshot()["chat_ok"] == 5

    def test_snapshot_returns_copy(self):
        metrics.increment("test")
        snap = metrics.snapshot()
        snap["hacked"] = 1
        assert "hacked" not in metrics.snapshot()

    def test_multiple_counters(self):
        metrics.increment("chat_ok")
        metrics.increment("chat_failed")
        metrics.increment("identity_repair", count=2)
        snap = metrics.snapshot()
        assert snap["chat_ok"] == 1
        assert snap["chat_failed"] == 1
        assert snap["identity_repair"] == 2

    def test_reset_clears_all(self):
        metrics.increment("chat_ok")
        metrics.reset()
        assert metrics.snapshot() == {}

    def test_unknown_counter_is_zero(self):
        snap = metrics.snapshot()
        assert "nonexistent" not in snap

    def test_isolation_between_instances(self):
        m1 = Metrics()
        m2 = Metrics()
        m1.increment("a")
        m2.increment("b")
        assert "b" not in m1.snapshot()
        assert "a" not in m2.snapshot()

    def test_metrics_module_is_singleton(self):
        from observability import metrics as metrics_module
        from observability.metrics import metrics as direct

        assert metrics_module.metrics is direct


class TestMetricsIntegration:
    """Verify metrics are wired into orchestrator and identity sanitizer."""

    @pytest.fixture(autouse=True)
    def _restore_registry(self):
        """Save and restore ProviderRegistry state."""
        from core.provider_registry import ProviderRegistry

        saved = (dict(ProviderRegistry._providers), ProviderRegistry._frozen, dict(ProviderRegistry._health_state))
        yield
        ProviderRegistry._providers, ProviderRegistry._frozen, ProviderRegistry._health_state = saved

    def setup_method(self):
        from core.identity.sanitizer import sanitize_response
        from core.provider_registry import ProviderRegistry

        ProviderRegistry._providers = {}
        ProviderRegistry._frozen = False
        metrics.reset()
        self.sanitize = sanitize_response

    def test_chat_ok_incremented_on_success(self):
        from core.provider_registry import ProviderRegistry
        from core.providers.base import BaseProvider

        class OkProvider(BaseProvider):
            async def chat(self, messages, context=None, trace_id="", xray_headers=None):
                return "Hello"

            async def health(self):
                return {"status": "ok"}

        ProviderRegistry.register("ok", OkProvider)
        ProviderRegistry.freeze()

        from core.orchestrator import Orchestrator

        orch = Orchestrator()
        req = {"messages": [{"role": "user", "content": "hi"}], "provider": "ok", "metadata": {"session_id": "s1"}}

        import asyncio

        asyncio.run(orch.chat(req, {"sub": "u1"}))

        snap = metrics.snapshot()
        assert snap.get("chat_started") == 1
        assert snap.get("chat_ok") == 1
        assert snap.get("provider_selected") == 1

    def test_chat_failed_on_all_providers_down(self):
        from core.provider_registry import ProviderRegistry
        from core.providers.base import BaseProvider
        import httpx

        class FailProvider(BaseProvider):
            async def chat(self, messages, context=None, trace_id="", xray_headers=None):
                raise httpx.ConnectError("down")

            async def health(self):
                return {"status": "error"}

        ProviderRegistry.register("fail", FailProvider)
        ProviderRegistry.freeze()

        from core.orchestrator import Orchestrator

        orch = Orchestrator()

        import asyncio

        req = {"messages": [{"role": "user", "content": "hi"}], "provider": "fail", "metadata": {"session_id": "s1"}}
        asyncio.run(orch.chat(req, {"sub": "u1"}))

        snap = metrics.snapshot()
        assert snap.get("chat_started") == 1
        assert snap.get("provider_failed") == 1
        assert snap.get("chat_failed") == 1

    def test_identity_repair_increments(self):
        result = self.sanitize("I am GigaChat, a language model.", provider="gigachat")
        assert "GigaChat" not in result
        snap = metrics.snapshot()
        assert snap.get("identity_repair", 0) > 0

    def test_identity_repair_not_incremented_on_clean(self):
        self.sanitize("Hermes can help you.", provider="gigachat")
        assert "identity_repair" not in metrics.snapshot()


class TestMetricsEndpoint:
    """/metrics endpoint returns proper snapshot."""

    def test_metrics_endpoint_exists(self):
        from core.main import app

        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/metrics" in routes
