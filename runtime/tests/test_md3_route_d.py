"""MD-3.2 Route D — миграция на canonical MediaPlan path.

Тесты фиксируют (ADR_MEDIA_PLAN_V0 + GO-приказ MD-3.2 Route D):
  1. Route D строит MediaPlan через MediaPlanBuilder (canonical);
  2. внешний контракт неизменен: {"media_plan": {...}};
  3. промпт byte-identical прежнему composer-пути (замороженный контракт);
  4. план несёт provenance/temporal из SceneContext (наследование MD-2);
  5. execution leakage в план отсутствует;
  6. generate-character/-location маршруты удалены (404/405).

Запуск (из runtime/):
  .venv\\Scripts\\python -m pytest tests/test_md3_route_d.py -v
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
from visual.visual_context import VisualContext  # noqa: E402

SCENE = "conflict_гиперборея_материальный_путь_атлантиды"


@pytest.fixture(autouse=True)
def _isolate_global_state():
    """Изоляция от кумулятивного состояния pytest-процесса (паттерн test_md2_routes).

    1. registry._instances: откат к снапшоту после каждого теста;
    2. main._rate_limits: сброс ДО и ПОСЛЕ (pre-existing M8.1-дефект
       429-пути: AttributeError → 500; тест-гигиена, не фикс продукта).
    """
    from core.services.registry import registry as _reg
    _main_module._rate_limits.clear()
    _snapshot = dict(_reg._instances)
    yield
    _main_module._rate_limits.clear()
    _reg._instances.clear()
    _reg._instances.update(_snapshot)


@pytest.fixture
def client():
    """TestClient без startup-events (паттерн test_md2_routes) + auth-override
    с RESTORE."""
    async def _fake_user():
        return {"user_id": "test-user", "role": "admin", "provider": "test",
                "username": "tester", "display_name": "Test User"}
    _saved = dict(app.dependency_overrides)
    app.dependency_overrides[get_current_user] = _fake_user
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()
    app.dependency_overrides.update(_saved)


# ── 1-3. Canonical path + внешний контракт generate-context ──


class TestRouteDGenerateContextPlanPath:
    def test_200_and_media_plan_contract(self, client):
        """Response-контракт: 200 + media_plan dict с prompt."""
        resp = client.post("/book/assets/generate-context",
                           params={"chapter": 1, "scene_id": SCENE,
                                   "generator": "comfyui", "size": "1024x576"})
        assert resp.status_code == 200
        data = resp.json()
        assert "media_plan" in data
        mp = data["media_plan"]
        assert isinstance(mp, dict)
        assert "prompt" in mp
        assert len(mp["prompt"]) > 0

    def test_plan_actually_built_by_builder(self, client):
        """MediaPlanBuilder строит план из того же ctx — доказательство
        единственного canonical path: план-промпт == route prompt."""
        from core.adc_deps import registry as reg
        import asyncio
        b = reg.get("visual_context_builder")
        ctx = asyncio.run(b.build_scene_context(1, SCENE))
        plan = MediaPlanBuilder(generator="comfyui").build_image_plan(ctx)
        resp = client.post("/book/assets/generate-context",
                           params={"chapter": 1, "scene_id": SCENE, "generator": "comfyui"})
        mp = resp.json()["media_plan"]
        assert plan.prompt == mp["prompt"]

    def test_prompt_byte_identical_to_composer_baseline(self, client):
        """Замороженный промпт-контракт: текст = composer(comfyui)-рендер."""
        from visual.prompt_composer import PromptComposer
        from core.adc_deps import registry as reg
        import asyncio
        b = reg.get("visual_context_builder")
        ctx = asyncio.run(b.build_scene_context(1, SCENE))
        expected = PromptComposer(generator="comfyui").compose(ctx)
        resp = client.post("/book/assets/generate-context",
                           params={"chapter": 1, "scene_id": SCENE, "generator": "comfyui"})
        assert resp.json()["media_plan"]["prompt"] == expected

    def test_unknown_scene_returns_media_plan_or_404(self, client):
        """Unknown-scene: либо 200 с media_plan, либо 404 — зависит от
        валидации genome. Главное: response не содержит image_bytes."""
        resp = client.post("/book/assets/generate-context",
                           params={"chapter": 99, "scene_id": "nope"})
        if resp.status_code == 200:
            data = resp.json()
            assert "media_plan" in data
            assert "image_bytes" not in data
        else:
            assert resp.status_code in (404, 422)


# ── 4-5. Наследование MD-2 в плане маршрута D ──


class TestRouteDPlanInheritance:
    def test_plan_carries_scene_context_refs(self, client):
        """План строится из SceneContext: source_refs/temporal/provenance
        наследуются (инвариант ADR_MEDIA_PLAN_V0 D3)."""
        from core.adc_deps import registry as reg
        import asyncio
        b = reg.get("visual_context_builder")
        ctx = asyncio.run(b.build_scene_context(1, SCENE))
        plan = MediaPlanBuilder(generator="comfyui").build_image_plan(ctx)
        assert plan.source_refs.scene_id == SCENE
        assert plan.source_refs.chapter == 1
        if plan.temporal_context is not None:
            assert plan.temporal_context.epoch_id
            assert plan.provenance == plan.temporal_context.provenance

    def test_plan_no_execution_leakage(self, client):
        """Запрет не ослаблен: маршрут не добавляет execution-полей."""
        from media_plan import verify_no_execution_fields
        assert verify_no_execution_fields() == []
        from core.adc_deps import registry as reg
        import asyncio
        b = reg.get("visual_context_builder")
        ctx = asyncio.run(b.build_scene_context(1, SCENE))
        plan = MediaPlanBuilder(generator="comfyui").build_image_plan(ctx)
        serialized = json.dumps(plan.to_dict(), ensure_ascii=False)
        for banned in ('"model"', '"steps"', '"seed"', '"cfg"', '"sampler"',
                        '"workflow"', '"provider"', '"backend"', '"quality"'):
            assert banned not in serialized


# ── 6. generate-character и generate-location УДАЛЕНЫ ──


class TestRouteDRemovedCharacterLocation:
    def test_generate_character_removed(self, client):
        resp = client.post("/book/assets/generate-character",
                           params={"character_id": "Световит"})
        assert resp.status_code in (404, 405)

    def test_generate_location_removed(self, client):
        resp = client.post("/book/assets/generate-location",
                           params={"location_id": "граница миров"})
        assert resp.status_code in (404, 405)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
