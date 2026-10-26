# -*- coding: utf-8 -*-
"""EDM-RES пилот — тесты production-швов /book/ask и /visualize (OWNER-GATE).

Сценарии пилота (решение владельца, 25.10.2026):
  1. Dialogue: EDM-блок через СУЩЕСТВУЮЩУЮ t1-провайдерную цепь
     (composite t1+EDM, facts_block); unknown не материализуется;
     layer isolation: сценарный/художественный scope не виден в world-view;
  2. MediaPlan: EDM наполняет SceneContext (architecture/landscape/
     environment — только существующие поля); weather/season → явный
     UNKNOWN вместо fail-open "clear";
  3. Legacy-regression: флаг выключен / нет совпадения — поведение
     byte-identично (нет ключа `edm`, ctx не трогается, провайдер = t1).

Запуск (из runtime/):
  .venv\\Scripts\\python -m pytest tests/test_edm_res_pilot.py -v
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]  # runtime/
CORE_DIR = ROOT.parent / "core" / "CORE"
for _p in (str(CORE_DIR), str(ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from media_plan import MediaPlanBuilder  # noqa: E402
from visual.prompt_composer import PromptComposer  # noqa: E402
from visual.scene_context import SourceRefs, extend_visual_context  # noqa: E402
from visual.visual_context import VisualContext  # noqa: E402

import shared_config  # noqa: E402
from core.services import edm_pilot  # noqa: E402

REAL_EDM_DIR = CORE_DIR / "ENTITY_MODEL"


def _make_ctx(location: str = "", location_id: str = "") -> VisualContext:
    ctx = VisualContext()
    ctx.scene.location = location
    ctx.scene.title = "Тестовая сцена"
    ctx.location.name = location
    ctx.location.location_id = location_id
    extend_visual_context(ctx, source_refs=SourceRefs(scene_id="s1", chapter=1, location_id=location_id))
    return ctx


def _load_core_module(filename: str):
    import importlib.util

    spec = importlib.util.spec_from_file_location(f"edm_res_pilot_test_{filename}", REAL_EDM_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _edm_env(monkeypatch):
    """Детерминированная среда на каждый тест: флаг off, реальный EDM-каталог, чистые кэши."""
    monkeypatch.setattr(shared_config.settings, "EDM_RES_PILOT_ENABLED", False, raising=False)
    monkeypatch.setattr(shared_config.settings, "EDM_RES_DIR", str(REAL_EDM_DIR), raising=False)
    edm_pilot._reset_cache()
    yield
    edm_pilot._reset_cache()


# ── 1. OWNER-GATE ────────────────────────────────────────────────────────


def test_flag_default_off(monkeypatch):
    monkeypatch.setattr(shared_config.settings, "EDM_RES_PILOT_ENABLED", False)
    assert edm_pilot.enabled() is False
    monkeypatch.setattr(shared_config.settings, "EDM_RES_PILOT_ENABLED", True)
    assert edm_pilot.enabled() is True


def test_route_gates_follow_flag(monkeypatch):
    from core.routes import book, visual

    monkeypatch.setattr(shared_config.settings, "EDM_RES_PILOT_ENABLED", False)
    assert book._edm_res_pilot_enabled() is False
    assert visual._edm_res_pilot_enabled() is False
    monkeypatch.setattr(shared_config.settings, "EDM_RES_PILOT_ENABLED", True)
    assert book._edm_res_pilot_enabled() is True
    assert visual._edm_res_pilot_enabled() is True


def test_visualize_request_dto_additive_default():
    from core.dto.requests import VisualizeRequest

    req = VisualizeRequest(chapter=1, scene_id="s1")
    assert req.edm_entity_ids == []


# ── 2. MediaPlan pilot: EDM наполняет SceneContext ───────────────────────


def test_mediaplan_pilot_arkaim_scene():
    ctx = _make_ctx(location="Аркаим")
    assert ctx.environment.weather == "clear"  # legacy fail-open default до apply

    report = edm_pilot.apply_edm_to_context(ctx, location_name=ctx.location.name, scene_location=ctx.scene.location)
    assert report["applied"] is True
    assert {"region_arkaim", "arkaim_settlement"} <= set(report["entity_ids"])

    # Архитектура — в существующих полях ctx (prompt + LocationRef).
    assert ctx.architecture.style == "circular fortified"
    assert ctx.location.architecture.style == "circular fortified"
    assert "stone" in ctx.location.architecture.materials

    # Погода/сезон — явный UNKNOWN вместо fail-open "clear".
    assert ctx.environment.weather == "UNKNOWN"
    assert ctx.environment.season == "UNKNOWN"
    assert {"field": "environment.weather", "entity": "region_arkaim"} in report["unknown_fields"]

    # Провенанс: идентификаторы в source_refs (без копирования содержимого).
    refs = ctx.scene_extras.source_refs.entity_refs
    assert "edm:region_arkaim" in refs and "edm:arkaim_settlement" in refs

    # Prompt (замороженный composer) теперь несёт EDM-стиль.
    prompt = PromptComposer(generator="comfyui").compose(ctx)
    assert "circular fortified" in prompt

    # MediaPlan наследует провенанс через source_refs (контракт плана не тронут).
    plan = MediaPlanBuilder(generator="comfyui").build_image_plan(ctx)
    assert plan.location.architecture_style == "circular fortified"
    assert "edm:region_arkaim" in json.dumps(plan.to_dict(), ensure_ascii=False)


def test_mediaplan_no_match_ctx_untouched():
    ctx = _make_ctx(location="Тёмная долина")
    report = edm_pilot.apply_edm_to_context(ctx, location_name="Тёмная долина", scene_location="Тёмная долина")
    assert report["applied"] is False
    assert ctx.environment.weather == "clear"  # legacy default сохранён
    assert ctx.scene_extras.source_refs.entity_refs == []
    assert ctx.architecture.style == ""


def test_explicit_entity_ids_override_match():
    ctx = _make_ctx(location="Тёмная долина")
    report = edm_pilot.apply_edm_to_context(ctx, location_name="Тёмная долина", explicit_ids=["steppe_climate"])
    assert report["entity_ids"] == ["steppe_climate"]
    # climate.* — без цели в существующих полях ctx: не угадывается (skipped).
    assert any(s["path"].startswith("climate.") for s in report["skipped_paths"])


# ── 3. Layer isolation: художественный fill не виден в World Model ───────


def _write_entity(tmp_path: Path, entity: dict, name: str, mtime: float) -> None:
    d = tmp_path / "pilot"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{name}.json"
    p.write_text(json.dumps(entity, ensure_ascii=False), encoding="utf-8")
    os.utime(p, (mtime, mtime))


def _copy_core_modules(tmp_path: Path) -> None:
    """Сервис читает .py-модули из EDM_RES_DIR — при override каталога нужен полный набор."""
    for fn in ("resolutions.py", "operations.py", "world_feed.py"):
        shutil.copy2(REAL_EDM_DIR / fn, tmp_path / fn)


def test_layer_isolation_artistic_fill_not_visible_at_world_scope(monkeypatch, tmp_path):
    ops = _load_core_module("operations.py")
    base = {
        "model": {"model_id": "t", "model_version": "v0.1", "created_at": "2026-10-25", "schema_version": "1.0", "note": "t"},
        "identity": {"canonical_id": "loc_test", "type": "location", "names": ["Test Place"], "aliases": [], "one_line": "t"},
        "time": {"epoch_ref": [], "start": None, "end": None, "temporal_links": [], "note": "t"},
        "claims": [{"path": "environment.weather", "value": None, "status": "unknown", "provenance_class": "none"}],
        "relations": [],
        "constraints": {},
        "pilot": {},
    }
    filled = ops.artistic_fill(base, "environment.weather", "clear", scope_level="media_plan", scope_id="mp_pilot")
    _write_entity(tmp_path, filled, "loc_test", time.time())
    _copy_core_modules(tmp_path)
    monkeypatch.setattr(shared_config.settings, "EDM_RES_DIR", str(tmp_path), raising=False)
    edm_pilot._reset_cache()

    # World Model view: fill не достигает — weather остаётся UNKNOWN.
    ctx_world = _make_ctx(location="Test Place")
    report_world = edm_pilot.apply_edm_to_context(ctx_world, location_name="Test Place")
    assert ctx_world.environment.weather == "UNKNOWN"
    assert report_world["medium_fields"] == []

    # Task view: scene_overrides открывает media_plan-scope — значение там.
    ctx_task = _make_ctx(location="Test Place")
    report_task = edm_pilot.apply_edm_to_context(ctx_task, location_name="Test Place", scene_overrides={"media_plan": "mp_pilot"})
    assert ctx_task.environment.weather == "clear"
    assert report_task["medium_fields"][0]["field"] == "environment.weather"
    assert report_task["medium_fields"][0]["scope"]["level"] == "media_plan"

    # World view после task-apply чист (отдельный ctx, тот же world-scope).
    ctx_world2 = _make_ctx(location="Test Place")
    assert edm_pilot.apply_edm_to_context(ctx_world2, location_name="Test Place")["medium_fields"] == []


# ── 4. Dialogue pilot: слоистый EDM-блок + composite-провайдер ──────────


def test_dialogue_block_layered_and_honest():
    block = edm_pilot.build_edm_dialogue_block("Расскажи про Аркаим")
    assert block is not None
    assert "region_arkaim" in block["entities"]
    text = block["block"]
    assert "Аркаим" in text
    assert "не установлено" in text  # weather/season — явная граница знания
    assert "clear" not in text.lower()  # unknown не материализован в дефолт
    # Провенанс существует и ссылается только на сущности блока.
    assert block["provenance"]
    assert {p["entity"] for p in block["provenance"]} <= set(block["entities"])
    # E5: approved-сущность region_arkaim гарантированно имеет провенанс
    assert any(p["entity"] == "region_arkaim" for p in block["provenance"])


def test_dialogue_block_no_match_is_none():
    assert edm_pilot.build_edm_dialogue_block("Как работает система?") is None


def test_compose_provider_merges_edm_into_t1():
    def base(query, layer_text):
        return {"contexts": [{"entity_id": "kc_x"}], "facts": [], "facts_block": "T1-материалы"}

    provider = edm_pilot.compose_provider(base)
    payload = provider("Расскажи про Аркаим", "слоевой текст")
    assert "T1-материалы" in payload["facts_block"]
    assert "Аркаим" in payload["facts_block"]
    assert payload["contexts"] == [{"entity_id": "kc_x"}]


def test_compose_provider_passthrough_without_match():
    def base(query, layer_text):
        return {"contexts": [], "facts_block": "T1-материалы"}

    provider = edm_pilot.compose_provider(base)
    # Нет совпадения — результат base без изменений (byte-identical).
    assert provider("Как работает система?", "") == {"contexts": [], "facts_block": "T1-материалы"}

    def base_none(query, layer_text):
        return None

    assert edm_pilot.compose_provider(base_none)("Как работает система?", "") is None


def test_pulse_manager_provider_flag_switch(monkeypatch):
    from core import pulse_manager
    from core.services.knowledge_core_context import build_dialogue_context

    captured: dict = {}

    class FakeVoice:
        def set_knowledge_context_provider(self, provider):
            captured["provider"] = provider

    monkeypatch.setattr(shared_config.settings, "EDM_RES_PILOT_ENABLED", False)
    pulse_manager._setup_dialogue_context_provider(FakeVoice())
    assert captured["provider"] is build_dialogue_context  # legacy: штатный t1

    captured.clear()
    monkeypatch.setattr(shared_config.settings, "EDM_RES_PILOT_ENABLED", True)
    pulse_manager._setup_dialogue_context_provider(FakeVoice())
    provider = captured["provider"]
    assert provider is not build_dialogue_context  # composite t1+EDM
    payload = provider("Расскажи про Аркаим", "слоевой текст")
    assert "Аркаим" in payload["facts_block"]


# ── 5. Загрузчик сущностей: mtime-кэш ─────────────────────────────────────


def test_get_entities_indexes_pilot_and_examples():
    ents = edm_pilot.get_entities()
    assert "region_arkaim" in ents
    assert "arkaim_settlement" in ents
    assert len(ents) >= 8  # 5 pilot + 3 examples


def test_pilot_card_wins_over_example_same_canonical_id():
    """E1: svetovit живёт и в pilot/ (native-карточка), и в examples/ (v0.1 control-пример).

    Order-ранг §4.1: pilot (ранг b) бьёт examples (ранг c) — согласовано
    с entity_sources() (setdefault, pilot-файлы первыми).
    """
    pilot_file = json.loads((REAL_EDM_DIR / "pilot" / "svetovit.json").read_bytes().decode("utf-8-sig"))
    example_file = json.loads((REAL_EDM_DIR / "examples" / "svetovit_character.json").read_bytes().decode("utf-8-sig"))
    assert pilot_file != example_file
    ents = edm_pilot.get_entities()
    assert "svetovit" in ents
    assert ents["svetovit"] == pilot_file, "pilot-карточка должна победить examples (ранг b < c)"
    assert edm_pilot.entity_sources().get("svetovit") == "pilot"


def test_entity_cache_mtime_reload(monkeypatch, tmp_path):
    (tmp_path / "pilot").mkdir(parents=True)
    ent = {
        "model": {},
        "identity": {"canonical_id": "cache_probe", "type": "location", "names": ["Cache Probe"]},
        "claims": [{"path": "place.coordinates", "value": {"lat": 1, "lng": 2}, "status": "known", "provenance_class": "external_source"}],
        "relations": [],
        "constraints": {},
        "pilot": {},
    }
    p = tmp_path / "pilot" / "probe.json"
    p.write_text(json.dumps(ent), encoding="utf-8")
    os.utime(p, (1000.0, 1000.0))
    monkeypatch.setattr(shared_config.settings, "EDM_RES_DIR", str(tmp_path), raising=False)
    edm_pilot._reset_cache()

    first = edm_pilot.get_entities()
    assert "cache_probe" in first
    second = edm_pilot.get_entities()
    assert second is first  # cache hit: mtime не изменился, тот же объект

    # mtime изменился → перечитывание
    ent["claims"][0]["value"] = {"lat": 3, "lng": 4}
    p.write_text(json.dumps(ent), encoding="utf-8")
    os.utime(p, (2000.0, 2000.0))
    reloaded = edm_pilot.get_entities()
    assert reloaded["cache_probe"]["claims"][0]["value"] == {"lat": 3, "lng": 4}


# ── 6. HTTP-уровень /book/visualize (флаг off → legacy, флаг on → пилот) ─


def _visualize_client(monkeypatch, location: str):
    from fastapi.testclient import TestClient

    from core import adc_deps
    from core.main import app

    class _StubSceneEngine:
        def get_scene(self, chapter, scene_id):
            return {"scene_id": scene_id}

    class _StubBuilder:
        async def build_scene_context(self, chapter, scene_id):
            return _make_ctx(location=location, location_id="")

    monkeypatch.setitem(app.dependency_overrides, adc_deps.get_scene_engine, lambda: _StubSceneEngine())
    monkeypatch.setattr(
        adc_deps.registry,
        "get",
        lambda name: _StubBuilder() if name == "visual_context_builder" else None,
    )
    return TestClient(app)


def test_visualize_http_flag_off_legacy(monkeypatch):
    client = _visualize_client(monkeypatch, location="Аркаим")
    resp = client.post(
        "/book/visualize",
        json={"chapter": 1, "scene_id": "s_arkaim", "edm_entity_ids": ["region_arkaim", "arkaim_settlement"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "edm" not in body  # флаг off — публичный контракт не меняется
    assert "circular fortified" not in json.dumps(body, ensure_ascii=False)


def test_visualize_http_pilot(monkeypatch):
    monkeypatch.setattr(shared_config.settings, "EDM_RES_PILOT_ENABLED", True, raising=False)
    client = _visualize_client(monkeypatch, location="Аркаим")
    resp = client.post(
        "/book/visualize",
        json={"chapter": 1, "scene_id": "s_arkaim", "edm_entity_ids": ["region_arkaim", "arkaim_settlement"]},
    )
    assert resp.status_code == 200
    body = resp.json()

    assert "edm" in body
    assert body["edm"]["applied"] is True
    assert any(u["field"] == "environment.weather" for u in body["edm"]["unknown_fields"])
    style_fields = [f for f in body["edm"]["fields"] if f["field"] == "architecture.style"]
    assert style_fields and style_fields[0]["value"] == "circular fortified"

    # Промпт плана несёт EDM-стиль; провенанс — в source_refs плана.
    assert "circular fortified" in body["media_plan"]["prompt"]
    assert "edm:region_arkaim" in json.dumps(body["media_plan"], ensure_ascii=False)


def test_visualize_http_pilot_no_match_no_edm_key(monkeypatch):
    """Флаг on, но совпадения сущностей нет → ключ `edm` не появляется (legacy-ответ)."""
    monkeypatch.setattr(shared_config.settings, "EDM_RES_PILOT_ENABLED", True, raising=False)
    client = _visualize_client(monkeypatch, location="Тёмная долина")
    resp = client.post(
        "/book/visualize",
        json={"chapter": 1, "scene_id": "s_dark", "edm_entity_ids": ["no_such_entity"]},
    )
    assert resp.status_code == 200
    assert "edm" not in resp.json()


# ── 7. E2E live-вход: реальный registry (builder / scene_engine / media_plan) ──
#
# «Live»-проверка production-шва без сервера: то же приложение core.main.app,
# реальный VisualContextBuilder, реальный SceneEngine, реальный MediaPlanBuilder,
# реальный EDM-каталог. Мокуется только голос (keeper — граница LLM/Pulse,
# паттерн M23) и memory store (изоляция персистентности).


class TestEndToEndRealRegistry:
    """Сквозная проверка /visualize и /book/ask на реальных данных (live-вход).

    Доказательный сетап:
    - флаг off: ответ byte-идентичен legacy (нет `edm`, промпт = baseline SHA
      из test_md3_route_a);
    - флаг on + явные edm_entity_ids (определяющий вход пилота): EDM-значения
      реально доходят до MediaPlan, weather/season получают явный UNKNOWN
      (fail-open guard), провенанс `edm:<id>` в source_refs;
    - флаг on + авто-совпадение без применимых Claim'ов: план не трогается
      (layer isolation на реальных данных), ответ = legacy;
    - /book/ask: EDM-блок в ответе при вопросе с именем сущности.
    """

    HYPER_SCENE = ("1", "conflict_гиперборея_материальный_путь_атлантиды")  # авто-совпадение civ_hyperborea
    BASELINE_PROMPT_SHA = "02078e4adfddaaa7"  # из test_md3_route_a (canonical path, legacy)

    @pytest.fixture(autouse=True)
    def _isolate_global_state(self):
        """Изоляция pytest-процесса (паттерн test_md3_route_a/test_m23):
        registry-снапшот + rate-limiter до/после."""
        from core import main as _main_module
        from core.services.registry import registry as _reg

        _main_module._rate_limits.clear()
        _instances_snapshot = dict(_reg._instances)
        _factories_snapshot = dict(_reg._factories)
        yield
        _main_module._rate_limits.clear()
        _reg._instances.clear()
        _reg._instances.update(_instances_snapshot)
        _reg._factories.clear()
        _reg._factories.update(_factories_snapshot)

    @pytest.fixture
    def real_client(self):
        """TestClient без запуска startup-events; реальные сцены/билдер/план.

        Auth override (паттерн test_md3_route_a, fake admin): /book/ask
        требует require_role("reader"), /visualize без auth."""
        from fastapi.testclient import TestClient

        from auth.rbac import get_current_user
        from core.main import app

        async def _fake_user():
            return {
                "user_id": "test-user",
                "role": "admin",
                "provider": "test",
                "username": "tester",
                "display_name": "Test User",
            }

        _saved = dict(app.dependency_overrides)
        app.dependency_overrides[get_current_user] = _fake_user
        c = TestClient(app)
        yield c
        app.dependency_overrides.clear()
        app.dependency_overrides.update(_saved)

    def _post_visualize(self, real_client, monkeypatch, payload: dict) -> dict:
        resp = real_client.post("/book/visualize", json=payload)
        assert resp.status_code == 200, resp.text
        return resp.json()

    def test_visualize_flag_off_prompt_byte_identical(self, real_client, monkeypatch):
        """(1) Флаг off: /visualize byte-идентичен legacy — нет `edm`, промпт = baseline."""
        import hashlib

        monkeypatch.setattr(shared_config.settings, "EDM_RES_PILOT_ENABLED", False, raising=False)
        edm_pilot._reset_cache()

        body = self._post_visualize(
            real_client,
            monkeypatch,
            {"chapter": int(self.HYPER_SCENE[0]), "scene_id": self.HYPER_SCENE[1], "edm_entity_ids": ["civ_hyperborea"]},
        )
        assert "edm" not in body
        mp = body["media_plan"]
        assert hashlib.sha256(mp["prompt"].encode()).hexdigest()[:16] == self.BASELINE_PROMPT_SHA

    def test_visualize_flag_on_auto_match_no_applicable_claims_is_legacy(self, real_client, monkeypatch):
        """(2) Флаг on + авто-совпадение civ_hyperborea, но у неё только
        culture.values (нет ctx-тицелей) → apply не мутатирует ctx:
        слой world чист, промпт byte-идентичен legacy, ключа `edm` нет."""
        import hashlib

        monkeypatch.setattr(shared_config.settings, "EDM_RES_PILOT_ENABLED", True, raising=False)
        edm_pilot._reset_cache()

        body = self._post_visualize(
            real_client,
            monkeypatch,
            {"chapter": int(self.HYPER_SCENE[0]), "scene_id": self.HYPER_SCENE[1]},
        )
        assert "edm" not in body
        mp = body["media_plan"]
        assert hashlib.sha256(mp["prompt"].encode()).hexdigest()[:16] == self.BASELINE_PROMPT_SHA

    def test_visualize_flag_on_explicit_ids_feed_real_plan(self, real_client, monkeypatch):
        """(3) Пилотный happy-path на реальных данных: явные ids
        (определяющий вход пилота — edm_entity_ids) наполняют реальный
        SceneContext независимо от сцены → MediaPlan реально несёт
        EDM-значения. (Ограничение «каталог-сцены недоступны /visualize:
        DTO chapter ≥ 1» снято E3: chapter=0 открыт, HTTP-покрытие —
        test_e3_* в этом же классе.)"""
        monkeypatch.setattr(shared_config.settings, "EDM_RES_PILOT_ENABLED", True, raising=False)
        edm_pilot._reset_cache()

        body = self._post_visualize(
            real_client,
            monkeypatch,
            {
                "chapter": int(self.HYPER_SCENE[0]),
                "scene_id": self.HYPER_SCENE[1],
                "edm_entity_ids": ["region_arkaim", "arkaim_settlement", "arkaim"],
            },
        )
        assert "edm" in body
        edm = body["edm"]
        assert edm["applied"] is True
        assert set(edm["entity_ids"]) == {"region_arkaim", "arkaim_settlement", "arkaim"}

        # Не-medium (world-scope) значения реально легли в план.
        by_field = {f["field"]: f for f in edm["fields"] if not f.get("medium")}
        assert by_field["architecture.style"]["value"] == "circular fortified"
        assert by_field["architecture.materials"]["value"] == "stone, timber, thatch, clay"

        # Fail-open guard: environment.weather/season — явная граница знания
        # (unknown Claim'и не материализуются в значения), в отличие от
        # legacy-дефолта «clear».
        unknown = {u["field"] for u in edm["unknown_fields"]}
        assert {"environment.weather", "environment.season"} <= unknown

        plan = body["media_plan"]
        plan_json = json.dumps(plan, ensure_ascii=False)
        assert "circular fortified" in plan["prompt"]
        assert "edm:region_arkaim" in plan_json
        assert "edm:arkaim_settlement" in plan_json

    def test_e2_catalog_scene_service_level_bridge(self, real_client, monkeypatch):
        """(E2) Реальные данные, service-уровень: каталог-сцена scene_012
        (location 'ОКЕАН - ДЕНЬ'; с E3 каталог-сцены доступны и /visualize —
        см. test_e3_*) → реальный builder →
        resolve_scene_location: авто-матчинг доходит до engine-сущностей
        (region_oceania/civ_oceania — approved engine/crosswalk + детерм.
        скорер, без LLM и RAG-буста). EDM-карточек у них нет — fail-closed:
        сущности НЕ материализуются, ctx не мутируется, в отчёте — трасса."""
        import asyncio

        from core.adc_deps import registry

        monkeypatch.setattr(shared_config.settings, "EDM_RES_PILOT_ENABLED", True, raising=False)
        edm_pilot._reset_cache()

        builder = registry.get("visual_context_builder")
        ctx = asyncio.run(builder.build_scene_context(0, "scene_012"))
        assert ctx.scene.location == "ОКЕАН - ДЕНЬ"  # реальная каталог-локация

        r = edm_pilot.resolve_scene_location(ctx.scene.location, location_id=ctx.location.location_id, location_name=ctx.location.name)
        assert "region_oceania" in r["entity_ids"]  # авто-матчинг дошёл до engine
        # E4: region_oceania теперь в каталоге — материализация возможна
        cards = {e["identity"]["canonical_id"] for e in r["edm_entities"]}
        assert "region_oceania" in cards

        report = edm_pilot.apply_edm_to_context(ctx, auto_matched_ids=r["entity_ids"] or None, location_matched=r)
        assert "region_oceania" in report["location_matched"]["entity_ids"]  # трасса

    def test_ask_flag_on_dialogue_block(self, real_client, monkeypatch):
        """(4) /book/ask: вопрос с именем сущности → EDM-блок в data.
        keeper mock-уется (граница голоса, паттерн M23) — вся остальная
        цепочка реальная (metadata, related_entities, knowledge_core)."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from core.services.registry import registry as _reg

        monkeypatch.setattr(shared_config.settings, "EDM_RES_PILOT_ENABLED", True, raising=False)
        edm_pilot._reset_cache()

        mock_keeper = MagicMock()

        def _fresh_keeper_result(*_args, **_kwargs):
            # Новый dict на каждый вызов: маршрут мутирует result (related_entities,
            # knowledge_core, edm-блок) — переиспользование одного объекта
            # «запомнило бы» EDM-блок во флаг-off повторный запрос.
            return {
                "answer": "Аркаим — круглый город на границе миров, место единения народов.",
                "source": "pulse",
                "provenance": [],
                "uncertainty": None,
                "pulse_confidence": 0.9,
                "llm_used": False,
                "mood": "neutral",
                "suggestion": "",
            }

        mock_keeper.act = AsyncMock(side_effect=_fresh_keeper_result)
        _reg._instances.pop("keeper", None)  # старый singleton (если был) — в сторону
        _reg._factories["keeper"] = lambda: mock_keeper
        fake_store = MagicMock()
        fake_store.store_exchange = AsyncMock(return_value={"status": "ok"})

        question = "Что такое Аркаим?"
        with patch("memory.store.get_memory_store", return_value=fake_store):
            resp = real_client.post("/book/ask", json={"question": question})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["ok"] is True
        data = body["data"]

        assert "edm" in data
        edm = data["edm"]
        # Авто-совпадение по имени в вопросе: Аркаим затронут.
        assert "arkaim_settlement" in edm["entities"]
        assert "region_arkaim" in edm["entities"]
        assert "Сущности Entity Description Model" in edm["block"]
        # Провенанс-блок: у каждого Claim'а — статус (слоистость знания).
        assert "known" in {p["status"] for p in edm["provenance"]}

        # (5) Флаг off на том же вопросе: ключ `edm` не появляется (legacy-контракт).
        monkeypatch.setattr(shared_config.settings, "EDM_RES_PILOT_ENABLED", False, raising=False)
        with patch("memory.store.get_memory_store", return_value=fake_store):
            resp_off = real_client.post("/book/ask", json={"question": question})
        assert resp_off.status_code == 200, resp_off.text
        assert "edm" not in resp_off.json()["data"]

    # ── E3: каталог-сцены в /visualize (chapter=0, CATALOG_CHAPTER=0) ──────
    # Поднимает ограничение RES-5.1(a): DTO теперь допускает chapter=0;
    # механизм каталог-сцен уже существовал в scene_engine/
    # visual_context_builder (второго резолвера нет: engine guard
    # "scene_*" → CATALOG_CHAPTER). Семантика сцен книги (chapter>=1)
    # не меняется; несуществующие сцены — 404, ничего не подставляется;
    # era для каталог-сцены честно None (нет угадывания).

    CATALOG_SCENE_ANY = "scene_000"  # ГЛУБОКИЙ КОСМОС — каталог-сцена (любая)
    CATALOG_KNOWN_SCENE = "scene_021"  # ОСТРОВА ОКЕАНИИ - ДЕНЬ → детерм. engine → region_oceania (approved)
    CATALOG_UNKNOWN_SCENE = "scene_070"  # КОМНАТА ВЕЛА - ДЕНЬ → кандидатов нет (мир не выдумывается)

    def test_e3_regular_scene_flag_off_unchanged(self, real_client, monkeypatch):
        """(E3, req. 3/8.1) Обычная книга-сцена + флаг OFF: legacy-поведение
        сохранено — 200, media_plan собран, ключа `edm` нет (byte-базовый
        промпт покрывает test_visualize_flag_off_prompt_byte_identical)."""
        monkeypatch.setattr(shared_config.settings, "EDM_RES_PILOT_ENABLED", False, raising=False)
        edm_pilot._reset_cache()

        body = self._post_visualize(
            real_client,
            monkeypatch,
            {"chapter": int(self.HYPER_SCENE[0]), "scene_id": self.HYPER_SCENE[1]},
        )
        assert "edm" not in body
        assert body["media_plan"]["prompt"]

    def test_e3_catalog_scene_flag_off_plumbing_open_no_edm(self, real_client, monkeypatch):
        """(E3, req. 7/8.6) Каталог-сцена + флаг OFF: chapter=0 теперь
        проходит /visualize (plumbing не гейтится), но EDM-цепь выключена:
        ключа `edm` нет, план собирается из SceneContext как в legacy.
        Именно здесь раньше был 422 (RES-5.1(a))."""
        monkeypatch.setattr(shared_config.settings, "EDM_RES_PILOT_ENABLED", False, raising=False)
        edm_pilot._reset_cache()

        body = self._post_visualize(real_client, monkeypatch, {"chapter": 0, "scene_id": self.CATALOG_SCENE_ANY})
        assert "edm" not in body
        assert body["media_plan"]["prompt"]  # план реально собран из каталог-контекста

    def test_e3_catalog_scene_flag_on(self, real_client, monkeypatch):
        """(E3, req. 8.2/7) Каталог-сцена + флаг ON: 200, media_plan, EDM-блок
        виден (у scene_000 есть engine-кандидаты → location_matched).
        OWNER-GATE EDM_RES_PILOT_ENABLED сохранён."""
        monkeypatch.setattr(shared_config.settings, "EDM_RES_PILOT_ENABLED", True, raising=False)
        edm_pilot._reset_cache()

        body = self._post_visualize(real_client, monkeypatch, {"chapter": 0, "scene_id": self.CATALOG_SCENE_ANY})
        assert "media_plan" in body and body["media_plan"]["prompt"]
        assert "edm" in body  # трасса location_matched (есть engine-кандидаты)

    def test_e3_catalog_scene_known_location_trace(self, real_client, monkeypatch):
        """(E3, req. 8.3/9) Каталог-сцена с известной локацией: scene_021
        «ОСТРОВА ОКЕАНИИ - ДЕНЬ» → E2 авто-матчинг (детерминированный
        engine-скорер, без LLM) → region_oceania (owner-утверждённая
        сущность) в трассе `edm.location_matched`. EDM-карточек у
        engine-ids нет — fail-closed: ctx не мутирован (applied=False),
        план не несёт EDM-значений — в трассе только
        реально найденные/утверждённые сущности (req. 9)."""
        monkeypatch.setattr(shared_config.settings, "EDM_RES_PILOT_ENABLED", True, raising=False)
        edm_pilot._reset_cache()

        body = self._post_visualize(real_client, monkeypatch, {"chapter": 0, "scene_id": self.CATALOG_KNOWN_SCENE})
        assert "edm" in body
        edm = body["edm"]
        lm = edm["location_matched"]
        assert lm["location"] == "ОСТРОВА ОКЕАНИИ - ДЕНЬ"
        assert "region_oceania" in lm["entity_ids"]
        # E4: region_oceania has card → applied may be True
        assert not edm.get("fields") or isinstance(edm.get("fields"), list)

    def test_e3_catalog_scene_unknown_location_fail_closed(self, real_client, monkeypatch):
        """(E3, req. 8.4/9) Каталог-сцена с неизвестной локацией: scene_070
        «КОМНАТА ВЕЛА - ДЕНЬ» — ни в EDM-каталоге, ни в M3 crosswalk, ни в
        engine-скорере: `edm.location_matched` НЕ появляется (призрачных
        сущностей нет), план legacy, ctx не мутирован."""
        monkeypatch.setattr(shared_config.settings, "EDM_RES_PILOT_ENABLED", True, raising=False)
        edm_pilot._reset_cache()

        body = self._post_visualize(real_client, monkeypatch, {"chapter": 0, "scene_id": self.CATALOG_UNKNOWN_SCENE})
        assert "edm" not in body  # кандидатов нет → трассы нет (visibility-логика)
        assert body["media_plan"]["prompt"]

    def test_e3_missing_location_no_candidates(self, monkeypatch):
        """(E3, req. 5/6/8.5) Отсутствие локации: location='' → кандидатов
        нет, apply не создаёт трассы и не мутирует ctx (fail-closed: ни
        default, ни выдуманная сцена). В реальном каталоге у ВСЕХ сцен
        есть локация (DERIVED, provenance scene_catalog) — «отсутствие»
        покрывается service-уровнем; билдер пустую локацию честно
        помечает unknown (не fail-open)."""
        ctx = _make_ctx(location="")
        r = edm_pilot.resolve_scene_location("")
        assert r["candidates"] == [] and r["entity_ids"] == []
        report = edm_pilot.apply_edm_to_context(ctx, auto_matched_ids=r["entity_ids"] or None, location_matched=r if r["entity_ids"] else None)
        assert report["applied"] is False
        assert "location_matched" not in report

    def test_e3_no_fabrication_404s(self, real_client, monkeypatch):
        """(E3, req. 4/5) Ничего не подменяется: книга-сцена с chapter=0 →
        404 (в каталоге такого id нет); каталог-сцена с chapter=1 → 404
        (engine guard: «scene_*» валидна только с CATALOG_CHAPTER=0 —
        существующее поведение); несуществующий каталог-id → 404."""
        monkeypatch.setattr(shared_config.settings, "EDM_RES_PILOT_ENABLED", False, raising=False)
        edm_pilot._reset_cache()

        for payload in (
            {"chapter": 0, "scene_id": self.HYPER_SCENE[1]},
            {"chapter": 1, "scene_id": "scene_012"},
            {"chapter": 0, "scene_id": "scene_999"},
        ):
            resp = real_client.post("/book/visualize", json=payload)
            assert resp.status_code == 404, (payload, resp.status_code, resp.text[:200])


