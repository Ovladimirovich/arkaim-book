"""MD-3.2 Route C — /book/assets/generate УДАЛЁН.

После миграции на Arkaim Media Boundary эндпоинт POST /book/assets/generate
удалён (возвращает 404/405). Этот файл тестирует:
  1. Удалённый маршрут действительно возвращает 404/405.
  2. MediaPlanBuilder работает корректно (канонический path).
  3. Execution leakage в план отсутствует.

Запуск (из runtime/):
  .venv\\Scripts\\python -m pytest tests/test_md3_route_c.py -v
"""

from __future__ import annotations

import json
import sys
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
        return {"user_id": "test-user", "role": "admin", "provider": "test", "username": "tester", "display_name": "Test User"}

    _saved = dict(app.dependency_overrides)
    app.dependency_overrides[get_current_user] = _fake_user
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()
    app.dependency_overrides.update(_saved)


# ── Маршрут C удалён ──


class TestRouteCRemoved:
    def test_generate_asset_route_removed(self, client):
        """POST /book/assets/generate → 404/405 (маршрут удалён)."""
        resp = client.post("/book/assets/generate", params={"chapter": 1, "scene_id": SCENE})
        assert resp.status_code in (404, 405)

    def test_generate_asset_unknown_scene_removed(self, client):
        resp = client.post("/book/assets/generate", params={"chapter": 99, "scene_id": "nope"})
        assert resp.status_code in (404, 405)


# ── MediaPlanBuilder standalone tests (канонический path через generate-context) ──


class TestMediaPlanBuilderStandalone:
    def test_plan_built_from_canonical_ctx(self, client):
        """MediaPlan строится Builder'ом из canonical SceneContext."""
        from core.adc_deps import registry as reg
        import asyncio

        b = reg.get("visual_context_builder")
        ctx = asyncio.run(b.build_scene_context(1, SCENE))
        plan = MediaPlanBuilder(generator="comfyui").build_image_plan(ctx, intent="key_frame", created_from="scene_context", style_override="mythic_realism")
        assert plan.source_refs.scene_id == SCENE
        assert plan.visual_style == "mythic_realism"
        assert plan.intent == "key_frame"

    def test_negative_prompt_is_plan_constraint(self, client):
        """Смысловое negative_prompt попадает в план (negative_constraints),
        НЕ в execution-поля."""
        from media_plan.schemas import MediaPlan

        plan = MediaPlan(
            plan_id="plan_md32c000001",
            plan_version="0.1.0",
            media_kind="image",
            prompt="p",
            negative_constraints=["blur, noise"],
        )
        assert plan.negative_constraints == ["blur, noise"]
        assert "negative_prompt" not in plan.to_dict()

    def test_no_execution_fields_in_plan(self, client):
        """Execution-поля НЕ попадают в план; сериализация без banned-полей."""
        import asyncio
        from core.adc_deps import registry as reg

        b = reg.get("visual_context_builder")
        ctx = asyncio.run(b.build_scene_context(1, SCENE))
        plan = MediaPlanBuilder(generator="comfyui").build_image_plan(ctx)
        serialized = json.dumps(plan.to_dict(), ensure_ascii=False)
        for banned in (
            '"model"',
            '"steps"',
            '"seed"',
            '"cfg"',
            '"sampler"',
            '"workflow"',
            '"provider"',
            '"backend"',
            '"quality"',
            '"checkpoint"',
            '"lora"',
            '"size"',
        ):
            assert banned not in serialized
        from media_plan import verify_no_execution_fields

        assert verify_no_execution_fields() == []

    def test_no_second_canonical_path(self, client):
        """Plan не содержит execution-полей; один Builder — canonical path."""
        from core.adc_deps import registry as reg
        import asyncio

        b = reg.get("visual_context_builder")
        ctx = asyncio.run(b.build_scene_context(1, SCENE))
        plan = MediaPlanBuilder(generator="comfyui").build_image_plan(ctx)
        assert "dispatch" not in plan.to_dict()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
