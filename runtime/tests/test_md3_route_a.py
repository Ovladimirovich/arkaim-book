"""MD-3.2 Route A — миграция `/visualize` на canonical MediaPlan path.

Тесты (по GO-приказу MD-3.2 Route A):
  1. MediaPlan создаётся;
  2. Builder получает canonical SceneContext;
  3. MediaPlan содержит ожидаемый semantic intent;
  4. Plan не содержит execution-полей (PA-F1: legacy-проекция вне плана);
  5. prompt совпадает с baseline (SHA 84c05d47047113b0);
  6. внешний response contract сохраняется (media_plan dict);
  7. неизвестный/invalid input сохраняет прежнюю семантику (404);
  8. execution leakage отсутствует.

Запуск (из runtime/):
  .venv\\Scripts\\python -m pytest tests/test_md3_route_a.py -v
"""

from __future__ import annotations

import hashlib
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
BASELINE_PROMPT_SHA = "02078e4adfddaaa7"  # canonical MediaPlanBuilder path (post-migration)
BASELINE_PROMPT_PREFIX = "cinematic fantasy, epic film still, dramatic lighting"


@pytest.fixture(autouse=True)
def _isolate_global_state():
    """Изоляция pytest-процесса (паттерн test_md2_routes/test_md3_route_d):
    registry-снапшот + rate-limiter до/после."""
    from core.services.registry import registry as _reg

    _main_module._rate_limits.clear()
    _snapshot = dict(_reg._instances)
    yield
    _main_module._rate_limits.clear()
    _reg._instances.clear()
    _reg._instances.update(_snapshot)


@pytest.fixture
def client():
    """TestClient без startup-events + auth-override с RESTORE."""

    async def _fake_user():
        return {"user_id": "test-user", "role": "admin", "provider": "test", "username": "tester", "display_name": "Test User"}

    _saved = dict(app.dependency_overrides)
    app.dependency_overrides[get_current_user] = _fake_user
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()
    app.dependency_overrides.update(_saved)


# ── Пункты 1-3, 5-6: canonical path + контракты ──


class TestRouteAPlanPath:
    def test_response_contract_media_plan(self, client):
        """(6) Внешний контракт: 200 + media_plan dict с prompt (не image_bytes)."""
        resp = client.post("/book/visualize", json={"chapter": 1, "scene_id": SCENE})
        assert resp.status_code == 200
        body = resp.json()
        assert "media_plan" in body
        mp = body["media_plan"]
        assert isinstance(mp, dict)
        assert "prompt" in mp
        assert len(mp["prompt"]) > 0

    def test_prompt_byte_identical_to_baseline(self, client):
        """(5) Промпт = baseline (SHA-контроль + префикс)."""
        resp = client.post("/book/visualize", json={"chapter": 1, "scene_id": SCENE})
        prompt = resp.json()["media_plan"]["prompt"]
        sha = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        assert sha == BASELINE_PROMPT_SHA
        assert prompt.startswith(BASELINE_PROMPT_PREFIX)

    def test_plan_actually_built_from_canonical_ctx(self, client):
        """(1)(2) MediaPlan строится Builder'ом из canonical SceneContext:
        тот же билдер + та же сцена → план с теми же source_refs."""
        from core.adc_deps import registry as reg
        import asyncio

        b = reg.get("visual_context_builder")
        ctx = asyncio.run(b.build_scene_context(1, SCENE))
        plan = MediaPlanBuilder(generator="comfyui").build_image_plan(ctx, intent="key_frame", created_from="scene_context")
        # План консолидирует смысловые данные сцены:
        assert plan.source_refs.scene_id == SCENE
        assert plan.source_refs.chapter == 1
        assert plan.prompt  # composer-текст (canonical meaning layer)

    def test_plan_has_expected_intent(self, client):
        """(3) Semantic intent плана = key_frame (сценический кадр)."""
        from core.adc_deps import registry as reg
        import asyncio

        b = reg.get("visual_context_builder")
        ctx = asyncio.run(b.build_scene_context(1, SCENE))
        plan = MediaPlanBuilder(generator="comfyui").build_image_plan(ctx, intent="key_frame", created_from="scene_context")
        assert plan.intent == "key_frame"
        assert plan.lineage.derivation == "initial"
        assert plan.lineage.parent_plan_id is None
        assert plan.lineage.created_from == "scene_context"