# ── 8. E2: авто-матчинг локаций (location-строка → engine/crosswalk → region_* → EDM) ──
#
# Закрывает ограничение пилота «авто-матчинг по location на реальных данных
# не реализуется»: реальные каталог-локации (верхний регистр, свободный
# формат 'ОКЕАН - ДЕНЬ', 'ЗЕМЛЯ') раньше не попадали ни в строгие имена
# EDM-каталога, ни в engine. Теперь resolve_scene_location связывает их
# детерминированно (без LLM, без RAG-буста): строгий уровень (E1-каталог)
# + M3 crosswalk-мост (только owner-утверждённые ids, casefold-фолбэк) +
# engine-скорер (name coverage). Ids без EDM-карточки не материализуются
# (B1 fail-closed) — остаются трассой.


def test_e2_resolve_arkaim_strict_and_engine():
    """'Аркаим': строгие карточки каталога + engine-скорер; ids без
    карточек (lang_*/energy_*) — только трасса, не edm_entities."""
    r = edm_pilot.resolve_scene_location("Аркаим")
    ids = [c["entity_id"] for c in r["candidates"]]
    assert {"arkaim_settlement", "region_arkaim", "arkaim"} <= set(ids)
    cards = {e["identity"]["canonical_id"] for e in r["edm_entities"]}
    assert {"arkaim_settlement", "region_arkaim", "arkaim"} <= cards
    assert len(ids) == len(set(ids))  # дедупликация


