"""
LLM Client — единый интерфейс для LLM (GigaChat).

Используется Voice для озвучки, KeeperAgent для формулировок.
Поддерживает OAuth2 авторизацию GigaChat.
"""
from typing import List, Dict, Optional, AsyncIterator
import httpx
import os
import base64
import time
import logging

log = logging.getLogger("hermes.llm")


class GigaChatToken:
    """Управление OAuth2 токеном GigaChat."""

    def __init__(self):
        self._access_token = ""
        self._expires_at = 0.0

    @property
    def is_valid(self) -> bool:
        return bool(self._access_token) and time.time() < self._expires_at - 300

    async def acquire(self, client: httpx.AsyncClient) -> str:
        """Получить валидный access token."""
        if self.is_valid:
            return self._access_token

        client_id = os.getenv("GIGACHAT_CLIENT_ID", "")
        client_secret = os.getenv("GIGACHAT_CLIENT_SECRET", "")

        if client_id and client_secret:
            return await self._oauth_token(client, client_id, client_secret)

        # Fallback на статический токен
        token = os.getenv("GIGACHAT_TOKEN", "")
        if token:
            self._access_token = token
            self._expires_at = float("inf")
            return token

        raise RuntimeError("No GigaChat credentials configured")

    async def _oauth_token(self, client: httpx.AsyncClient, client_id: str, client_secret: str) -> str:
        """Получить OAuth2 токен."""
        basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        scope = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
        log.info("llm_oauth_start client_id=%s", client_id[:10])
        resp = await client.post(
            "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            headers={
                "Authorization": f"Basic {basic}",
                "RqUID": client_id,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data=f"scope={scope}",
            timeout=30.0,
        )
        log.info("llm_oauth_response status=%d", resp.status_code)
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data["access_token"]
        expires_at_raw = data.get("expires_at", int(time.time() + 1800))
        if isinstance(expires_at_raw, (int, float)) and expires_at_raw > 1e12:
            self._expires_at = expires_at_raw / 1000
        else:
            self._expires_at = float(expires_at_raw)
        log.info("llm_oauth_ok expires_in=%d", self._expires_at - time.time())
        return self._access_token


class LLMClient:
    """
    Клиент для GigaChat API.

    Voice использует этот клиент как микрофон.
    """

    def __init__(self):
        self.url = os.getenv("GIGACHAT_URL", "https://gigachat.devices.sberbank.ru/api/v1")
        self.model = "GigaChat-Pro"
        self.verify_ssl = os.getenv("GIGACHAT_VERIFY_SSL", "false").lower() == "true"
        self._token = GigaChatToken()
        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=30.0,
        )
        self._client = httpx.AsyncClient(
            timeout=120.0,
            limits=limits,
            verify=self.verify_ssl,
        )

    async def _get_headers(self) -> dict:
        """Получить заголовки с валидным токеном."""
        token = await self._token.acquire(self._client)
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """
        Отправить запрос к GigaChat API.

        Voice вызывает этот метод для формулировки ответа.
        """
        try:
            headers = await self._get_headers()
            log.info("llm_chat_start model=%s messages=%d", model or self.model, len(messages))
            response = await self._client.post(
                f"{self.url}/chat/completions",
                json={
                    "messages": messages,
                    "model": model or self.model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                headers=headers,
            )
            log.info("llm_chat_response status=%d", response.status_code)
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                raise RuntimeError(f"LLM service error: {data['error']}")
            if "choices" not in data or not data["choices"]:
                raise RuntimeError("LLM empty response")
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.json()
            except Exception:
                error_detail = e.response.text[:200]
            if e.response.status_code == 401:
                # Токен протух — сбросить и попробовать снова
                self._token._access_token = ""
                self._token._expires_at = 0
                raise RuntimeError("LLM auth expired, retrying")
            if e.response.status_code == 429:
                raise RuntimeError("LLM rate_limit_exceeded")
            raise RuntimeError(f"LLM HTTP {e.response.status_code}: {error_detail}")
        except Exception as e:
            raise RuntimeError(f"LLM request failed: {e}")

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Потоковый чат для Voice."""
        try:
            headers = await self._get_headers()
            async with self._client.stream(
                "POST",
                f"{self.url}/chat/completions",
                json={
                    "messages": messages,
                    "model": model or self.model,
                    "stream": True,
                },
                headers=headers,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        yield line
        except Exception as e:
            raise RuntimeError(f"LLM stream failed: {e}")

    async def health(self) -> dict:
        """Проверка здоровья GigaChat."""
        try:
            headers = await self._get_headers()
            resp = await self._client.get(
                f"{self.url}/models",
                headers=headers,
                timeout=5.0,
            )
            if resp.status_code == 200:
                return {"status": "ok", "provider": "gigachat"}
            return {"status": "error", "detail": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    async def close(self):
        await self._client.aclose()


# Singleton
llm = LLMClient()