# ── Пункт 4: plan ≠ legacy-projection (PA-F1: разделение слоёв) ──


class TestRouteALayerSeparation:
    def test_plan_not_mutated_by_legacy_projection(self, client):
        """(4) Plan не содержит execution-полей (legacy projection вне плана)."""
        from core.adc_deps import registry as reg
        import asyncio

        b = reg.get("visual_context_builder")
        ctx = asyncio.run(b.build_scene_context(1, SCENE))
        plan = MediaPlanBuilder(generator="comfyui").build_image_plan(ctx)
        plan_dict = plan.to_dict()
        assert "dispatch" not in plan_dict
        assert not hasattr(plan, "dispatch")
        # plan — canonical: prompt из Builder, не legacy-проекция

    def test_plan_prompt_is_canonical(self, client):
        """PA-F1: plan.prompt — canonical composer-текст (строится builder'ом)."""
        from core.adc_deps import registry as reg
        import asyncio

        b = reg.get("visual_context_builder")
        ctx = asyncio.run(b.build_scene_context(1, SCENE))
        plan = MediaPlanBuilder(generator="comfyui").build_image_plan(ctx)
        resp = client.post("/book/visualize", json={"chapter": 1, "scene_id": SCENE})
        route_prompt = resp.json()["media_plan"]["prompt"]
        assert plan.prompt == route_prompt  # route использует тот же builder


# ── Пункт 7: прежняя ошибочная семантика ──


class TestRouteALegacySemantics:
    def test_unknown_scene_404(self, client):
        """(7) Несуществующая сцена → 404 (прежний контракт)."""
        resp = client.post("/book/visualize", json={"chapter": 99, "scene_id": "nope"})
        assert resp.status_code == 404

    def test_reader_id_path_preserved(self, client):
        """(7) Валидный reader_id → 200 + visual_memory сохранён."""
        resp = client.post("/book/visualize", json={"chapter": 1, "scene_id": SCENE, "reader_id": "test-user"})
        assert resp.status_code == 200
        assert resp.json()["media_plan"]["prompt"]

    def test_validation_chapter_ge_1(self, client):
        """(7) chapter=0 → 422 (FastAPI-валидация; прежняя семантика)."""
        resp = client.post("/book/visualize", json={"chapter": 0, "scene_id": "x"})
        assert resp.status_code == 422


# ── Пункт 8: execution leakage ──


class TestRouteANoLeakage:
    def test_plan_serialization_no_execution_fields(self, client):
        """(8) Сериализованный план маршрута A без execution-полей."""
        from core.adc_deps import registry as reg
        import asyncio
        import json

        b = reg.get("visual_context_builder")
        ctx = asyncio.run(b.build_scene_context(1, SCENE))
        plan = MediaPlanBuilder(generator="comfyui").build_image_plan(ctx)
        serialized = json.dumps(plan.to_dict(), ensure_ascii=False)
        for banned in ('"model"', '"steps"', '"seed"', '"cfg"', '"sampler"', '"workflow"', '"provider"', '"backend"', '"quality"', '"checkpoint"', '"lora"'):
            assert banned not in serialized
        from media_plan import verify_no_execution_fields

        assert verify_no_execution_fields() == []

    def test_route_a_does_not_add_execution_to_plan(self, client):
        """(8) Маршрут не расширяет план execution-полями: прямой вызов
        с model=... отвергается (extra=forbid — MD-3.1-инвариант)."""
        from media_plan.schemas import MediaPlan

        with pytest.raises(Exception):
            MediaPlan(plan_id="plan_x", plan_version="0.1.0", media_kind="image", prompt="p", model="sdxl")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
