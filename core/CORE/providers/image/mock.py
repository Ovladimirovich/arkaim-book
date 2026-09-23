"""Mock-провайдер: возвращает детерминированный SVG-placeholder."""
from io import BytesIO

from providers.image import ImageProvider


class MockImageProvider(ImageProvider):
    """Для тестов и开发-режима без GPU."""

    async def generate(self, prompt: str, size: str = "1024x1024") -> bytes:
        width, height = self._parse_size(size)
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
            f'<rect width="100%" height="100%" fill="#1a1a1a"/>'
            f'<text x="50%" y="50%" font-family="Arial" font-size="32"'
            f' fill="#7cfc00" text-anchor="middle" dy=".3em">'
            f'Mock Visualization</text>'
            f'</svg>'
        )
        return svg.encode("utf-8")

    async def health(self) -> bool:
        return True

    @staticmethod
    def _parse_size(size: str) -> tuple[int, int]:
        try:
            w, h = size.split("x")
            return int(w), int(h)
        except Exception:
            return 1024, 1024