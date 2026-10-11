"""MD-2 маршрутные тесты: пять живых путей на едином SceneContext-входе.

Каждый тест фиксирует контракт «до = после» миграции: тот же статус-код,
та же структура ответа, тот же промпт-паттерн; плюс MD-2-инварианты
(temporal read-only, без синтеза связей, media-neutral).

Запуск (из runtime/):
  .venv\\Scripts\\python -m pytest tests/test_md2_routes.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
sys.path.insert(0, str(CORE_DIR))

from fastapi.testclient import TestClient

from core.main import app


@pytest.fixture(autouse=True)
def _isolate_global_state():
    """Изоляция MD-2-тестов от кумулятивного состояния pytest-процесса.

    1. registry._instances: откат после каждого теста (закэшированные
       визуальные сервисы pollute temporal/m10/m7-тесты).
    2. main._rate_limits: сброс ДО и ПОСЛЕ каждого теста. Причина:
       rate-limiter (100 req/60с sliding) общий на процесс; в комбинации
       с temporal-семьёй (~83 запроса) мои ~21 запроса пересекают лимит,
       429-путь middleware читает несуществующий атрибут
       SharedSettings.RATE_LIMIT_REQUESTS_PER_MINUTE (pre-existing дефект,
       см. docs/M8_1_POST_IMPLEMENTATION_AUDIT.md, Failure 1) и падает
       AttributeError → 500. Это тест-гигиена, НЕ фикс продукта.
    """
    from core.services.registry import registry
    from core import main as _main_mod

    saved_instances = dict(registry._instances)
    _main_mod._rate_limits.clear()  # fresh start: не наследуем счётчик
    yield
    _main_mod._rate_limits.clear()  # не оставляем свой счётчик другим
    registry._instances.clear()
    registry._instances.update(saved_instances)


@pytest.fixture
def client():
    return TestClient(app)


# ── Маршрут D: /assets/generate-context (канонический вход) ────────


class TestRouteDGenerateContext:
    def test_generate_context_returns_media_plan_with_scene(self, client):
        """Контракт: 200 + media_plan dict с prompt; сцена собирается из genome."""
        resp = client.post("/book/assets/generate-context", params={"chapter": 1, "scene_id": "conflict_гиперборея_материальный_путь_атлантиды"})
        assert resp.status_code == 200
        data = resp.json()
        assert "media_plan" in data
        mp = data["media_plan"]
        assert isinstance(mp, dict)
        assert "prompt" in mp
        assert len(mp["prompt"]) > 0

    def test_generate_context_explicit_epoch_accepted(self, client):
        """MD-2: явный epoch_id принимается (temporal-параметр канонического входа)."""
        resp = client.post(
            "/book/assets/generate-context", params={"chapter": 1, "scene_id": "conflict_гиперборея_материальный_путь_атлантиды", "epoch_id": "arkaim_era"}
        )
        assert resp.status_code == 200
        assert "media_plan" in resp.json()


# ── Маршрут A: /visualize (сцена) ──────────────────────────────────


class TestRouteAVisualize:
    def test_visualize_contract_media_plan(self, client):
        """Контракт: 200 + media_plan dict с prompt."""
        resp = client.post("/book/visualize", json={"chapter": 1, "scene_id": "conflict_гиперборея_материальный_путь_атлантиды"})
        assert resp.status_code == 200
        body = resp.json()
        assert "media_plan" in body
        mp = body["media_plan"]
        assert isinstance(mp, dict)
        assert "prompt" in mp
        assert len(mp["prompt"]) > 0

    def test_visualize_404_unknown_scene(self, client):
        resp = client.post("/book/visualize", json={"chapter": 99, "scene_id": "nope"})
        assert resp.status_code == 404


# ── Маршрут B: /visualize/epoch/{epoch_id} (temporal-мост M7.2) ────


class TestRouteBVisualizeEpoch:
    def test_epoch_contract_media_plan(self, client):
        """200 + media_plan dict; эпоха из WorldModel; read-only."""
        resp = client.post("/book/visualize/epoch/arkaim_era")
        assert resp.status_code == 200
        body = resp.json()
        assert "media_plan" in body
        mp = body["media_plan"]
        assert isinstance(mp, dict)
        assert "prompt" in mp
        assert len(mp["prompt"]) > 0

    def test_epoch_404_unknown(self, client):
        resp = client.post("/book/visualize/epoch/nonexistent_epoch")
        assert resp.status_code == 404

    def test_world_model_not_mutated(self, client):
        """Инвариант: visualize-epoch не мутирует WORLD_MODEL (read-only)."""
        from narrative_engine.world_model import WorldModel

        before = WorldModel.load()
        client.post("/book/visualize/epoch/arkaim_era")
        after = WorldModel.load()
        assert before._data == after._data


# ── Удалённые маршруты: /assets/generate, /assets/generate-character,
#    /assets/generate-location, /shots/{id}/generate
#    Тестируем, что они возвращают 404.
# ──


class TestRemovedRoutesReturnNotFound:
    def test_assets_generate_removed(self, client):
        resp = client.post("/book/assets/generate", params={"chapter": 1, "scene_id": "conflict_гиперборея_материальный_путь_атлантиды"})
        assert resp.status_code in (404, 405)

    def test_assets_generate_character_removed(self, client):
        resp = client.post("/book/assets/generate-character", params={"character_id": "Световит"})
        assert resp.status_code in (404, 405)

    def test_assets_generate_location_removed(self, client):
        resp = client.post("/book/assets/generate-location", params={"location_id": "граница миров"})
        assert resp.status_code in (404, 405)

    def test_film_shot_generate_removed(self, client):
        """POST /book/film/{id}/scenes/{id}/shots/{id}/generate удалён."""
        resp = client.post("/book/film/any_pid/scenes/any_sid/shots/any_shid/generate")
        assert resp.status_code in (404, 405)


# ── Инварианты MD-2 по всем маршрутам ──────────────────────────────


class TestMD2RouteInvariants:
    def test_scene_context_has_no_execution_fields(self, client):
        """Сгенерированный MediaPlan: execution живут в generation (домен
        результата), а MediaPlan.prompt не содержит steps/seed/model
        значений (media-neutral контекст)."""
        resp = client.post("/book/assets/generate-context", params={"chapter": 1, "scene_id": "conflict_гиперборея_материальный_путь_атлантиды"})
        mp = resp.json()["media_plan"]
        prompt = mp["prompt"]
        for banned in ("steps:", "seed:", "cfg:", "sampler=", "checkpoint"):
            assert banned not in prompt.lower(), f"execution-утечка в промпт: {banned}"

    def test_builder_returns_canonical_extras(self, client):
        """DI-инстанс builder'а строит контекст с scene_extras (temporal/integrity)."""
        from core.services.registry import registry

        b = registry.get("visual_context_builder")
        import asyncio

        ctx = asyncio.run(b.build_scene_context(1, "conflict_гиперборея_материальный_путь_атлантиды"))
        assert ctx.scene_extras is not None
        assert ctx.scene_extras.integrity.links_synthesized is False
        assert ctx.scene_extras.source_refs.scene_id == "conflict_гиперборея_материальный_путь_атлантиды"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
