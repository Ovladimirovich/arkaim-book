"""Video providers — генерация видео для Visualization Layer."""
from abc import ABC, abstractmethod


class VideoProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, duration: float = 8.0, size: str = "1024x576", fps: int = 24) -> bytes:
        raise NotImplementedError()

    @abstractmethod
    async def health(self) -> bool:
        raise NotImplementedError()


class VideoProviderChain:
    def __init__(self, providers: list[VideoProvider]):
        self.providers = providers

    async def generate(self, prompt: str, duration: float = 8.0, size: str = "1024x576", fps: int = 24) -> bytes:
        last_exc = None
        for provider in self.providers:
            try:
                if await provider.health():
                    return await provider.generate(prompt, duration=duration, size=size, fps=fps)
            except Exception as exc:
                last_exc = exc
                continue
        raise RuntimeError(f"All video providers failed, last error: {last_exc}")


# ImageSequenceVideoProvider removed: Arkaim no longer runs local video assembly
# (Arkaim Media Boundary ADR). Video assembly now lives in arkaim-media (separate repo).
from .mock import MockVideoProvider

__all__ = ["VideoProvider", "VideoProviderChain", "MockVideoProvider"]
