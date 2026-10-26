"""Этап 2: управление видеозаданием из Studio — offline-проверки (без live).

Сквозной путь на тестовых ответах API arkaim-media:
  POST /studio/video-jobs (план + выбор исполнителя)
    → ассет generating → фон: MediaClient (httpx-API подменён)
    → AssetStorage (tmp) → completed | failed
    → статус/ошибка/файл читаются существующими GET /book/assets/{id}[ /file].

Байты генерации — существующий видеоклип
data/visual_assets/videos/asset_20261015_003700_f07044.mp4 (второй платный
запуск ComfyICU НЕ выполняется, сеть не используется).

Запуск (из runtime/):
  .venv\\Scripts\\python -m pytest tests/test_studio_video_job.py -v
"""

from __future__ import annotations

import asyncio
import base64
import sys
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

REPO = Path(__file__).resolve().parent.parent.parent
EXISTING_MP4 = REPO / "data" / "visual_assets" / "videos" / "asset_20261015_003700_f07044.mp4"
SCENE = "conflict_гиперборея_материальный_путь_атлантиды"  # chapter 1
PLAN_ID = "plan_028a6dda3148"  # plan_id video_description из /book/studio-describe


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture()
def isolated_assets(tmp_path, monkeypatch):
    """AssetStorage на временных хранилищах: рабочие БД/файлы не трогаются."""
    from core.adc_deps import registry
    from visual_assets import storage as storage_mod

    monkeypatch.setattr(storage_mod, "_DATA_DIR", tmp_path / "visual_assets")
    store = storage_mod.AssetStorage(db_path=tmp_path / "studio_video_jobs.db")
    had = "asset_store" in registry._instances
    old = registry._instances.get("asset_store")
    registry._instances["asset_store"] = store
    yield store
    # Соединение открывается внутри asyncio.run/TestClient-цикла; без закрытия
    # не-daemon поток aiosqlite не даёт процессу pytest завершиться.
    asyncio.run(store.close())
    if had:
        registry._instances["asset_store"] = old
    else:
        registry._instances.pop("asset_store", None)


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload


@pytest.fixture()
def fake_media_api(monkeypatch):
    """Подмена API arkaim-media на уровне HTTP: MediaClient видит тестовые ответы.

    state["payloads"] — очередь следующих ответов; state["default"] — успех
    (байты существующего клипа + provenance). Ответ с "error" → HTTP-ошибка.
    """
    import core.media_client as mc

    state: dict = {
        "payloads": [],
        "last": {},
        "default": {
            "bytes_b64": base64.b64encode(EXISTING_MP4.read_bytes()).decode("ascii"),
            "media_id": "media_offline_001",
            "backend": "comfyicu",
            "workflow_used": "comfyicu_ltx25_i2v.json",
        },
    }

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, json=None, **kwargs):
            state["last"] = {"url": url, "body": json}
            payload = state["payloads"].pop(0) if state["payloads"] else state["default"]
            if "error" in payload:
                return _FakeResponse(int(payload.get("status", 500)), payload)
            return _FakeResponse(200, payload)

    monkeypatch.setattr(mc.httpx, "AsyncClient", _FakeAsyncClient)
    return state


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient
    from core.main import app

    return TestClient(app)


def _job_payload(**overrides) -> dict:
    payload = {
        "chapter": 1,
        "scene_id": SCENE,
        "prompt": "cinematic fantasy, epic film still, движение камеры",
        "plan_id": PLAN_ID,
        "preferred_backend": "comfyicu",
        "duration_sec": 8.0,
        "fps": 24,
        "size": "1024x576",
    }
    payload.update(overrides)
    return payload


# ── 1. Сквозной путь: запуск → статус → сохранённый результат ────


