"""Этап 5: API-решения по гипотезам/сценариям (persist + RBAC).

Проверяется реальный сценарий из плана:
  GET hypotheses → accept → «перезапуск» (новый клиент/новые store) →
  GET снова показывает ту же гипотезу со статусом accepted.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_CORE = _PROJECT_ROOT / "core" / "CORE"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))


def _client_for_role(
    role: str | None,
    data_dir: Path,
    monkeypatch,
) -> TestClient:
    from auth import rbac
    from narrative_engine import api_routes
    from narrative_engine.branch_manager import ScenarioStore
    from narrative_engine.hypothesis_generator import HypothesisStore
    from narrative_engine.performance import _hypotheses_cache
    from narrative_engine.world_explorer import WorldExplorer

    _hypotheses_cache.clear()

    def explorer_factory(world_model):
        return WorldExplorer(
            world_model,
            graph_engine=None,
            hypothesis_store=HypothesisStore(data_dir),
            scenario_store=ScenarioStore(data_dir),
        )

    app = FastAPI()
    app.include_router(api_routes.router)

    # Подменяем только фабрику explorer: маршруты и stores — настоящие.
    monkeypatch.setattr(api_routes, "WorldExplorer", explorer_factory)

    if role is None:

        async def anon_user() -> dict:
            raise HTTPException(status_code=401, detail="Не авторизован")

        app.dependency_overrides[rbac.get_current_user] = anon_user
    else:

        async def fixed_user() -> dict:
            return {"user_id": "stage5-test", "role": role, "provider": "test"}

        app.dependency_overrides[rbac.get_current_user] = fixed_user

    return TestClient(app)


def _get_hypotheses(
    client: TestClient,
    epoch: str = "satya_yuga",
    limit: int = 3,
) -> list[dict]:
    response = client.get(f"/world-explorer/hypotheses/{epoch}", params={"limit": limit})
    assert response.status_code == 200, response.text
    return response.json()["data"]


class TestHypothesisDecisionApi:
    def test_accept_survives_restart(self, tmp_path: Path, monkeypatch):
        client = _client_for_role("editor", tmp_path, monkeypatch)
        hypotheses = _get_hypotheses(client)
        assert hypotheses

        target = hypotheses[0]
        assert target["status"] == "proposed"

        response = client.post(f"/world-explorer/hypothesis/{target['id']}/accept")
        assert response.status_code == 200, response.text
        assert response.json()["data"]["status"] == "accepted"

        # «Перезапуск сервера»: новый клиент и новые экземпляры stores.
        restarted = _client_for_role("editor", tmp_path, monkeypatch)
        again = _get_hypotheses(restarted, limit=10)
        same = [h for h in again if h["id"] == target["id"]]
        assert same, f"гипотеза {target['id']} исчезла после перезапуска"
        assert same[0]["status"] == "accepted"

    def test_reject_marks_status(self, tmp_path: Path, monkeypatch):
        client = _client_for_role("editor", tmp_path, monkeypatch)
        hypotheses = _get_hypotheses(client, limit=2)
        assert len(hypotheses) >= 2

        target = hypotheses[1]
        response = client.post(
            f"/world-explorer/hypothesis/{target['id']}/reject",
            json={"reason": "не по канону"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["data"]["status"] == "rejected"

        again = _get_hypotheses(client, limit=10)
        assert target["id"] not in {h["id"] for h in again}

    def test_unknown_hypothesis_returns_404(self, tmp_path: Path, monkeypatch):
        client = _client_for_role("editor", tmp_path, monkeypatch)
        response = client.post("/world-explorer/hypothesis/nope/accept")
        assert response.status_code == 404


class TestScenarioSupersedeApi:
    def _propose_scenario(self, data_dir: Path) -> str:
        from narrative_engine.branch_manager import ScenarioStore
        from narrative_engine.scenario_modeler import ScenarioBranch

        branch = ScenarioBranch(
            id="hyp_test_conservative",
            hypothesis_id="hyp_test",
            title="Conservative",
            title_ru="Консервативная ветвь",
            branch_type="conservative",
        )
        ScenarioStore(data_dir).propose(branch)
        return branch.id

    def test_supersede_keeps_history(self, tmp_path: Path, monkeypatch):
        scenario_id = self._propose_scenario(tmp_path)
        client = _client_for_role("editor", tmp_path, monkeypatch)

        response = client.post(
            f"/world-explorer/scenario/{scenario_id}/supersede",
            json={"superseded_by": "hyp_test_radical", "reason": "уточнение"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["data"]["status"] == "superseded"

        from narrative_engine.branch_manager import ScenarioStore

        record = ScenarioStore(tmp_path).get(scenario_id)
        assert record.status == "superseded"
        assert record.superseded_by == "hyp_test_radical"

    def test_supersede_unknown_returns_404(self, tmp_path: Path, monkeypatch):
        client = _client_for_role("editor", tmp_path, monkeypatch)
        response = client.post(
            "/world-explorer/scenario/ghost/supersede",
            json={"superseded_by": "other"},
        )
        assert response.status_code == 404


class TestDecisionRbac:
    def test_reader_cannot_decide(self, tmp_path: Path, monkeypatch):
        client = _client_for_role("reader", tmp_path, monkeypatch)
        assert client.post("/world-explorer/hypothesis/x/accept").status_code == 403
        assert client.post("/world-explorer/hypothesis/x/reject").status_code == 403
        assert (
            client.post(
                "/world-explorer/scenario/x/supersede",
                json={"superseded_by": "y"},
            ).status_code
            == 403
        )

    def test_anonymous_gets_401(self, tmp_path: Path, monkeypatch):
        client = _client_for_role(None, tmp_path, monkeypatch)
        assert client.post("/world-explorer/hypothesis/x/accept").status_code == 401