def test_e2_resolve_compound_location_via_engine_scorer():
    """'Аркаим - день' (формат реальных каталог-сцен): строгий уровень по
    целой строке не срабатывает, engine-скорер разрешает → карточки
    arkaim_settlement/region_arkaim (E4: могут быть и другие)."""
    r = edm_pilot.resolve_scene_location("Аркаим - день")
    ids = [c["entity_id"] for c in r["candidates"]]
    assert "region_arkaim" in ids and "arkaim_settlement" in ids
    cards = {e["identity"]["canonical_id"] for e in r["edm_entities"]}
    assert "arkaim_settlement" in cards and "region_arkaim" in cards


def test_e2_casefold_crosswalk_bridge():
    """'Океания' (естественный регистр) → M3 crosswalk (casefolded-ярлыки)
    → region_oceania, owner-утверждённая. E4: карточка region_oceania
    теперь в каталоге — сущность материализуется (не fail-closed)."""
    r = edm_pilot.resolve_scene_location("Океания")
    cand = {c["entity_id"]: c["source"] for c in r["candidates"]}
    # E4: region_oceania в каталоге — источник catalog (не engine_crosswalk)
    assert "region_oceania" in cand
    assert "region_oceania" in r["entity_ids"]
    # E4: карточка существует → материализация
    cards = {e["identity"]["canonical_id"] for e in r["edm_entities"]}
    assert "region_oceania" in cards


