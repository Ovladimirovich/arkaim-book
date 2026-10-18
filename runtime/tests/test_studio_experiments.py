"""История экспериментов — управление статусами и очисткой."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

from test_studio_art_direction import SCENE, _make_session_with_shots  # noqa: E402


@pytest.fixture()
def isolated_session_store(tmp_path, monkeypatch):
    from studio import store as studio_store_mod

    monkeypatch.setattr(studio_store_mod, "_DB_PATH", tmp_path / "studio_exp_test.db")


@pytest.fixture()
def isolated_assets(tmp_path, monkeypatch):
    from core.adc_deps import registry
    from visual_assets import storage as storage_mod

    monkeypatch.setattr(storage_mod, "_DATA_DIR", tmp_path / "visual_assets")
    store = storage_mod.AssetStorage(db_path=tmp_path / "experiments_assets.db")
    had = "asset_store" in registry._instances
    old = registry._instances.get("asset_store")
    registry._instances["asset_store"] = store
    yield store
    if had:
        registry._instances["asset_store"] = old
    else:
        registry._instances.pop("asset_store", None)


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient
    from core.main import app

    return TestClient(app)


def _run(coro):
    """Запустить coroutine в изолированном event loop (для синхронных тестов)."""

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def _save_asset(store, scene_id, status="experimental", shot_id=None):
    from visual_assets.schemas import AssetStatus, AssetType, GenerationParams, VisualAsset
    from visual_assets.storage import generate_asset_id

    asset = VisualAsset(
        asset_id=generate_asset_id(),
        asset_type=AssetType.IMAGE,
        chapter=1,
        scene_id=scene_id,
        title="тестовый кадр",
        status=AssetStatus.COMPLETED,
        prompt_used="test prompt",
        generation=GenerationParams(shot_id=shot_id),
        experiment_status=status,
    )
    return _run(store.save(asset)) or asset


def _save_video(store, scene_id, ref_image_id):
    from visual_assets.schemas import AssetStatus, AssetType, GenerationParams, VisualAsset
    from visual_assets.storage import generate_asset_id

    asset = VisualAsset(
        asset_id=generate_asset_id(),
        asset_type=AssetType.VIDEO,
        chapter=1,
        scene_id=scene_id,
        title="тестовое видео",
        status=AssetStatus.COMPLETED,
        prompt_used="video prompt",
        generation=GenerationParams(reference_image_id=ref_image_id),
        experiment_status="experimental",
    )
    return _run(store.save(asset)) or asset


# ── 1. Создание и маркировка ───────────────────────────────────────


class TestExperimentMarking:
    def test_image_job_marks_experimental(self, client, isolated_assets, isolated_session_store):
        _make_session_with_shots()
        resp = client.post(
            "/studio/image-jobs",
            json={
                "chapter": 1,
                "scene_id": SCENE,
                "prompt": "test prompt",
                "preferred_backend": "mock",
                "title": "test",
            },
        )
        assert resp.status_code == 200, resp.text
        asset_id = resp.json()["data"]["asset_id"]
        asset = _run(isolated_assets.get(asset_id))
        assert asset is not None
        assert asset.experiment_status == "experimental"

    def test_prepared_update_marks_candidate(self, client, isolated_assets, isolated_session_store):
        from studio.prepared_updates import PREPARED_STATUS_DONE

        session_id = _make_session_with_shots()
        prep_resp = client.post(
            f"/studio/{session_id}/prepared-updates",
            json={"shot_id": "shot_001", "backend": "mock"},
        )
        assert prep_resp.status_code == 200
        prep_id = prep_resp.json()["data"]["prepared"]["prepared_id"]
        asset = _save_asset(isolated_assets, SCENE, status="experimental", shot_id="shot_001")
        patch_resp = client.patch(
            f"/studio/{session_id}/prepared-updates/{prep_id}",
            json={"status": PREPARED_STATUS_DONE, "new_asset_id": asset.asset_id},
        )
        assert patch_resp.status_code == 200, patch_resp.text
        updated = _run(isolated_assets.get(asset.asset_id))
        assert updated.experiment_status == "candidate"


# ── 2. Список экспериментов ────────────────────────────────────────


class TestListExperiments:
    def test_list_returns_experiments(self, client, isolated_assets, isolated_session_store):
        session_id = _make_session_with_shots()
        _save_asset(isolated_assets, SCENE, status="experimental", shot_id="shot_001")
        _save_asset(isolated_assets, SCENE, status="experimental", shot_id="shot_002")
        _save_asset(isolated_assets, SCENE, status="approved")

        resp = client.get(f"/studio/{session_id}/experiments")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 3
        assert len(data["experiments"]) == 3
        assert data["groups"]

    def test_filter_by_status(self, client, isolated_assets, isolated_session_store):
        session_id = _make_session_with_shots()
        _save_asset(isolated_assets, SCENE, status="experimental")
        _save_asset(isolated_assets, SCENE, status="candidate")
        _save_asset(isolated_assets, SCENE, status="approved")

        resp = client.get(f"/studio/{session_id}/experiments?status=approved")
        assert resp.status_code == 200
        assert resp.json()["data"]["total"] == 1

    def test_filter_by_shot(self, client, isolated_assets, isolated_session_store):
        session_id = _make_session_with_shots()
        _save_asset(isolated_assets, SCENE, status="experimental", shot_id="shot_001")
        _save_asset(isolated_assets, SCENE, status="experimental", shot_id="shot_002")

        resp = client.get(f"/studio/{session_id}/experiments?shot_id=shot_001")
        assert resp.status_code == 200
        assert resp.json()["data"]["total"] == 1

    def test_pagination(self, client, isolated_assets, isolated_session_store):
        session_id = _make_session_with_shots()
        for _ in range(5):
            _save_asset(isolated_assets, SCENE, status="experimental")

        resp = client.get(f"/studio/{session_id}/experiments?limit=2&offset=0")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 5
        assert len(data["experiments"]) == 2
        assert data["limit"] == 2
        assert data["offset"] == 0


# ── 3. Безопасное удаление ────────────────────────────────────────


class TestDeleteExperiment:
    def test_delete_experimental_success(self, client, isolated_assets, isolated_session_store):
        session_id = _make_session_with_shots()
        asset = _save_asset(isolated_assets, SCENE, status="experimental")
        resp = client.delete(f"/studio/{session_id}/experiments/{asset.asset_id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] == asset.asset_id
        assert _run(isolated_assets.get(asset.asset_id)) is None

    def test_delete_approved_protected(self, client, isolated_assets, isolated_session_store):
        from studio.store import StudioStore

        session_id = _make_session_with_shots()
        asset = _save_asset(isolated_assets, SCENE, status="approved")
        store = StudioStore()
        _run(store.set_approved_image(session_id, asset.asset_id))

        resp = client.delete(f"/studio/{session_id}/experiments/{asset.asset_id}")
        assert resp.status_code == 409

    def test_delete_video_source_protected(self, client, isolated_assets, isolated_session_store):
        session_id = _make_session_with_shots()
        image_asset = _save_asset(isolated_assets, SCENE, status="experimental", shot_id="shot_001")
        _save_video(isolated_assets, SCENE, ref_image_id=image_asset.asset_id)

        resp = client.delete(f"/studio/{session_id}/experiments/{image_asset.asset_id}")
        assert resp.status_code == 409


class TestDeleteBatch:
    def test_batch_deletes_experimental(self, client, isolated_assets, isolated_session_store):
        session_id = _make_session_with_shots()
        ids = []
        for _ in range(3):
            a = _save_asset(isolated_assets, SCENE, status="experimental")
            ids.append(a.asset_id)

        resp = client.post(
            f"/studio/{session_id}/experiments/delete-batch",
            json={"asset_ids": ids},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["deleted_count"] == 3
        assert data["protected"] == []


# ── 4. Архивирование ──────────────────────────────────────────────


class TestArchiveBatch:
    def test_archive_experimental(self, client, isolated_assets, isolated_session_store):
        session_id = _make_session_with_shots()
        asset = _save_asset(isolated_assets, SCENE, status="experimental")

        resp = client.post(
            f"/studio/{session_id}/experiments/archive-batch",
            json={"asset_ids": [asset.asset_id]},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert asset.asset_id in data["archived"]
        updated = _run(isolated_assets.get(asset.asset_id))
        assert updated.experiment_status == "archived"

    def test_archive_protected_fails_gracefully(self, client, isolated_assets, isolated_session_store):
        from studio.store import StudioStore

        session_id = _make_session_with_shots()
        asset = _save_asset(isolated_assets, SCENE, status="approved")
        store = StudioStore()
        _run(store.set_approved_image(session_id, asset.asset_id))

        resp = client.post(
            f"/studio/{session_id}/experiments/archive-batch",
            json={"asset_ids": [asset.asset_id]},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["archived"] == []
        assert len(data["protected"]) == 1
        assert data["protected"][0]["asset_id"] == asset.asset_id


# ── 5. Архивная очистка ───────────────────────────────────────────


class TestArchiveCleanup:
    def test_archive_cleanup_dry_run(self, client, isolated_assets, isolated_session_store):
        """Dry-run: показывает сколько будет архивировано."""
        session_id = _make_session_with_shots()
        _save_asset(isolated_assets, SCENE, status="experimental")

        resp = client.post(
            f"/studio/{session_id}/experiments/archive-cleanup",
            json={"older_than_days": 1, "dry_run": True},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["archived_count"] == 0  # свежие не архивируются
        assert data["dry_run"] is True

    def test_archive_cleanup_protected(self, client, isolated_assets, isolated_session_store):
        """Утверждённый ассет не архивируется."""
        from studio.store import StudioStore

        session_id = _make_session_with_shots()
        asset = _save_asset(isolated_assets, SCENE, status="experimental")
        store = StudioStore()
        _run(store.set_approved_image(session_id, asset.asset_id))

        resp = client.post(
            f"/studio/{session_id}/experiments/archive-cleanup",
            json={"older_than_days": 1, "dry_run": False},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["archived_count"] == 0
        # Утверждённый не должен быть архивирован
        assert asset.asset_id not in data.get("archived", [])
        # Ассет всё ещё experimental
        assert _run(isolated_assets.get(asset.asset_id)).experiment_status == "experimental"


# ── 6. Очистка ────────────────────────────────────────────────────


class TestCleanup:
    def test_cleanup_dry_run_fresh_assets(self, client, isolated_assets, isolated_session_store):
        """Свежие ассеты не попадают под очистку (старше 1 дня)."""
        session_id = _make_session_with_shots()
        _save_asset(isolated_assets, SCENE, status="experimental")

        resp = client.post(
            f"/studio/{session_id}/experiments/cleanup",
            json={"older_than_days": 1, "dry_run": True},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["would_delete"] == 0


class TestMigrate:
    def test_migrate_marks_old_assets(self, client, isolated_assets, isolated_session_store):
        from visual_assets.schemas import AssetStatus, AssetType, VisualAsset
        from visual_assets.storage import generate_asset_id

        session_id = _make_session_with_shots()
        asset = VisualAsset(
            asset_id=generate_asset_id(),
            asset_type=AssetType.IMAGE,
            chapter=1,
            scene_id=SCENE,
            title="старый кадр",
            status=AssetStatus.COMPLETED,
            experiment_status=None,
        )
        _run(isolated_assets.save(asset))

        resp = client.post(f"/studio/{session_id}/experiments/migrate")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["experimental"] == 1

        updated = _run(isolated_assets.get(asset.asset_id))
        assert updated.experiment_status == "experimental"
