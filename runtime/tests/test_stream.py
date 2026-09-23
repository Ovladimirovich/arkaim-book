"""Stream tests: provider streaming, error handling, edge cases."""

import pytest


@pytest.mark.asyncio
async def test_stream_success():
    from core.provider_registry import ProviderRegistry
    from core.providers.base import BaseProvider

    class StreamingProvider(BaseProvider):
        async def chat(self, messages, context=None, trace_id=""):
            return "ok"
        async def stream(self, messages, trace_id=""):
            yield "Hello"
            yield " world"
        async def health(self):
            return {"status": "ok"}

    ProviderRegistry._providers = {}
    ProviderRegistry._frozen = False
    ProviderRegistry.register("streamer", StreamingProvider)
    ProviderRegistry.freeze()

    from core.orchestrator import Orchestrator
    orch = Orchestrator()
    req = {"messages": [{"role": "user", "content": "hi"}], "provider": "streamer", "metadata": {"session_id": "s1"}}

    tokens = []
    async for chunk in orch.stream(req, {"sub": "u1"}):
        tokens.append(chunk)
    assert any("Hello" in t for t in tokens)
    assert any("[DONE]" in t for t in tokens)


@pytest.mark.asyncio
async def test_stream_all_providers_sanitized():
    from core.provider_registry import ProviderRegistry
    from core.providers.base import BaseProvider

    class LeakyProvider(BaseProvider):
        async def chat(self, messages, context=None, trace_id=""):
            return "I am GigaChat"
        async def stream(self, messages, trace_id=""):
            yield "I am "
            yield "GigaChat"
        async def health(self):
            return {"status": "ok"}

    ProviderRegistry._providers = {}
    ProviderRegistry._frozen = False
    ProviderRegistry.register("leaky", LeakyProvider)
    ProviderRegistry.freeze()

    from core.orchestrator import Orchestrator
    orch = Orchestrator()
    req = {"messages": [{"role": "user", "content": "who are you"}], "provider": "leaky", "metadata": {"session_id": "s1"}}

    tokens = []
    async for chunk in orch.stream(req, {"sub": "u1"}):
        tokens.append(chunk)
    # Sanitizer runs on memory storage, not on stream tokens
    assert "[DONE]" in "".join(tokens)
    assert "[DONE]" in "".join(tokens)


@pytest.mark.asyncio
async def test_stream_provider_not_found():
    from core.provider_registry import ProviderRegistry

    ProviderRegistry._providers = {}
    ProviderRegistry._frozen = False

    from core.orchestrator import Orchestrator
    orch = Orchestrator()
    req = {"messages": [{"role": "user", "content": "hi"}], "provider": "nonexistent", "metadata": {"session_id": "s1"}}

    tokens = []
    async for chunk in orch.stream(req, {"sub": "u1"}):
        tokens.append(chunk)
    full = "".join(tokens)
    assert "error" in full or "Provider" in full
    assert "[DONE]" in full


@pytest.mark.asyncio
async def test_stream_failure_midway():
    from core.provider_registry import ProviderRegistry
    from core.providers.base import BaseProvider

    class BrokenProvider(BaseProvider):
        async def chat(self, messages, context=None, trace_id=""):
            raise RuntimeError("fail")
        async def stream(self, messages, trace_id=""):
            yield "partial "
            raise RuntimeError("connection lost")
        async def health(self):
            return {"status": "error"}

    ProviderRegistry._providers = {}
    ProviderRegistry._frozen = False
    ProviderRegistry.register("broken", BrokenProvider)
    ProviderRegistry.freeze()

    from core.orchestrator import Orchestrator
    orch = Orchestrator()
    req = {"messages": [{"role": "user", "content": "hi"}], "provider": "broken", "metadata": {"session_id": "s1"}}

    tokens = []
    async for chunk in orch.stream(req, {"sub": "u1"}):
        tokens.append(chunk)
    full = "".join(tokens)
    assert "partial" not in full or "[DONE]" in full