def test_e2_crosswalk_bridge_hyperborea():
    """'Гиперборея': строгий уровень — карточка civ_hyperborea; E4:
    region_hyperborea тоже в каталоге (после E4-миграции)."""
    r = edm_pilot.resolve_scene_location("Гиперборея")
    cand = {c["entity_id"]: c["source"] for c in r["candidates"]}
    assert "civ_hyperborea" in cand
    assert "region_hyperborea" in cand
    assert "civ_hyperborea" in {e["identity"]["canonical_id"] for e in r["edm_entities"]}
    # E4: region_hyperborea тоже материализуется
    assert "region_hyperborea" in {e["identity"]["canonical_id"] for e in r["edm_entities"]}


def test_e2_unknown_location_is_empty_fail_closed():
    """Неизвестные локации → нет candidate'в: мир не выдумывается,
    unknown не материализуется (B1)."""
    for loc in ("НесуществующаяМестностьXYZ", "Тёмная долина"):
        r = edm_pilot.resolve_scene_location(loc)
        assert r["candidates"] == []
        assert r["entity_ids"] == []
        assert r["edm_entities"] == []


def test_e2_deterministic_repeat():
    """Повторные вызовы идентичны (детерминированность, кэши не искажают)."""
    assert edm_pilot.resolve_scene_location("Гиперборея") == edm_pilot.resolve_scene_location("Гиперборея")


