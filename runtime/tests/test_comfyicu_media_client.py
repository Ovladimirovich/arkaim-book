"""OWNER-GO 2026-10-14: ComfyICU — проброс preferred_backend в video-конверте моста.

Offline (без сети и без media-сервера): MediaClient video-вызов формирует
execution.preferred_backend из аргумента (по умолчанию "auto" — прежнее
поведение, контракт M4.1 не меняется: поле уже часть execution-схемы).

Запуск (из runtime/):
  .venv\\Scripts\\python -m pytest tests/test_comfyicu_media_client.py -v
"""

from __future__ import annotations

import asyncio

from core.media_client import MediaClient


def _captured_client():
    client = MediaClient()
    captured: dict = {}

    async def fake_post(body: dict) -> bytes:
        captured["body"] = body
        return b"\x00\x00\x00\x18ftypmp42"

    client._post_generate = fake_post  # type: ignore[method-assign]
    return client, captured


class TestVideoPreferredBackendPassthrough:
    def test_generate_video_explicit_comfyicu(self):
        client, captured = _captured_client()
        asyncio.run(client.generate_video("движение камеры", duration=5.0, preferred_backend="comfyicu"))
        ex = captured["body"]["execution"]
        assert ex["media_kind"] == "video"
        assert ex["preferred_backend"] == "comfyicu"
        assert ex["duration_sec"] == 5.0
        assert captured["body"]["plan"]["media_kind"] == "video"

    def test_generate_video_default_is_auto(self):
        """Прежнее поведение не меняется: авто-путь цепи (mock) не трогается."""
        client, captured = _captured_client()
        asyncio.run(client.generate_video("x", duration=5.0))
        assert captured["body"]["execution"]["preferred_backend"] == "auto"

    def test_generate_video_kwargs_route(self):
        """Универсальный generate() с duration/fps → video + проброс бэкенда."""
        client, captured = _captured_client()
        asyncio.run(client.generate("x", size="1024x576", duration=6.0, fps=24, preferred_backend="comfyicu"))
        ex = captured["body"]["execution"]
        assert ex["media_kind"] == "video"
        assert ex["preferred_backend"] == "comfyicu"
        assert ex["fps"] == 24

    def test_image_path_unaffected(self):
        client, captured = _captured_client()
        asyncio.run(client.generate("x", size="1024x1024"))
        assert captured["body"]["execution"]["media_kind"] == "image"
        assert captured["body"]["execution"]["preferred_backend"] == "auto"
