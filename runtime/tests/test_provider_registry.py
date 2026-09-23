"""Provider Registry tests: immutability, chain, isolation."""

import pytest
from core.provider_registry import ProviderRegistry
from core.providers.base import BaseProvider


class DummyProvider(BaseProvider):
    async def chat(self, messages, context=None, trace_id=""):
        return "dummy"

    async def health(self):
        return {"status": "ok", "provider": "dummy"}


class TestProviderRegistry:

    @pytest.fixture(autouse=True)
    def _restore_registry(self):
        """Save and restore ProviderRegistry state."""
        saved = (dict(ProviderRegistry._providers), ProviderRegistry._frozen, dict(ProviderRegistry._health_state))
        yield
        ProviderRegistry._providers, ProviderRegistry._frozen, ProviderRegistry._health_state = saved

    def setup_method(self):
        ProviderRegistry._providers = {}
        ProviderRegistry._frozen = False

    def test_register_and_get(self):
        ProviderRegistry.register("dummy", DummyProvider)
        provider = ProviderRegistry.get("dummy")
        assert isinstance(provider, DummyProvider)

    def test_get_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            ProviderRegistry.get("nonexistent")

    def test_freeze_prevents_registration(self):
        ProviderRegistry.register("dummy", DummyProvider)
        ProviderRegistry.freeze()
        with pytest.raises(RuntimeError, match="frozen"):
            ProviderRegistry.register("another", DummyProvider)

    def test_is_registered(self):
        ProviderRegistry.register("dummy", DummyProvider)
        assert ProviderRegistry.is_registered("dummy") is True
        assert ProviderRegistry.is_registered("nonexistent") is False

    def test_all_returns_copy(self):
        ProviderRegistry.register("dummy", DummyProvider)
        all_providers = ProviderRegistry.all()
        assert "dummy" in all_providers
        all_providers["hacked"] = DummyProvider
        assert "hacked" not in ProviderRegistry._providers

    @pytest.mark.asyncio
    async def test_health_returns_list(self):
        ProviderRegistry.register("dummy", DummyProvider)
        results = await ProviderRegistry.health()
        assert len(results) == 1
        assert results[0]["name"] == "dummy"
        assert results[0]["status"] == "ok"
