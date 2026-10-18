"""i2v: утверждённый кадр реально передаётся в arkaim-media (OWNER-GO).

Offline-проверки (без live, платные облачные запуски НЕ выполняются):
  - POST /studio/video-jobs с image_asset_id → в теле POST /v1/generate
    execution.input_image.bytes_b64 декодируется в СОДЕРЖИМОЕ ФАЙЛА кадра
    (проверка передачи, а не только наличия id в provenance);
  - reference_image_id + input_image_sha256 фиксируются ПОСЛЕ фактической
    передачи (completed), при ошибке чтения — задание failed без вызова
    MediaClient (молчаливый запуск без кадра исключён);
  - без image_asset_id — прежний t2v (тело без input_image);
  - MediaClient._video_body: структура execution.

Запуск (из runtime/):
  python -m pytest tests/test_studio_video_i2v.py -v
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import sys
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

SCENE = "conflict_гиперборея_материальный_путь_атлантиды"  # chapter 1

# 1x1 PNG — «утверждённый кадр»; хеш ровно этих байтов обязан дойти до media-сервера
PNG_1PX = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
PNG_1PX_SHA = hashlib.sha256(PNG_1PX).hexdigest()


# ── Fixtures (образец test_studio_image_job.py) ────────────────────


@pytest.fixture()
def isolated_assets(tmp_path, monkeypatch):
    from core.adc_deps import registry
    from visual_assets import storage as storage_mod

    monkeypatch.setattr(storage_mod, "_DATA_DIR", tmp_path / "visual_assets")
    store = storage_mod.AssetStorage(db_path=tmp_path / "studio_video_i2v.db")
    had = "asset_store" in registry._instances
    old = registry._instances.get("asset_store")
    registry._instances["asset_store"] = store
    yield store
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
    """HTTP-подмена arkaim-media: фиксируем ВСЕ тела запросов (не только последний)."""
    import core.media_client as mc

    state: dict = {
        "posts": [],
        "payloads": [],
        "default": {
            "bytes_b64": base64.b64encode(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 16).decode("ascii"),
            "media_id": "media_video_i2v_001",
            "backend": "mock",
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
            state["posts"].append({"url": url, "body": json})
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


async def _image_asset_with_file(store, asset_id: str, data: bytes = PNG_1PX):
    from visual_assets.schemas import AssetStatus, AssetType, VisualAsset

    asset = VisualAsset(
        asset_id=asset_id,
        asset_type=AssetType.IMAGE,
        chapter=1,
        scene_id=SCENE,
        title=f"кадр {asset_id}",
        status=AssetStatus.COMPLETED,
    )
    asset = await store.save(asset)
    asset.file_path = store.save_file(asset.asset_id, asset.asset_type, data)
    return await store.save(asset)


def _video_job(**overrides) -> dict:
    payload = {
        "chapter": 1,
        "scene_id": SCENE,
        "prompt": "движение: медленный наезд камеры",
        "plan_id": "plan_video_i2v",
        "preferred_backend": "comfyicu",
        "duration_sec": 8.0,
        "fps": 24,
        "size": "1024x576",
    }
    payload.update(overrides)
    return payload


# ── 1. Байты кадра доходят до тела запроса к media-серверу ─────────


class TestFrameBytesTransmitted:
    def test_input_image_bytes_equal_asset_file(self, client, isolated_assets, fake_media_api):
        """execution.input_image.bytes_b64 → ровно содержимое файла кадра."""
        asyncio.run(_image_asset_with_file(isolated_assets, "asset_frame_bytes"))

        resp = client.post(
            "/studio/video-jobs",
            json=_video_job(image_asset_id="asset_frame_bytes"),
        )
        assert resp.status_code == 200, resp.text
        asset_id = resp.json()["data"]["asset_id"]

        assert len(fake_media_api["posts"]) == 1, "ровно один POST к media-сервису"
        execution = fake_media_api["posts"][0]["body"]["execution"]
        img = execution["input_image"]
        assert base64.b64decode(img["bytes_b64"]) == PNG_1PX, "в запрос должны уйти сами байты кадра"
        assert img["filename"] == "scene_frame_asset_frame_bytes.png"
        assert execution["media_kind"] == "video"

        # Связь результата с исходным кадром: id + sha256 переданных байтов
        asset = client.get(f"/book/assets/{asset_id}").json()["data"]
        assert asset["status"] == "completed"
        assert asset["generation"]["reference_image_id"] == "asset_frame_bytes"
        assert asset["generation"]["input_image_sha256"] == PNG_1PX_SHA

    def test_other_frame_bytes_transmitted(self, client, isolated_assets, fake_media_api):
        """Другой кадр → другие байты (не захардкоженный шаблон)."""
        other = b"\xff\xd8\xff\xe0OTHER_FRAME_JPEG_BYTES"
        asyncio.run(_image_asset_with_file(isolated_assets, "asset_frame_other", data=other))

        resp = client.post("/studio/video-jobs", json=_video_job(image_asset_id="asset_frame_other"))
        assert resp.status_code == 200, resp.text

        img = fake_media_api["posts"][0]["body"]["execution"]["input_image"]
        assert base64.b64decode(img["bytes_b64"]) == other
        asset = client.get(f"/book/assets/{resp.json()['data']['asset_id']}").json()["data"]
        assert asset["generation"]["input_image_sha256"] == hashlib.sha256(other).hexdigest()

    def test_t2v_without_image_sends_no_input_image(self, client, isolated_assets, fake_media_api):
        """Без image_asset_id — прежний t2v: поля нет, provenance пуст."""
        resp = client.post("/studio/video-jobs", json=_video_job())
        assert resp.status_code == 200, resp.text
        asset_id = resp.json()["data"]["asset_id"]

        execution = fake_media_api["posts"][0]["body"]["execution"]
        assert "input_image" not in execution
        asset = client.get(f"/book/assets/{asset_id}").json()["data"]
        assert asset["status"] == "completed"
        assert asset["generation"]["reference_image_id"] is None
        assert asset["generation"]["input_image_sha256"] is None

    def test_failed_transmission_keeps_no_reference(self, client, isolated_assets, fake_media_api):
        """Ошибка media-сервиса → failed; id/хеш не выдаются за «переданные»."""
        fake_media_api["payloads"] = [{"status": 500, "error": {"code": "GENERATION_FAILED"}}]
        asyncio.run(_image_asset_with_file(isolated_assets, "asset_frame_err"))

        resp = client.post("/studio/video-jobs", json=_video_job(image_asset_id="asset_frame_err"))
        assert resp.status_code == 200, resp.text
        asset = client.get(f"/book/assets/{resp.json()['data']['asset_id']}").json()["data"]
        assert asset["status"] == "failed"
        assert asset["error"] and "media_backend_error" in asset["error"]
        # запрос с кадром УШЁЛ, но подтверждения нет — provenance не заполняем
        assert asset["generation"]["reference_image_id"] is None
        assert asset["generation"]["input_image_sha256"] is None


# ── 2. Отказ до запуска: файл не читается → задание не идёт без кадра ──


class TestFrameReadFailureFailsLoudly:
    def test_reference_without_file_409_and_no_post(self, client, isolated_assets, fake_media_api):
        from visual_assets.schemas import AssetStatus, AssetType, VisualAsset

        asset = VisualAsset(
            asset_id="asset_frame_nofile",
            asset_type=AssetType.IMAGE,
            chapter=1,
            scene_id=SCENE,
            title="кадр без файла",
            status=AssetStatus.COMPLETED,
        )
        asyncio.run(isolated_assets.save(asset))  # file_path не задан

        resp = client.post("/studio/video-jobs", json=_video_job(image_asset_id="asset_frame_nofile"))
        assert resp.status_code == 409
        assert fake_media_api["posts"] == [], "запуск без читаемого кадра запрещён"

    def test_file_vanished_fails_job_without_media_call(self, client, isolated_assets, fake_media_api):
        """Страховка фона: файл пропал между роутом и исполнением → failed, POST нет."""
        from core.routes.studio import _execute_video_job
        from visual_assets.schemas import AssetStatus, AssetType, VisualAsset

        async def _scenario():
            ref = await _image_asset_with_file(isolated_assets, "asset_frame_vanish")
            job = VisualAsset(
                asset_id="asset_job_vanish",
                asset_type=AssetType.VIDEO,
                chapter=1,
                scene_id=SCENE,
                title="видео",
                status=AssetStatus.GENERATING,
            )
            job = await isolated_assets.save(job)
            frame_path = isolated_assets.get_file_path(ref)
            assert frame_path is not None
            Path(frame_path).unlink()  # файл исчез между валидацией и исполнением
            await _execute_video_job(
                job.asset_id,
                "движение",
                "comfyicu",
                8.0,
                "1024x576",
                24,
                ref.asset_id,
            )
            return await isolated_assets.get(job.asset_id)

        job = asyncio.run(_scenario())
        assert job is not None
        assert job.status == AssetStatus.FAILED
        assert job.error and "input_image_read_failed" in job.error
        assert job.generation.reference_image_id is None
        assert fake_media_api["posts"] == [], "MediaClient не вызывается при нечитаемом кадре"


# ── 3. MediaClient: тело запроса ───────────────────────────────────


class TestMediaClientVideoBody:
    def test_body_with_input_image(self):
        from core.media_client import MediaClient

        body = MediaClient._video_body(
            "движение",
            8.0,
            "1024x576",
            24,
            "comfyicu",
            input_image=PNG_1PX,
            input_image_filename="f.png",
        )
        img = body["execution"]["input_image"]
        assert base64.b64decode(img["bytes_b64"]) == PNG_1PX
        assert img["filename"] == "f.png"
        assert body["execution"]["media_kind"] == "video"
        assert body["execution"]["preferred_backend"] == "comfyicu"

    def test_body_without_input_image_unchanged(self):
        from core.media_client import MediaClient

        body = MediaClient._video_body("движение", 8.0, "1024x576", 24, "auto")
        assert "input_image" not in body["execution"]
        assert set(body["execution"]) == {
            "media_kind",
            "size",
            "preferred_backend",
            "duration_sec",
            "fps",
        }
