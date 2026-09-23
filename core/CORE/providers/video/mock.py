"""MockVideoProvider — заглушка для генерации видео."""
from __future__ import annotations

import asyncio
from . import VideoProvider


class MockVideoProvider(VideoProvider):
    """Всегда доступен, возвращает SVG-анимацию."""

    async def generate(self, prompt: str, duration: float = 8.0, size: str = "1024x576", fps: int = 24) -> bytes:
        w, h = 1024, 576
        if "x" in size:
            try:
                w, h = map(int, size.split("x"))
            except ValueError:
                pass
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">
            <rect width="100%" height="100%" fill="#1a1a2e"/>
            <circle cx="{w//2}" cy="{h//2}" r="100" fill="#e94560" opacity="0.8">
                <animate attributeName="r" values="80;120;80" dur="2s" repeatCount="indefinite"/>
            </circle>
            <text x="50%" y="50%" text-anchor="middle" fill="#ffffff" font-size="20" dy="5">
                Mock Video: {prompt[:50]}
            </text>
        </svg>'''
        return svg.encode("utf-8")

    async def health(self) -> bool:
        return True
