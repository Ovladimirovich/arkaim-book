import asyncio
import base64
import time

import httpx

from core.config import settings
from core.logging import log
from core.retry import with_retry
from core.providers.base import BaseProvider
from aethon.xray import Event, emit, EventKind, ComponentKind, Severity, start_span, SpanKind, provider_latency

_AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
_BASE_URL = "https://gigachat.devices.sberbank.ru/api/v1"


class GigaChatToken:
    def __init__(self) -> None:
        self._access_token = ""
        self._expires_at = 0.0
        self._lock = asyncio.Lock()

    @property
    def is_valid(self) -> bool:
        return bool(self._access_token) and time.time() < self._expires_at - 300


class GigaChatProvider(BaseProvider):
    def __init__(self) -> None:
        self.base_url = _BASE_URL
        self.verify = settings.GIGACHAT_VERIFY_SSL
        self.token = GigaChatToken()
        self._client = httpx.AsyncClient(timeout=60, verify=self.verify)

    async def _acquire_token(self) -> str:
        if self.token.is_valid:
            return self.token._access_token
        async with self.token._lock:
            if self.token.is_valid:
                return self.token._access_token
            if settings.GIGACHAT_CLIENT_ID and settings.GIGACHAT_CLIENT_SECRET:
                return await self._oauth_token(settings.GIGACHAT_CLIENT_ID, settings.GIGACHAT_CLIENT_SECRET)
            if settings.GIGACHAT_TOKEN:
                self.token._access_token = settings.GIGACHAT_TOKEN
                self.token._expires_at = float("inf")
                return self.token._access_token
            raise RuntimeError("No GigaChat credentials configured")

    async def _oauth_token(self, client_id: str, client_secret: str) -> str:
        basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        headers = {"Authorization": f"Basic {basic}", "RqUID": client_id, "Content-Type": "application/x-www-form-urlencoded"}
        data = {"scope": settings.GIGACHAT_SCOPE}
        t0 = time.time()
        resp = await self._client.post(_AUTH_URL, headers=headers, data=data, timeout=30)
        resp.raise_for_status()
        body = resp.json()
        refresh_time = time.time() - t0
        self.token._access_token = body["access_token"]
        expires_at_raw = body.get("expires_at", int(time.time() + 1800))
        if isinstance(expires_at_raw, (int, float)) and expires_at_raw > 1e12:
            self.token._expires_at = expires_at_raw / 1000
        else:
            self.token._expires_at = float(expires_at_raw)
        log.info("token_refresh refresh_time=%.2fs", refresh_time)
        return self.token._access_token

    async def chat(self, messages, context=None, trace_id="", xray_headers=None) -> str:
        token = await self._acquire_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        if xray_headers:
            headers.update(xray_headers)
        payload = {"model": "GigaChat-Pro", "messages": messages}
        t0 = time.time()
        span = start_span(SpanKind.PROVIDER_CALL, "gigachat.chat", trace_id=trace_id)

        async def _do():
            r = await self._client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            r.raise_for_status()
            return r.json()

        try:
            data = await with_retry(_do, context="gigachat.chat", trace_id=trace_id)
        except Exception:
            span.end("error")
            latency = time.time() - t0
            provider_latency.observe(latency * 1000)
            emit(Event(time.time(), trace_id, ComponentKind.PROVIDER, EventKind.PROVIDER_FAILED, Severity.ERROR, "gigachat failed", {"latency_ms": latency * 1000}))
            log.error("provider_failed provider=gigachat latency=%.2fs trace_id=%s", time.time() - t0, trace_id)
            raise
        latency = time.time() - t0
        span.end()
        provider_latency.observe(latency * 1000)
        log.info("provider_ok provider=gigachat latency=%.2fs trace_id=%s", latency, trace_id)
        return data["choices"][0]["message"]["content"]

    async def stream(self, messages, trace_id="", xray_headers=None):
        token = await self._acquire_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        if xray_headers:
            headers.update(xray_headers)
        payload = {"model": "GigaChat-Pro", "messages": messages, "stream": True}
        t0 = time.time()
        try:
            async with self._client.stream("POST", f"{self.base_url}/chat/completions", json=payload, headers=headers) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line:
                        yield line
        except Exception:
            log.error("provider_failed provider=gigachat operation=stream latency=%.2fs trace_id=%s", time.time() - t0, trace_id)
            raise

    async def health(self) -> dict:
        try:
            token = await self._acquire_token()
            headers = {"Authorization": f"Bearer {token}"}
            async with httpx.AsyncClient(verify=self.verify, timeout=10) as client:
                r = await client.get(f"{self.base_url}/models", headers=headers)
                r.raise_for_status()
                return {"status": "ok", "provider": "gigachat"}
        except Exception as exc:
            return {"status": "error", "provider": "gigachat", "error": str(exc)}

    async def list_models(self) -> list[dict]:
        try:
            token = await self._acquire_token()
            headers = {"Authorization": f"Bearer {token}"}
            async with httpx.AsyncClient(verify=self.verify, timeout=10) as client:
                r = await client.get(f"{self.base_url}/models", headers=headers)
                r.raise_for_status()
                data = r.json()
                models = []
                for m in data.get("data", []):
                    models.append({"id": m.get("id", "unknown"), "object": "model", "owned_by": "sber", "context_window": 0, "modalities": ["text"]})
                return models if models else [{"id": "GigaChat-Pro", "object": "model", "owned_by": "sber", "context_window": 32000, "modalities": ["text"]}]
        except Exception as exc:
            log.warning("gigachat_list_models_failed error=%s", exc)
            return [{"id": "GigaChat-Pro", "object": "model", "owned_by": "sber", "context_window": 32000, "modalities": ["text"], "status": "unknown"}]

    async def close(self) -> None:
        await self._client.aclose()
