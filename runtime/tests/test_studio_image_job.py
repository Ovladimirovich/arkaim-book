"""Производственная модель Studio: промпт → изображение → утверждение → видео.

Offline-проверки (без live, новые облачные запуски НЕ выполняются):
  POST /studio/image-jobs   — изображение-задание по промпту (фон, MediaClient
                              с подменённым HTTP) → AssetStorage → completed/failed
  POST /studio/{id}/approve-image — утверждение готового IMAGE-ассета кадром
                              сцены (session.approved_image_asset_id)
  POST /studio/video-jobs   — привязка утверждённого кадра (image_asset_id →
                              generation.reference_image_id, провенанс Arkaim)
  MediaClient.generate_image_with_meta — bytes + provenance

Схема scenario-теста: байты изображения — 1x1 PNG (сеть не используется).

Запуск (из runtime/):
  python -m pytest tests/test_studio_image_job.py -v
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

SCENE = "conflict_гиперборея_материальный_путь_атлантиды"  # chapter 1
PLAN_ID = "plan_img_test_001"

# 1x1 PNG — валидные magic-bytes для AssetStorage.save_file (определение png)
PNG_1PX = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture()
def isolated_assets(tmp_path, monkeypatch):
    """AssetStorage на временных хранилищах: рабочие БД/файлы не трогаются."""
    from core.adc_deps import registry
    from visual_assets import storage as storage_mod

    monkeypatch.setattr(storage_mod, "_DATA_DIR", tmp_path / "visual_assets")
    store = storage_mod.AssetStorage(db_path=tmp_path / "studio_image_jobs.db")
    had = "asset_store" in registry._instances
    old = registry._instances.get("asset_store")
    registry._instances["asset_store"] = store
    yield store
    if had:
        registry._instances["asset_store"] = old
    else:
        registry._instances.pop("asset_store", None)


@pytest.fixture()
def isolated_session_store(tmp_path, monkeypatch):
    """StudioStore на временной БД: рабочий data/studio.db не трогается."""
    from studio import store as studio_store_mod

    monkeypatch.setattr(studio_store_mod, "_DB_PATH", tmp_path / "studio_test.db")
    yield


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
    (1x1 PNG + provenance agnes). Ответ с "error" → HTTP-ошибка.
    """
    import core.media_client as mc

    state: dict = {
        "payloads": [],
        "last": {},
        "default": {
            "bytes_b64": base64.b64encode(PNG_1PX).decode("ascii"),
            "media_id": "media_img_001",
            "backend": "agnes",
            "workflow_used": "agnes_txt2img.json",
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


def _image_payload(**overrides) -> dict:
    payload = {
        "chapter": 1,
        "scene_id": SCENE,
        "prompt": "cinematic fantasy, key frame, эпический кадр Аркаима",
        "plan_id": PLAN_ID,
        "preferred_backend": "agnes",
        "size": "1024x1024",
    }
    payload.update(overrides)
    return payload


async def _make_asset(store, asset_id: str, asset_type: str, status: str):
    from visual_assets.schemas import AssetStatus, AssetType, VisualAsset

    asset = VisualAsset(
        asset_id=asset_id,
        asset_type=AssetType(asset_type),
        chapter=1,
        scene_id=SCENE,
        title=f"test {asset_id}",
        status=AssetStatus(status),
    )
    return await store.save(asset)


async def _make_asset_with_file(store, asset_id: str, asset_type: str, status: str, data: bytes = PNG_1PX):
    """Ассет с ФАЙЛОМ на диске — обязателен для i2v-референса (video-jobs читает байты)."""
    asset = await _make_asset(store, asset_id, asset_type, status)
    asset.file_path = store.save_file(asset.asset_id, asset.asset_type, data)
    return await store.save(asset)


# ── 1. Изображение-задание: запуск → статус → файл ───────────────


class TestImageJobOffline:
    def test_image_job_completes(self, client, isolated_assets, fake_media_api):
        resp = client.post("/studio/image-jobs", json=_image_payload())
        assert resp.status_code == 200, resp.text
        started = resp.json()["data"]
        assert started["status"] == "generating"
        assert started["plan_id"] == PLAN_ID
        asset_id = started["asset_id"]

        got = client.get(f"/book/assets/{asset_id}")
        assert got.status_code == 200
        asset = got.json()["data"]
        assert asset["status"] == "completed"
        assert asset["asset_type"] == "image"
        assert asset["scene_id"] == SCENE
        # Связь вариантов: общий plan_id (сравнение вариантов на клиенте)
        assert asset["generation"]["plan_id"] == PLAN_ID
        # Provenance реальной интеграции (agnes через arkaim-media)
        assert asset["generation"]["workflow_used"] == "agnes_txt2img.json"
        assert asset["generation"]["media_id"] == "media_img_001"
        assert asset["generation"]["backend"] == "agnes"
        # Выбор исполнителя дошёл до запроса arkaim-media
        assert fake_media_api["last"]["body"]["execution"]["preferred_backend"] == "agnes"
        assert fake_media_api["last"]["body"]["execution"]["media_kind"] == "image"
        assert fake_media_api["last"]["body"]["plan"]["prompt"] == _image_payload()["prompt"]

        opened = client.get(f"/book/assets/{asset_id}/file")
        assert opened.status_code == 200
        assert opened.headers["content-type"].startswith("image/png")
        assert opened.content == PNG_1PX

    def test_image_job_variants_share_plan_id(self, client, isolated_assets, fake_media_api):
        """Варианты одного промпта — несколько ассетов с общим plan_id."""
        first = client.post("/studio/image-jobs", json=_image_payload()).json()["data"]
        second = client.post("/studio/image-jobs", json=_image_payload()).json()["data"]
        assert first["asset_id"] != second["asset_id"]
        assert first["plan_id"] == second["plan_id"] == PLAN_ID

        images = client.get(f"/book/assets?asset_type=image&scene_id={SCENE}").json()["data"]
        variant_ids = [a["asset_id"] for a in images if (a.get("generation") or {}).get("plan_id") == PLAN_ID]
        assert {first["asset_id"], second["asset_id"]} <= set(variant_ids)

    def test_image_job_failed_shows_error(self, client, isolated_assets, fake_media_api):
        fake_media_api["payloads"] = [{"status": 500, "error": {"code": "GENERATION_FAILED"}}]

        resp = client.post("/studio/image-jobs", json=_image_payload())
        assert resp.status_code == 200, resp.text
        asset_id = resp.json()["data"]["asset_id"]

        asset = client.get(f"/book/assets/{asset_id}").json()["data"]
        assert asset["status"] == "failed"
        assert asset["error"] and "media_backend_error: GENERATION_FAILED" in asset["error"]
        assert client.get(f"/book/assets/{asset_id}/file").status_code == 404

    def test_unknown_scene_rejected(self, client, isolated_assets, fake_media_api):
        resp = client.post("/studio/image-jobs", json=_image_payload(scene_id="no_such_scene"))
        assert resp.status_code == 404


# ── 2. Утверждение изображения кадром сцены ──────────────────────


class TestApproveImage:
    @staticmethod
    def _create_session():
        """Создать сессию и закрыть соединение (иначе процесс виснет на aiosqlite)."""
        from studio.store import StudioStore

        async def _run():
            store = StudioStore()
            try:
                return await store.create_session(
                    user_id="admin",
                    title="тест",
                    chapter=1,
                    scene_id=SCENE,
                )
            finally:
                await store.close()

        return asyncio.run(_run())

    @staticmethod
    def _get_session(session_id: str):
        from studio.store import StudioStore

        async def _run():
            store = StudioStore()
            try:
                return await store.get_session(session_id)
            finally:
                await store.close()

        return asyncio.run(_run())

    def test_approve_completed_image(self, client, isolated_assets, isolated_session_store, fake_media_api):
        session = self._create_session()

        # Готовый IMAGE-ассет через штатный image-jobs
        resp = client.post("/studio/image-jobs", json=_image_payload())
        asset_id = resp.json()["data"]["asset_id"]
        assert client.get(f"/book/assets/{asset_id}").json()["data"]["status"] == "completed"

        ok = client.post(f"/studio/{session.session_id}/approve-image?asset_id={asset_id}")
        assert ok.status_code == 200, ok.text
        assert ok.json()["data"]["approved_image_asset_id"] == asset_id

        saved = self._get_session(session.session_id)
        assert saved is not None
        assert saved.approved_image_asset_id == asset_id

    def test_approve_rejects_wrong_types(self, client, isolated_assets, isolated_session_store, fake_media_api):
        session = self._create_session()

        # Видео-ассет утвердить кадром нельзя
        asyncio.run(_make_asset(isolated_assets, "asset_vid_x", "video", "completed"))
        r = client.post(f"/studio/{session.session_id}/approve-image?asset_id=asset_vid_x")
        assert r.status_code == 400

        # Неготовое (generating) изображение утвердить нельзя
        asyncio.run(_make_asset(isolated_assets, "asset_img_busy", "image", "generating"))
        r = client.post(f"/studio/{session.session_id}/approve-image?asset_id=asset_img_busy")
        assert r.status_code == 409

        # Неизвестные сессия/ассет
        assert client.post("/studio/session_missing/approve-image?asset_id=x").status_code == 404
        asyncio.run(_make_asset(isolated_assets, "asset_img_ok", "image", "completed"))
        assert client.post(f"/studio/{session.session_id}/approve-image?asset_id=asset_nope").status_code == 404

    def test_approve_can_be_cleared(self, client, isolated_assets, isolated_session_store, fake_media_api):
        session = self._create_session()
        asyncio.run(_make_asset(isolated_assets, "asset_img_c", "image", "completed"))
        client.post(f"/studio/{session.session_id}/approve-image?asset_id=asset_img_c")

        cleared = client.post(f"/studio/{session.session_id}/approve-image?asset_id=")
        assert cleared.status_code == 200
        assert cleared.json()["data"]["approved_image_asset_id"] is None

        saved = self._get_session(session.session_id)
        assert saved.approved_image_asset_id is None


# ── 3. Видео на основе утверждённого кадра (провенанс) ───────────


class TestVideoJobWithReferenceImage:
    def test_video_job_links_reference_image(self, client, isolated_assets, isolated_session_store, fake_media_api):
        # i2v: референс обязан иметь читаемый файл (video-jobs читает байты из AssetStorage)
        asyncio.run(_make_asset_with_file(isolated_assets, "asset_frame_1", "image", "completed"))

        resp = client.post(
            "/studio/video-jobs",
            json={
                "chapter": 1,
                "scene_id": SCENE,
                "prompt": "движение: медленный наезд камеры",
                "plan_id": "plan_video_1",
                "preferred_backend": "mock",
                "duration_sec": 8.0,
                "fps": 24,
                "size": "1024x576",
                "image_asset_id": "asset_frame_1",
            },
        )
        assert resp.status_code == 200, resp.text
        asset_id = resp.json()["data"]["asset_id"]

        asset = client.get(f"/book/assets/{asset_id}").json()["data"]
        # reference фиксируется после ФАКТИЧЕСКОЙ передачи (задание completed)
        assert asset["status"] == "completed"
        assert asset["generation"]["reference_image_id"] == "asset_frame_1"
        assert asset["generation"]["plan_id"] == "plan_video_1"

    def test_video_job_reference_without_file_rejected(self, client, isolated_assets, isolated_session_store, fake_media_api):
        """Ассет-референс без файла → 409 ДО запуска (не тихий запуск без кадра)."""
        asyncio.run(_make_asset(isolated_assets, "asset_frame_nofile", "image", "completed"))
        resp = client.post(
            "/studio/video-jobs",
            json={
                "chapter": 1,
                "scene_id": SCENE,
                "prompt": "движение",
                "image_asset_id": "asset_frame_nofile",
            },
        )
        assert resp.status_code == 409

    def test_video_job_rejects_non_image_reference(self, client, isolated_assets, isolated_session_store, fake_media_api):
        asyncio.run(_make_asset(isolated_assets, "asset_vid_ref", "video", "completed"))
        resp = client.post(
            "/studio/video-jobs",
            json={
                "chapter": 1,
                "scene_id": SCENE,
                "prompt": "x" * 8,
                "image_asset_id": "asset_vid_ref",
            },
        )
        assert resp.status_code == 400


# ── 4. MediaClient: image bytes + provenance ─────────────────────


class TestMediaClientImageMeta:
    def test_generate_image_with_meta(self, fake_media_api):
        from core.media_client import MediaClient

        res = asyncio.run(MediaClient().generate_image_with_meta("кадр", size="1024x1024", preferred_backend="agnes"))
        assert res.data == PNG_1PX
        assert res.media_id == "media_img_001"
        assert res.backend == "agnes"
        assert res.workflow_used == "agnes_txt2img.json"
        assert fake_media_api["last"]["body"]["execution"]["preferred_backend"] == "agnes"
        assert fake_media_api["last"]["body"]["execution"]["media_kind"] == "image"

    def test_generate_image_bytes_contract_unchanged(self, fake_media_api):
        """Прежний интерфейс не меняется: generate → только bytes."""
        from core.media_client import MediaClient

        data = asyncio.run(MediaClient().generate("кадр", size="1024x1024"))
        assert isinstance(data, bytes)
        assert data == PNG_1PX
