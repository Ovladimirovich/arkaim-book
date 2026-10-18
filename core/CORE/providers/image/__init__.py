"""Image providers — генерация изображений для Visualization Layer."""
import logging
from typing import Optional
from abc import ABC, abstractmethod

log = logging.getLogger("hermes.visualization.providers")


class ImageProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, size: str = "1024x1024") -> bytes:
        raise NotImplementedError()

    @abstractmethod
    async def health(self) -> bool:
        raise NotImplementedError()


class ProviderExecutionResult:
    def __init__(self, provider_name: str, provider_kind: str, data: bytes):
        self.provider_name = provider_name
        self.provider_kind = provider_kind
        self.bytes = data


class ImageProviderChain:
    def __init__(self, providers: list[ImageProvider]):
        self.providers = providers

    def _provider_name(self, provider: ImageProvider) -> str:
        for attr in ("provider_name", "name"):
            value = getattr(provider, attr, None)
            if value:
                return str(value)
        return type(provider).__name__.replace("Provider", "").replace("Image", "").lower()

    def _provider_kind(self, provider: ImageProvider) -> str:
        name = self._provider_name(provider).lower()
        if "mock" in name or "svg" in name or "template" in name:
            return "fallback"
        return "real"

    def _normalize_preferred_provider(self, preferred_provider: Optional[str]) -> str:
        if not preferred_provider:
            return "auto"
        normalized = preferred_provider.strip().lower()
        aliases = {
            "real": "real",
            "auto": "auto",
            "mock": "mock",
            "fallback": "fallback",
            "comfy": "comfyui",
            "comfyui": "comfyui",
            "svg": "mock",
        }
        return aliases.get(normalized, normalized)

    def _ordered_providers(self, preferred_provider: Optional[str]) -> list[ImageProvider]:
        normalized = self._normalize_preferred_provider(preferred_provider)
        if normalized == "auto":
            return list(self.providers)
        if normalized == "real":
            real_providers = [p for p in self.providers if self._provider_kind(p) == "real"]
            fallback_providers = [p for p in self.providers if self._provider_kind(p) != "real"]
            return real_providers + fallback_providers

        exact_matches = [p for p in self.providers if self._provider_name(p).lower() == normalized]
        other_providers = [p for p in self.providers if self._provider_name(p).lower() != normalized]
        return exact_matches + other_providers

    async def generate_with_metadata(
        self,
        prompt: str,
        size: str = "1024x1024",
        preferred_provider: Optional[str] = None,
    ) -> ProviderExecutionResult:
        last_exc = None
        for provider in self._ordered_providers(preferred_provider):
            provider_name = self._provider_name(provider)
            try:
                if await provider.health():
                    data = await provider.generate(prompt, size)
                    result = ProviderExecutionResult(
                        provider_name=provider_name,
                        provider_kind=self._provider_kind(provider),
                        data=data,
                    )
                    log.info("image_provider_selected provider=%s kind=%s", provider_name, result.provider_kind)
                    return result
            except Exception as exc:
                last_exc = exc
                import traceback
                log.error("image_provider_failed provider=%s error=%s", provider_name, exc)
                log.error("image_provider_traceback provider=%s", provider_name)
                traceback.print_exc()
                continue
        raise RuntimeError(f"All image providers failed, last error: {last_exc}")

    async def generate(self, prompt: str, size: str = "1024x1024") -> bytes:
        result = await self.generate_with_metadata(prompt, size=size)
        return result.bytes


from .mock import MockImageProvider
from .svg_template import SVGTemplateProvider
# StableDiffusionProvider / ComfyUIProvider removed: Arkaim no longer runs
# local image generation (Arkaim Media Boundary ADR). These providers
# now live in arkaim-media (separate repo).

__all__ = ["ImageProvider", "ImageProviderChain", "ProviderExecutionResult", "MockImageProvider", "SVGTemplateProvider"]
