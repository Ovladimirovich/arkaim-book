
import httpx

GATEWAY_URL = "http://127.0.0.1:8000"


class HermesClient:
    def __init__(self, base_url: str = GATEWAY_URL, api_key: str = ""):
        self.base_url = base_url
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    async def chat(self, messages: list[dict], provider: str = "") -> dict:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{self.base_url}/v1/chat",
                json={"messages": messages, "provider": provider},
                headers=self.headers,
            )
            r.raise_for_status()
            return r.json()

    async def stream(self, messages: list[dict], provider: str = ""):
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/stream",
                json={"messages": messages, "provider": provider, "stream": True},
                headers=self.headers,
            ) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if line and line != "data: [DONE]":
                        yield line
