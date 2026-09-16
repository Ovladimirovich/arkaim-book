class BaseProvider:
    async def chat(self, messages: list[dict], context: list[dict] | None = None, trace_id: str = "", xray_headers: dict | None = None) -> str:
        raise NotImplementedError

    async def stream(self, messages: list[dict], trace_id: str = "", xray_headers: dict | None = None):
        raise NotImplementedError

    async def health(self) -> dict:
        return {"status": "unknown", "provider": self.__class__.__name__}

    async def list_models(self) -> list[dict]:
        return []

    async def close(self):
        pass
