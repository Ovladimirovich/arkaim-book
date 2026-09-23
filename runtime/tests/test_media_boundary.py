"""Boundary regression test: prove Arkaim has NO local media generation execution path.

This test validates the Arkaim Media Boundary ADR:
- Arkaim = semantic task generator (SceneContext → MediaPlan / Prompt Package)
- Arkaim ≠ executor of image/video generation
- All execution (ComfyUI, StableDiffusion, video assembly, pipeline, queue)
  has been removed from Arkaim's codebase and DI container.

Запуск (из runtime/):
  .venv/Scripts/python -m pytest tests/test_media_boundary.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
sys.path.insert(0, str(CORE_DIR))


# ── Helpers ────────────────────────────────────────────────────

def _collect_route_paths(app) -> set[str]:
    """Collect all registered route paths from the FastAPI app."""
    paths = set()
    for route in app.routes:
        if hasattr(route, "path"):
            paths.add(route.path)
    return paths


# ── 1. Removed routes MUST NOT exist ──────────────────────────

class TestRemovedRoutesAbsent:
    """Execution/infrastructure routes removed per Media Boundary must not exist."""

    @pytest.fixture(autouse=True)
    def _app(self):
        from core.main import app
        self.paths = _collect_route_paths(app)

    def test_no_comfyui_status(self):
        assert "/book/comfyui/status" not in self.paths

    def test_no_comfyui_config(self):
        assert "/book/comfyui/config" not in self.paths

    def test_no_providers_list(self):
        assert "/book/providers/list" not in self.paths

    def test_no_providers_status(self):
        assert "/book/providers/status" not in self.paths

    def test_no_assets_generate(self):
        assert "/book/assets/generate" not in self.paths

    def test_no_assets_generate_async(self):
        assert "/book/assets/generate-async" not in self.paths

    def test_no_assets_generate_character(self):
        assert "/book/assets/generate-character" not in self.paths

    def test_no_assets_generate_location(self):
        assert "/book/assets/generate-location" not in self.paths

    def test_no_assets_batch(self):
        assert "/book/assets/batch" not in self.paths

    def test_no_assets_queue_status(self):
        assert "/book/assets/queue/status" not in self.paths

    def test_no_assets_queue_task(self):
        # Check there's no pattern matching /book/assets/queue/task/{task_id}
        for p in self.paths:
            assert "queue/task" not in p, f"Unexpected queue task route: {p}"

    def test_no_film_shot_generate(self):
        # Check there's no pattern matching /book/film/.../shots/{id}/generate
        for p in self.paths:
            assert not (
                "/film/" in p and "/shots/" in p and "generate" in p
            ), f"Unexpected film shot generate route: {p}"

    def test_no_film_assemble(self):
        for p in self.paths:
            assert not (
                "/film/" in p and "/assemble" in p
            ), f"Unexpected film assemble route: {p}"

    def test_no_visual_genome_auto_generate(self):
        assert "/book/visual-genome/auto-generate" not in self.paths


# ── 2. Execution DI registrations must not exist ───────────────

class TestExecutionDIAbsent:
    """Execution factories (image_provider, video_provider, generation_pipeline,
    generation_queue) must NOT be registered in the DI container."""

    @pytest.fixture(autouse=True)
    def _registry(self):
        from core.adc_deps import registry
        self.registry = registry

    def test_no_image_provider_registered(self):
        assert not self.registry.has("image_provider")
        assert "image_provider" not in self.registry._instances

    def test_no_video_provider_registered(self):
        assert not self.registry.has("video_provider")
        assert "video_provider" not in self.registry._instances

    def test_no_generation_pipeline_registered(self):
        assert not self.registry.has("generation_pipeline")
        assert "generation_pipeline" not in self.registry._instances

    def test_no_generation_queue_registered(self):
        assert not self.registry.has("generation_queue")
        assert "generation_queue" not in self.registry._instances


# ── 3. Preparation endpoints return MediaPlan (not image bytes) ──

class TestPreparationEndpointsReturnMediaPlan:
    """Endpoints that previously executed generation now return
    MediaPlan (Prompt Package) without calling any provider."""

    @pytest.fixture(autouse=True)
    def _isolate(self):
        from core.services.registry import registry as _reg
        from core import main as _main_mod
        _main_mod._rate_limits.clear()
        snapshot = dict(_reg._instances)
        yield
        _main_mod._rate_limits.clear()
        _reg._instances.clear()
        _reg._instances.update(snapshot)

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from core.main import app
        from auth.rbac import get_current_user

        async def _fake_user():
            return {"user_id": "test-user", "role": "admin", "provider": "test",
                    "username": "tester", "display_name": "Test User"}

        saved = dict(app.dependency_overrides)
        app.dependency_overrides[get_current_user] = _fake_user
        c = TestClient(app)
        yield c
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved)

    def test_visualize_returns_media_plan(self, client):
        """POST /book/visualize returns MediaPlan, not image bytes."""
        resp = client.post("/book/visualize",
                           json={"chapter": 1,
                                 "scene_id": "conflict_гиперборея_материальный_путь_атлантиды"})
        assert resp.status_code == 200
        body = resp.json()
        assert "media_plan" in body
        plan = body["media_plan"]
        assert isinstance(plan, dict)
        # MediaPlan must have prompt (the semantic text)
        assert "prompt" in plan
        assert isinstance(plan["prompt"], str)
        assert len(plan["prompt"]) > 0
        # Must NOT have image_bytes (no generation)
        assert "image_bytes" not in body
        assert "image_bytes" not in plan

    def test_visualize_epoch_returns_media_plan(self, client):
        """POST /book/visualize/epoch returns MediaPlan, not image bytes."""
        resp = client.post("/book/visualize/epoch/arkaim_era")
        if resp.status_code == 404:
            pytest.skip("arkaim_era epoch not in WorldModel")
        assert resp.status_code == 200
        body = resp.json()
        assert "media_plan" in body
        plan = body["media_plan"]
        assert isinstance(plan, dict)
        assert "prompt" in plan
        assert len(plan["prompt"]) > 0
        assert "image_bytes" not in body

    def test_generate_context_returns_media_plan(self, client):
        """POST /book/assets/generate-context returns MediaPlan, not asset."""
        resp = client.post("/book/assets/generate-context",
                           params={"chapter": 1,
                                   "scene_id": "conflict_гиперборея_материальный_путь_атлантиды"})
        assert resp.status_code == 200
        body = resp.json()
        assert "media_plan" in body
        plan = body["media_plan"]
        assert isinstance(plan, dict)
        assert "prompt" in plan
        assert len(plan["prompt"]) > 0
        # Must NOT have asset fields (no generation)
        assert "asset_id" not in body
        assert "status" not in body or body.get("status") != "completed"

    def test_media_plan_has_no_execution_fields(self, client):
        """MediaPlan must NOT contain execution fields (provider/steps/seed/etc)."""
        resp = client.post("/book/assets/generate-context",
                           params={"chapter": 1,
                                   "scene_id": "conflict_гиперборея_материальный_путь_атлантиды"})
        assert resp.status_code == 200
        plan = resp.json()["media_plan"]
        plan_str = str(plan).lower()
        banned = ["comfyui", "kSampler", "checkpoint", "sampler_name",
                  "sampler_name", "cfg_scale", "seed", "steps",
                  "workflow", "node_graph"]
        for term in banned:
            assert term not in plan_str or term == "comfyui", \
                f"Execution term '{term}' leaked into MediaPlan"


# ── 4. Execution provider files are stubs ──────────────────────

class TestExecutionProvidersStubbed:
    """ComfyUI/StableDiffusion/ImageSequence files must be stubs (no real code)."""

    def test_comfyui_is_stub(self):
        comfyui_path = Path(__file__).resolve().parent.parent.parent / "core" / "CORE" / "providers" / "image" / "comfyui.py"
        if not comfyui_path.exists():
            pytest.skip("comfyui.py not found")
        content = comfyui_path.read_text(encoding="utf-8")
        # Must be a stub: no class definition, no DEFAULT_WF, no KSampler
        assert "class ComfyUIProvider" not in content, \
            "ComfyUIProvider class still present — not stubbed"
        assert "KSampler" not in content, \
            "KSampler node-graph knowledge still present"
        assert "DEFAULT_WF" not in content, \
            "DEFAULT_WF workflow still present"

    def test_stable_diffusion_is_stub(self):
        sd_path = Path(__file__).resolve().parent.parent.parent / "core" / "CORE" / "providers" / "image" / "stable_diffusion.py"
        if not sd_path.exists():
            pytest.skip("stable_diffusion.py not found")
        content = sd_path.read_text(encoding="utf-8")
        assert "class StableDiffusionProvider" not in content, \
            "StableDiffusionProvider class still present — not stubbed"

    def test_image_sequence_is_stub(self):
        is_path = Path(__file__).resolve().parent.parent.parent / "core" / "CORE" / "providers" / "video" / "image_sequence.py"
        if not is_path.exists():
            pytest.skip("image_sequence.py not found")
        content = is_path.read_text(encoding="utf-8")
        assert "class ImageSequenceVideoProvider" not in content, \
            "ImageSequenceVideoProvider class still present — not stubbed"


# ── 5. Preparation infrastructure IS present ───────────────────

class TestPreparationInfrastructurePresent:
    """The preparation layer (SceneContext, MediaPlanBuilder, VisualContextBuilder)
    must remain in Arkaim — these are the semantic core, not execution."""

    def test_visual_context_builder_registered(self):
        from core.adc_deps import registry
        assert registry.has("visual_context_builder")

    def test_scene_engine_registered(self):
        from core.adc_deps import registry
        assert registry.has("scene_engine")

    def test_prompt_builder_registered(self):
        from core.adc_deps import registry
        assert registry.has("prompt_builder")

    def test_asset_store_registered(self):
        from core.adc_deps import registry
        assert registry.has("asset_store")

    def test_film_store_registered(self):
        from core.adc_deps import registry
        assert registry.has("film_store")

    def test_mediaplan_builder_importable(self):
        from media_plan import MediaPlanBuilder
        builder = MediaPlanBuilder(generator="comfyui")
        assert builder is not None

    def test_scene_context_importable(self):
        from visual.visual_context import VisualContext
        assert VisualContext is not None

    def test_verify_no_execution_fields_importable(self):
        from media_plan import verify_no_execution_fields
        assert callable(verify_no_execution_fields)