class TestVideoJobOffline:
    def test_job_completes_with_existing_clip(self, client, isolated_assets, fake_media_api):
        assert EXISTING_MP4.exists(), "существующий клип не найден"

        resp = client.post("/studio/video-jobs", json=_job_payload())
        assert resp.status_code == 200, resp.text
        started = resp.json()["data"]
        assert started["status"] == "generating"
        assert started["scene_id"] == SCENE
        assert started["plan_id"] == PLAN_ID
        asset_id = started["asset_id"]

        # Статус задания — существующий GET /book/assets/{id}
        got = client.get(f"/book/assets/{asset_id}")
        assert got.status_code == 200
        asset = got.json()["data"]
        assert asset["status"] == "completed"
        assert asset["asset_type"] == "video"
        # Связь: сцена, производственный план, workflow, исполнитель
        assert asset["scene_id"] == SCENE
        assert asset["generation"]["plan_id"] == PLAN_ID
        assert asset["generation"]["workflow_used"] == "comfyicu_ltx25_i2v.json"
        assert asset["generation"]["media_id"] == "media_offline_001"
        assert asset["generation"]["provider"] == "comfyicu"
        assert asset["generation"]["backend"] == "comfyicu"
        # Выбор исполнителя дошёл до запроса к arkaim-media
        assert fake_media_api["last"]["body"]["execution"]["preferred_backend"] == "comfyicu"
        assert fake_media_api["last"]["body"]["execution"]["media_kind"] == "video"

        # Готовый результат — существующее чтение файла
        opened = client.get(f"/book/assets/{asset_id}/file")
        assert opened.status_code == 200
        assert opened.headers["content-type"].startswith("video/mp4")
        assert opened.content == EXISTING_MP4.read_bytes()

        # Файл физически сохранён через AssetStorage (в tmp изоляции)
        from visual_assets import storage as storage_mod

        assert asset["file_path"]
        saved = storage_mod._DATA_DIR / asset["file_path"]
        assert saved.exists()
        assert saved.read_bytes() == EXISTING_MP4.read_bytes()

    def test_job_failed_shows_error(self, client, isolated_assets, fake_media_api):
        fake_media_api["payloads"] = [{"status": 500, "error": {"code": "GENERATION_FAILED"}}]

        resp = client.post("/studio/video-jobs", json=_job_payload())
        assert resp.status_code == 200, resp.text
        asset_id = resp.json()["data"]["asset_id"]

        asset = client.get(f"/book/assets/{asset_id}").json()["data"]
        assert asset["status"] == "failed"
        assert asset["error"] and "media_backend_error: GENERATION_FAILED" in asset["error"]
        # Готового результата нет — файл не отдаётся
        assert client.get(f"/book/assets/{asset_id}/file").status_code == 404

    def test_unknown_scene_rejected(self, client, isolated_assets, fake_media_api):
        resp = client.post("/studio/video-jobs", json=_job_payload(scene_id="no_such_scene"))
        assert resp.status_code == 404


# ── 2. Жизненный цикл статуса: generating → completed ────────────


class TestVideoJobLifecycle:
    def test_generating_until_execution_then_completed(self, isolated_assets, fake_media_api):
        """Задание создаётся как generating и завершается только исполнением."""
        from fastapi import BackgroundTasks

        from core.dto.requests import VideoJobRequest
        from core.routes.studio import create_video_job
        from visual_assets.schemas import AssetStatus

        async def scenario():
            tasks = BackgroundTasks()
            req = VideoJobRequest(**_job_payload())
            result = await create_video_job(req, tasks)  # фон НЕ запущен
            store = isolated_assets
            asset = await store.get(result.data["asset_id"])
            assert asset.status == AssetStatus.GENERATING
            assert asset.file_path is None

            await tasks()  # так FastAPI исполняет background-задачи

            asset = await store.get(asset.asset_id)
            assert asset.status == AssetStatus.COMPLETED
            assert asset.file_path is not None
            assert asset.generation.workflow_used == "comfyicu_ltx25_i2v.json"
            return asset

        asset = asyncio.run(scenario())
        assert asset.error is None


# ── 3. MediaClient: bytes + provenance (обратная совместимость) ──


class TestMediaClientMeta:
    def test_generate_video_with_meta(self, fake_media_api):
        from core.media_client import MediaClient

        res = asyncio.run(MediaClient().generate_video_with_meta("x", duration=8.0, preferred_backend="comfyicu"))
        assert res.data == EXISTING_MP4.read_bytes()
        assert res.media_id == "media_offline_001"
        assert res.backend == "comfyicu"
        assert res.workflow_used == "comfyicu_ltx25_i2v.json"
        assert fake_media_api["last"]["body"]["execution"]["preferred_backend"] == "comfyicu"

    def test_generate_video_bytes_contract_unchanged(self, fake_media_api):
        """Прежний интерфейс не меняется: generate_video → только bytes."""
        from core.media_client import MediaClient

        data = asyncio.run(MediaClient().generate_video("x", duration=8.0))
        assert data == EXISTING_MP4.read_bytes()
        assert isinstance(data, bytes)

    def test_backend_error_raises_media_client_error(self, fake_media_api):
        from core.media_client import MediaClient, MediaClientError

        fake_media_api["payloads"] = [{"status": 500, "error": {"code": "GENERATION_FAILED"}}]
        with pytest.raises(MediaClientError, match="media_backend_error: GENERATION_FAILED"):
            asyncio.run(MediaClient().generate_video("x"))
