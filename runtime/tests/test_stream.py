"""Stream tests: provider streaming, error handling, edge cases."""

import json

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
    metadata_index = next(i for i, token in enumerate(tokens) if '"related_entities"' in token)
    done_index = next(i for i, token in enumerate(tokens) if "[DONE]" in token)
    assert metadata_index < done_index
    metadata = json.loads(tokens[metadata_index].removeprefix("data: ").strip())
    assert metadata == {"related_entities": []}


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


# ═══════════════════════════════════════════════════════════════
# B3: provenance frame in SSE — real SkillResult.metadata only
# ═══════════════════════════════════════════════════════════════


def _register_streamer(name: str = "streamer") -> None:
    from core.provider_registry import ProviderRegistry
    from core.providers.base import BaseProvider

    class StreamingProvider(BaseProvider):
        async def chat(self, messages, context=None, trace_id=""):
            return "ok"
        async def stream(self, messages, trace_id=""):
            yield "Answer "
            yield "text"
        async def health(self):
            return {"status": "ok"}

    ProviderRegistry._providers = {}
    ProviderRegistry._frozen = False
    ProviderRegistry.register(name, StreamingProvider)
    ProviderRegistry.freeze()


class _FakeSkill:
    """Minimal skill double with controllable SkillResult."""

    def __init__(self, name: str, result) -> None:
        self.name = name
        self.priority = 0
        self._result = result

    async def execute(self, ctx):
        return self._result

    async def post_process(self, response, ctx):
        return response


def _provenance_frames(tokens: list[str]) -> list[dict]:
    """Parse SSE frames that carry provenance keys (not text/related_entities)."""
    frames = []
    for token in tokens:
        if not token.startswith("data: ") or "[DONE]" in token:
            continue
        try:
            data = json.loads(token.removeprefix("data: ").strip())
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and any(k in data for k in ("source", "pulse_confidence", "llm_used")):
            frames.append(data)
    return frames


@pytest.mark.asyncio
async def test_stream_direct_skill_emits_real_provenance():
    """Direct skill answer: final frame carries the skill's real metadata."""
    _register_streamer()
    from core.orchestrator import Orchestrator
    from skills.base import SkillResult

    orch = Orchestrator()
    orch.skills = [_FakeSkill("book", SkillResult(
        handled=True,
        response="Ответ из книги",
        metadata={"source": "knowledge:character", "llm_used": False, "confidence": 0.9, "routing": "direct"},
    ))]
    req = {"messages": [{"role": "user", "content": "Кто такой Велик?"}],
           "provider": "streamer", "metadata": {"session_id": "s1"}}

    tokens = [chunk async for chunk in orch.stream(req, {"sub": "u1"})]
    frames = _provenance_frames(tokens)
    assert len(frames) == 1
    # Маппинг реальных полей скилла на имена AskAnswer — без выдуманных значений
    assert frames[0]["source"] == "knowledge:character"
    assert frames[0]["pulse_confidence"] == 0.9
    assert frames[0]["llm_used"] is False
    # Провенанс — финальное событие перед [DONE]
    done_index = next(i for i, t in enumerate(tokens) if "[DONE]" in t)
    prov_index = next(i for i, t in enumerate(tokens) if t.startswith("data: ") and '"source"' in t)
    assert prov_index < done_index


@pytest.mark.asyncio
async def test_stream_llm_assisted_emits_real_provenance():
    """LLM-assisted path: provenance comes from skill metadata, before [DONE]."""
    _register_streamer()
    from core.orchestrator import Orchestrator
    from skills.base import SkillResult

    orch = Orchestrator()
    orch.skills = [_FakeSkill("book", SkillResult(
        handled=True,
        response="Ответ из книги",
        system_prompt="Перефразируй ответ",
        metadata={"source": "pulse", "llm_used": True, "confidence": 0.4, "routing": "llm_assisted"},
    ))]
    req = {"messages": [{"role": "user", "content": "Кто такой Велик?"}],
           "provider": "streamer", "metadata": {"session_id": "s1"}}

    tokens = [chunk async for chunk in orch.stream(req, {"sub": "u1"})]
    frames = _provenance_frames(tokens)
    assert len(frames) == 1
    assert frames[0] == {"source": "pulse", "pulse_confidence": 0.4, "llm_used": True}
    done_index = next(i for i, t in enumerate(tokens) if "[DONE]" in t)
    prov_index = next(i for i, t in enumerate(tokens) if '"pulse_confidence"' in t)
    assert prov_index < done_index


@pytest.mark.asyncio
async def test_stream_without_skill_metadata_emits_no_provenance():
    """No skill metadata → no provenance frame: values must never be invented."""
    _register_streamer()
    from core.orchestrator import Orchestrator

    orch = Orchestrator()
    orch.skills = []  # обычный LLM-путь без провенанса
    req = {"messages": [{"role": "user", "content": "hi"}],
           "provider": "streamer", "metadata": {"session_id": "s1"}}

    tokens = [chunk async for chunk in orch.stream(req, {"sub": "u1"})]
    assert _provenance_frames(tokens) == []
    assert any("[DONE]" in t for t in tokens)


@pytest.mark.asyncio
async def test_stream_skill_metadata_partially_omits_missing_fields():
    """Fields the skill did not send are omitted, not defaulted."""
    _register_streamer()
    from core.orchestrator import Orchestrator
    from skills.base import SkillResult

    orch = Orchestrator()
    orch.skills = [_FakeSkill("book", SkillResult(
        handled=True,
        response="Ответ",
        metadata={"routing": "direct"},  # без source/confidence/llm_used
    ))]
    req = {"messages": [{"role": "user", "content": "Кто такой Велик?"}],
           "provider": "streamer", "metadata": {"session_id": "s1"}}

    tokens = [chunk async for chunk in orch.stream(req, {"sub": "u1"})]
    assert _provenance_frames(tokens) == []