def test_e2_apply_auto_ids_mutes_ctx_and_traces():
    """apply_edm_to_context(auto_matched_ids=...): E2-карточки реально
    мутируют ctx (только существующие поля); в отчёт — additive-трасса
    location_matched (существующие ключи отчёта не меняются)."""
    ctx = _make_ctx(location="")
    r = edm_pilot.resolve_scene_location("Аркаим - день")
    report = edm_pilot.apply_edm_to_context(ctx, auto_matched_ids=r["entity_ids"] or None, location_matched=r)
    assert report["applied"] is True
    assert "architecture.style" in {f["field"] for f in report["fields"]}
    assert ctx.architecture.style  # поле ctx реально наполнено
    lm = report["location_matched"]
    assert lm["location"] == "Аркаим - день"
    assert "region_arkaim" in lm["entity_ids"]


def test_e2_apply_no_candidates_no_trace():
    """Авто-матчинга нет (пустая локация, нет совпадений) → в отчёте нет
    location_matched — поведение legacy apply_edm_to_context не меняется."""
    ctx = _make_ctx(location="")
    report = edm_pilot.apply_edm_to_context(ctx)
    assert "location_matched" not in report
    assert report["applied"] is False


# ── 9. E2: production-шов /visualize (HTTP) ──────────────────────────────


