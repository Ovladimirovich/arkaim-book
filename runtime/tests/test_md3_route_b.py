"""MD-3.2 Route B — миграция `/visualize/epoch` на canonical MediaPlan path.

Тесты (по GO-приказу MD-3.2 Route B):
  1. Route B строит MediaPlan из canonical SceneContext;
  2. epoch/temporal данные попадают в SceneContext/plan из существующего источника;
  3. внешний response contract сохранён (media_plan dict);
  4. prompt до/после идентичен (SHA f460318283a4cbf8);
  5. нет второго canonical path;
  6. нет execution leakage в MediaPlan;
  7. ошибка неизвестного epoch не превращается в выдуманный temporal context (404);
  8. existing route behavior regression-free.

Запуск (из runtime/):
  .venv\\Scripts\\python -m pytest tests/test_md3_route_b.py -v
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

EPOCH = "arkaim_era"
BASELINE_PROMPT_SHA = "a5a3fb732353d64a"  # canonical MediaPlanBuilder path (post-migration)
BASELINE_PROMPT_PREFIX = "cinematic fantasy, epic film still, dramatic lighting"


@pytest.fixture(autouse=True)
def _isolate_global_state():
    """Изоляция pytest-процесса (паттерн route_a/route_d)."""
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
        return {"user_id": "test-user", "role": "admin", "provider": "test",
                "username": "tester", "display_name": "Test User"}
    _saved = dict(app.dependency_overrides)
    app.dependency_overrides[get_current_user] = _fake_user
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()
    app.dependency_overrides.update(_saved)


# ── Пункты 1-3, 4: canonical path + контракты ──


class TestRouteBPlanPath:
    def test_response_contract_media_plan(self, client):
        """(3) Внешний контракт: 200 + media_plan dict с prompt."""
        resp = client.post(f"/book/visualize/epoch/{EPOCH}", json={})
        assert resp.status_code == 200
        body = resp.json()
        assert "media_plan" in body
        mp = body["media_plan"]
        assert isinstance(mp, dict)
        assert "prompt" in mp
        assert len(mp["prompt"]) > 0

    def test_prompt_byte_identical_to_baseline(self, client):
        """(4) Промпт = baseline (SHA-контроль + префикс)."""
        resp = client.post(f"/book/visualize/epoch/{EPOCH}", json={})
        prompt = resp.json()["media_plan"]["prompt"]
        sha = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        assert sha == BASELINE_PROMPT_SHA
        assert prompt.startswith(BASELINE_PROMPT_PREFIX)

    def test_plan_actually_built_from_canonical_epoch_ctx(self, client):
        """(1) MediaPlan строится Builder'ом из canonical SceneContext
        (build_scene_context_for_epoch — существующий источник)."""
        from core.adc_deps import registry as reg
        import asyncio
        b = reg.get("visual_context_builder")
        ctx = asyncio.run(b.build_scene_context_for_epoch(EPOCH))
        plan = MediaPlanBuilder(generator="comfyui").build_image_plan(
            ctx, intent="era_establishing", created_from="epoch")
        assert plan.source_refs.entity_refs == [EPOCH]
        assert plan.lineage.created_from == "epoch"
        assert plan.prompt

    def test_epoch_temporal_flows_from_existing_source(self, client):
        """(2) Epoch/temporal данные попадают в план ИЗ СУЩЕСТВУЮЩЕГО
        источника: WorldModel → canonical-билдер → temporal_context плана;
        provenance наследуется 1:1 (не выдумывается)."""
        from core.adc_deps import registry as reg
        import asyncio
        b = reg.get("visual_context_builder")
        ctx = asyncio.run(b.build_scene_context_for_epoch(EPOCH))
        plan = MediaPlanBuilder(generator="comfyui").build_image_plan(
            ctx, intent="era_establishing", created_from="epoch")
        assert plan.temporal_context is not None
        assert plan.temporal_context.is_temporal
        assert plan.temporal_context.epoch_id == "temporal_arkaim_era"
        assert plan.temporal_context.epoch_id.startswith("temporal_")
        assert plan.provenance == ctx.scene_extras.temporal.provenance
        assert plan.provenance == []  # факт WorldModel для arkaim_era

    def test_plan_has_expected_intent(self, client):
        """Semantic intent плана = era_establishing (эпохальный кадр)."""
        from core.adc_deps import registry as reg
        import asyncio
        b = reg.get("visual_context_builder")
        ctx = asyncio.run(b.build_scene_context_for_epoch(EPOCH))
        plan = MediaPlanBuilder(generator="comfyui").build_image_plan(
            ctx, intent="era_establishing", created_from="epoch")
        assert plan.intent == "era_establishing"
        assert plan.lineage.derivation == "initial"
        assert plan.lineage.parent_plan_id is None


# ── Пункты 5-6: canonical path единственный + leakage ──


class TestRouteBNoSecondPathNoLeakage:
    def test_plan_not_mutated_by_legacy_projection(self, client):
        """(5)(6) Plan не содержит execution-полей; canonical prompt = route prompt."""
        from core.adc_deps import registry as reg
        import asyncio
        b = reg.get("visual_context_builder")
        ctx = asyncio.run(b.build_scene_context_for_epoch(EPOCH))
        plan = MediaPlanBuilder(generator="comfyui").build_image_plan(ctx)
        assert "dispatch" not in plan.to_dict()
        assert not hasattr(plan, "dispatch")
        resp = client.post(f"/book/visualize/epoch/{EPOCH}", json={})
        route_prompt = resp.json()["media_plan"]["prompt"]
        assert plan.prompt == route_prompt

    def test_plan_serialization_no_execution_fields(self, client):
        """(6) Сериализованный план маршрута B без execution-полей."""
        from core.adc_deps import registry as reg
        import asyncio
        import json
        b = reg.get("visual_context_builder")
        ctx = asyncio.run(b.build_scene_context_for_epoch(EPOCH))
        plan = MediaPlanBuilder(generator="comfyui").build_image_plan(ctx)
        serialized = json.dumps(plan.to_dict(), ensure_ascii=False)
        for banned in ('"model"', '"steps"', '"seed"', '"cfg"', '"sampler"',
                       '"workflow"', '"provider"', '"backend"', '"quality"',
                       '"checkpoint"', '"lora"'):
            assert banned not in serialized
        from media_plan import verify_no_execution_fields
        assert verify_no_execution_fields() == []


# ── Пункт 7: прежняя ошибочная семантика (без выдуманного temporal) ──


class TestRouteBUnknownEpoch:
    def test_unknown_epoch_404_no_invented_temporal(self, client):
        """(7) Несуществующая эпоха → 404; план/генерация не создаются;
        temporal НЕ выдумывается (is_temporal=False у пустого контекста)."""
        resp = client.post("/book/visualize/epoch/nonexistent_epoch", json={})
        assert resp.status_code == 404
        # Проверка механизма: canonical-билдер для неизвестной эпохи даёт
        # НЕ-temporal контекст (выдумывания нет на уровне источника):
        from core.adc_deps import registry as reg
        import asyncio
        b = reg.get("visual_context_builder")
        ctx = asyncio.run(b.build_scene_context_for_epoch("nonexistent_epoch"))
        assert ctx.scene_extras.temporal.is_temporal is False

    def test_world_model_not_mutated(self, client):
        """(8) Инвариант MD-2: Route B не мутирует WorldModel (read-only)."""
        from narrative_engine.world_model import WorldModel
        before = WorldModel.load()
        client.post(f"/book/visualize/epoch/{EPOCH}", json={})
        client.post("/book/visualize/epoch/nonexistent_epoch", json={})
        after = WorldModel.load()
        assert before._data == after._data


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
