"""SVG Template Provider — compositional fallback без нейросетей."""
from typing import Optional
from providers.image import ImageProvider


class SVGTemplateProvider(ImageProvider):
    """Генерирует SVG на основе шаблонов."""

    async def generate(self, prompt: str, size: str = "1024x1024") -> bytes:
        width, height = self._parse_size(size)
        bg = "#1a1a2e"
        accent = "#7cfc00"
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
            f'<rect width="100%" height="100%" fill="{bg}"/>'
            f'<rect x="10%" y="10%" width="80%" height="80%" fill="none" stroke="{accent}" stroke-width="2"/>'
            f'<text x="50%" y="50%" font-family="monospace" font-size="24"'
            f' fill="{accent}" text-anchor="middle" dy=".3em">Scene Visualization</text>'
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