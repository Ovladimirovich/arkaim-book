import time

import httpx

from core.config import settings
from core.logging import log
from core.retry import with_retry
from core.providers.base import BaseProvider
from aethon.xray import Event, emit, EventKind, ComponentKind, Severity, start_span, SpanKind, provider_latency

_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterProvider(BaseProvider):
    def __init__(self) -> None:
        self.base_url = _BASE_URL
        self._client = httpx.AsyncClient(timeout=60)
        self._headers = {"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}", "Content-Type": "application/json"}

    async def chat(self, messages, context=None, trace_id="", xray_headers=None) -> str:
        req_headers = dict(self._headers)
        if xray_headers:
            req_headers.update(xray_headers)
        payload = {"model": settings.OPENROUTER_MODEL, "messages": messages}
        t0 = time.time()
        span = start_span(SpanKind.PROVIDER_CALL, "openrouter.chat", trace_id=trace_id)

        async def _do():
            r = await self._client.post(f"{self.base_url}/chat/completions", json=payload, headers=req_headers)
            r.raise_for_status()
            return r.json()

        try:
            data = await with_retry(_do, context="openrouter.chat", trace_id=trace_id)
        except Exception:
            span.end("error")
            latency = time.time() - t0
            provider_latency.observe(latency * 1000)
            emit(Event(time.time(), trace_id, ComponentKind.PROVIDER, EventKind.PROVIDER_FAILED, Severity.ERROR, "openrouter failed", {"latency_ms": latency * 1000}))
            log.error("provider_failed provider=openrouter latency=%.2fs trace_id=%s", latency, trace_id)
            raise
        latency = time.time() - t0
        span.end()
        provider_latency.observe(latency * 1000)
        log.info("provider_ok provider=openrouter latency=%.2fs trace_id=%s", latency, trace_id)
        return data["choices"][0]["message"]["content"]

    async def stream(self, messages, trace_id="", xray_headers=None):
        req_headers = dict(self._headers)
        if xray_headers:
            req_headers.update(xray_headers)
        payload = {"model": settings.OPENROUTER_MODEL, "messages": messages, "stream": True}
        t0 = time.time()
        try:
            async with self._client.stream("POST", f"{self.base_url}/chat/completions", json=payload, headers=req_headers) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line:
                        yield line
        except Exception:
            log.error("provider_failed provider=openrouter operation=stream latency=%.2fs trace_id=%s", time.time() - t0, trace_id)
            raise

    async def health(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{self.base_url}/models", headers=self._headers)
                r.raise_for_status()
                return {"status": "ok", "provider": "openrouter"}
        except Exception as exc:
            return {"status": "error", "provider": "openrouter", "error": str(exc)}

    async def list_models(self) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{self.base_url}/models", headers=self._headers)
                if r.status_code == 403:
                    log.warning("openrouter_list_models_403 external_blocker")
                    return [{"id": settings.OPENROUTER_MODEL, "object": "model", "owned_by": "openrouter", "status": "unavailable"}]
                r.raise_for_status()
                data = r.json()
                models = [
                    {"id": m.get("id", "unknown"), "object": "model", "owned_by": m.get("owned_by", "openrouter")}
                    for m in data.get("data", [])
                ]
                return models if models else [{"id": settings.OPENROUTER_MODEL, "object": "model", "owned_by": "openrouter"}]
        except Exception as exc:
            log.warning("openrouter_list_models_failed error=%s", exc)
            return [{"id": settings.OPENROUTER_MODEL, "object": "model", "owned_by": "openrouter", "status": "unavailable"}]

    async def close(self) -> None:
        await self._client.aclose()
