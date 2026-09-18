"""MD-3.2 Route E — /book/film/{id}/scenes/{id}/shots/{id}/generate УДАЛЁН.

После миграции на Arkaim Media Boundary маршрут генерации шота удалён.
Этот файл тестирует:
  1. Удалённый маршрут возвращает 404/405.
  2. MediaPlanBuilder работает корректно (канонический path).
  3. Execution leakage в план отсутствует.

Запуск (из runtime/):
  .venv\\Scripts\\python -m pytest tests/test_md3_route_e.py -v
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import pytest

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
sys.path.insert(0, str(CORE_DIR))

from fastapi.testclient import TestClient

from core.main import app
from core import main as _main_module
from auth.rbac import get_current_user

from media_plan import MediaPlanBuilder  # noqa: E402

SCENE = "conflict_гиперборея_материальный_путь_атлантиды"
SHA_SHOT = "53a10b4f48714232"  # «test shot» (canonical film_shot intent, post-migration)


@pytest.fixture(autouse=True)
def _isolate_global_state():
    from core.services.registry import registry as _reg
    _main_module._rate_limits.clear()
    _snapshot = dict(_reg._instances)
    yield
    _main_module._rate_limits.clear()
    _reg._instances.clear()
    _reg._instances.update(_snapshot)


@pytest.fixture
def client():
    async def _fake_user():
        return {"user_id": "test-user", "role": "admin", "provider": "test",
                "username": "tester", "display_name": "Test User"}
    _saved = dict(app.dependency_overrides)
    app.dependency_overrides[get_current_user] = _fake_user
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()
    app.dependency_overrides.update(_saved)


@pytest.fixture
def film_client(client, monkeypatch):
    """Изолированная film-БД (как test_md2_routes.film_client; НЕ трогает основную БД)."""
    from film_studio.store import FilmProjectStore
    db_dir = Path(__file__).resolve().parent / ".tmp_md3e"
    db_dir.mkdir(exist_ok=True)
    db_file = db_dir / f"film_test_{int(time.time() * 1000)}.db"
    store = FilmProjectStore(db_path=db_file)

    def _get_store():
        return store

    import core.routes.film_studio as fs_routes
    monkeypatch.setattr(fs_routes, "_get_store", _get_store)
    yield client
    try:
        db_file.unlink(missing_ok=True)
    except OSError:
        pass


def _setup_film_project(client):
    proj = client.post("/book/film/create", params={"title": "MD3-2 E", "style": "cinematic_fantasy"})
    assert proj.status_code == 200
    project_id = proj.json()["data"]["id"]
    scene = client.post(f"/book/film/{project_id}/scenes", params={"scene_id": SCENE})
    assert scene.status_code == 200
    scene_db_id = scene.json()["data"]["id"]
    shot = client.post(f"/book/film/{project_id}/scenes/{scene_db_id}/shots",
                       params={"prompt": "test shot"})
    assert shot.status_code == 200
    shot_data = shot.json()["data"]
    shot_id = shot_data["id"] if "id" in shot_data else shot_data["versions"][0]["id"]
    return project_id, scene_db_id, shot_id


# ── Маршрут E удалён ──


class TestRouteERemoved:
    def test_shot_generate_route_removed(self, film_client):
        """POST /book/film/{id}/scenes/{id}/shots/{id}/generate → 404/405 (удалён)."""
        pid, sid, shid = _setup_film_project(film_client)
        resp = film_client.post(f"/book/film/{pid}/scenes/{sid}/shots/{shid}/generate")
        assert resp.status_code in (404, 405)

    def test_assemble_route_removed(self, film_client):
        """POST /book/film/{id}/assemble удалён."""
        pid, _, _ = _setup_film_project(film_client)
        resp = film_client.post(f"/book/film/{pid}/assemble")
        assert resp.status_code in (404, 405)

    def test_assemble_status_route_removed(self, film_client):
        """GET /book/film/{id}/assemble/status удалён."""
        pid, _, _ = _setup_film_project(film_client)
        resp = film_client.get(f"/book/film/{pid}/assemble/status")
        assert resp.status_code in (404, 405)


# ── MediaPlanBuilder standalone tests (film_shot intent) ──


class TestRouteEPlanBuilderStandalone:
    def test_plan_built_from_canonical_ctx(self, film_client):
        """MediaPlan строится Builder'ом из canonical SceneContext."""
        import asyncio
        from core.adc_deps import registry as reg
        b = reg.get("visual_context_builder")
        ctx = asyncio.run(b.build_scene_context(1, SCENE))
        plan = MediaPlanBuilder(generator="comfyui").build_image_plan(
            ctx, intent="film_shot", created_from="film_shot",
            style_override="cinematic_fantasy", custom_prompt="test shot")
        assert plan.prompt == "test shot"
        assert plan.visual_style == "cinematic_fantasy"
        assert plan.lineage.created_from == "film_shot"
        assert plan.source_refs.scene_id == SCENE

    def test_no_execution_fields_in_plan(self, film_client):
        """Execution-поля НЕ попадают в план. ВАЖНО: camera/duration_sec/fps
        в MediaPlan — СЕМАНТИЧЕСКИЕ поля (composition/video-intent) — НЕ
        execution: image_kwargs = prompt/size/preferred. Проверяем РЕАЛЬНЫЕ
        execution-поля."""
        import asyncio
        from core.adc_deps import registry as reg
        b = reg.get("visual_context_builder")
        ctx = asyncio.run(b.build_scene_context(1, SCENE))
        plan = MediaPlanBuilder(generator="comfyui").build_image_plan(
            ctx, intent="film_shot", created_from="film_shot", custom_prompt="test shot")
        serialized = json.dumps(plan.to_dict(), ensure_ascii=False)
        for banned in ('"model"', '"steps"', '"seed"', '"cfg"', '"sampler"',
                       '"workflow"', '"provider"', '"backend"', '"quality"',
                       '"checkpoint"', '"lora"', '"size"', '"negative_prompt"'):
            assert banned not in serialized
        from media_plan import verify_no_execution_fields
        assert verify_no_execution_fields() == []

    def test_no_second_canonical_path(self, film_client):
        """Plan не содержит execution-полей; один Builder; проекция — после плана."""
        import asyncio
        from core.adc_deps import registry as reg
        b = reg.get("visual_context_builder")
        ctx = asyncio.run(b.build_scene_context(1, SCENE))
        plan = MediaPlanBuilder(generator="comfyui").build_image_plan(
            ctx, intent="film_shot", created_from="film_shot", custom_prompt="test shot")
        assert "dispatch" not in plan.to_dict()

    def test_film_shot_prompt_baseline(self, film_client):
        """Промпт шота байт-в-байт (SHA baseline)."""
        import asyncio
        from core.adc_deps import registry as reg
        b = reg.get("visual_context_builder")
        ctx = asyncio.run(b.build_scene_context(1, SCENE))
        plan = MediaPlanBuilder(generator="comfyui").build_image_plan(
            ctx, intent="film_shot", created_from="film_shot", custom_prompt="test shot")
        prompt = plan.prompt
        sha = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        assert sha == SHA_SHOT
        assert prompt == "test shot"  # custom_prompt overrides default text


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
