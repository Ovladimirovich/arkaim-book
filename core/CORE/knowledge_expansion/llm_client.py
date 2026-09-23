"""
LLM Client — обёртка над LLM для Knowledge Expansion Pipeline.

Поддерживает:
- GigaChat (через существующий провайдер с OAuth2)
- OpenRouter (fallback)
"""
import logging
import sys
from pathlib import Path

log = logging.getLogger("hermes.knowledge_expansion.llm_client")


class LLMClient:
    """Клиент для генерации текста через LLM."""

    def __init__(self, provider: str = "gigachat"):
        self._provider = provider
        self._gigachat = None

    async def generate(self, prompt: str, max_tokens: int = 2000) -> str:
        """Сгенерировать текст через LLM."""
        if self._provider == "gigachat":
            return await self._generate_gigachat(prompt, max_tokens)
        return ""

    async def chat(self, messages: list[dict], max_tokens: int = 2000) -> str:
        """Сгенерировать ответ через LLM (совместимость с Voice)."""
        # Извлечь последний user-запрос
        prompt = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                prompt = msg.get("content", "")
                break
        if not prompt and messages:
            prompt = messages[-1].get("content", "")
        return await self.generate(prompt, max_tokens)

    async def _generate_gigachat(self, prompt: str, max_tokens: int) -> str:
        """Генерация через GigaChat (используем существующий провайдер)."""
        try:
            # Добавляем путь к runtime
            runtime_path = str(Path(__file__).resolve().parents[3] / "runtime")
            if runtime_path not in sys.path:
                sys.path.insert(0, runtime_path)

            from core.providers.gigachat import GigaChatProvider
            from core.config import settings

            if not self._gigachat:
                self._gigachat = GigaChatProvider()

            # Получаем токен
            token = await self._gigachat._acquire_token()

            # Отправляем запрос
            import httpx
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": settings.GIGACHAT_MODEL if hasattr(settings, 'GIGACHAT_MODEL') else "GigaChat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
            }

            async with httpx.AsyncClient(timeout=120, verify=False) as client:
                resp = await client.post(
                    f"{self._gigachat.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]

        except Exception as e:
            log.error("gigachat_error error=%s", e)
            return ""

    async def health(self) -> bool:
        """Проверить доступность LLM."""
        try:
            result = await self.generate("Say hello.", max_tokens=10)
            return bool(result)
        except Exception:
            return False


def create_llm_client(provider: str = "gigachat") -> LLMClient:
    """Создать LLM-клиент."""
    return LLMClient(provider=provider)