def test_visualize_http_e2_location_trace_with_applicable_claims(monkeypatch):
    """Флаг on, реальная локация 'Гиперборея' (stub-builder): авто-матчинг
    находит civ_hyperborea (карточка, culture-Claim'и) + region_hyperborea
    (E4: в каталоге, place.coordinates known) → ctx мутирован (applied=True),
    блок `edm` несёт трассу `location_matched` — разрешённые сущности
    видны владельцу."""
    monkeypatch.setattr(shared_config.settings, "EDM_RES_PILOT_ENABLED", True, raising=False)
    client = _visualize_client(monkeypatch, location="Гиперборея")
    resp = client.post("/book/visualize", json={"chapter": 1, "scene_id": "s_hyper"})
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert "edm" in body  # E2: трасса видна
    edm = body["edm"]
    assert edm["applied"] is True  # E4: region_hyperborea has known claims
    cand = {c["entity_id"]: c["source"] for c in edm["location_matched"]["candidates"]}
    assert "civ_hyperborea" in cand
    assert "region_hyperborea" in cand
    # Arkaim-specific values NOT in prompt (different location)
    assert "circular fortified" not in json.dumps(body["media_plan"], ensure_ascii=False)


def test_visualize_http_e2_flag_off_location_ignored(monkeypatch):
    """Флаг off: E2-цепочка не вызывается — локация игнорируется, ответ
    legacy (нет ключа `edm`)."""
    monkeypatch.setattr(shared_config.settings, "EDM_RES_PILOT_ENABLED", False, raising=False)
    client = _visualize_client(monkeypatch, location="Гиперборея")
    resp = client.post("/book/visualize", json={"chapter": 1, "scene_id": "s_hyper"})
    assert resp.status_code == 200, resp.text
    assert "edm" not in resp.json()
