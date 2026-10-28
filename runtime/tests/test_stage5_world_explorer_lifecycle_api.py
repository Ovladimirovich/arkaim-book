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


class TestScenarioListApi:
    """Этап 6b: список сценариев и видимый результат замены (UI-путь)."""

    def _propose(
        self,
        data_dir: Path,
        scenario_id: str,
        hypothesis_id: str = "hyp_test",
        branch_type: str = "conservative",
    ) -> str:
        from narrative_engine.branch_manager import ScenarioStore
        from narrative_engine.scenario_modeler import ScenarioBranch

        ScenarioStore(data_dir).propose(
            ScenarioBranch(
                id=scenario_id,
                hypothesis_id=hypothesis_id,
                title=branch_type.title(),
                title_ru=f"{branch_type} ветвь",
                branch_type=branch_type,
            )
        )
        return scenario_id

    def _list(
        self,
        client: TestClient,
        **params,
    ) -> list[dict]:
        response = client.get("/world-explorer/scenarios", params=params)
        assert response.status_code == 200, response.text
        return response.json()["data"]

    def test_list_returns_active_scenarios(self, tmp_path: Path, monkeypatch):
        self._propose(tmp_path, "hyp_test_conservative")
        self._propose(tmp_path, "hyp_test_radical", branch_type="radical")
        client = _client_for_role("editor", tmp_path, monkeypatch)

        scenarios = self._list(client)

        assert {s["id"] for s in scenarios} == {
            "hyp_test_conservative",
            "hyp_test_radical",
        }
        assert all(s["status"] == "proposed" for s in scenarios)
        assert all(s["superseded_by"] == "" for s in scenarios)

    def test_list_filters_by_hypothesis(self, tmp_path: Path, monkeypatch):
        self._propose(tmp_path, "hyp_a_conservative", hypothesis_id="hyp_a")
        self._propose(tmp_path, "hyp_b_radical", hypothesis_id="hyp_b")
        client = _client_for_role("editor", tmp_path, monkeypatch)

        scenarios = self._list(client, hypothesis_id="hyp_a")

        assert [s["id"] for s in scenarios] == ["hyp_a_conservative"]

    def test_supersede_hides_from_active_but_keeps_history(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """Пользовательский путь: список → выбор → замена → результат виден."""
        old_id = self._propose(tmp_path, "hyp_test_conservative")
        new_id = self._propose(tmp_path, "hyp_test_radical", branch_type="radical")
        client = _client_for_role("editor", tmp_path, monkeypatch)

        assert {s["id"] for s in self._list(client)} == {old_id, new_id}

        response = client.post(
            f"/world-explorer/scenario/{old_id}/supersede",
            json={"superseded_by": new_id, "reason": "уточнение"},
        )
        assert response.status_code == 200, response.text

        active = self._list(client)
        assert [s["id"] for s in active] == [new_id], "заменённый сценарий остался активным"

        history = self._list(client, include_history=True)
        by_id = {s["id"]: s for s in history}
        assert by_id[old_id]["status"] == "superseded"
        assert by_id[old_id]["superseded_by"] == new_id
        assert by_id[old_id]["decision_note"] == "уточнение"
        assert by_id[new_id]["status"] == "proposed"
        assert len(history) == 2

    def test_superseded_survives_restart(self, tmp_path: Path, monkeypatch):
        old_id = self._propose(tmp_path, "hyp_test_conservative")
        new_id = self._propose(tmp_path, "hyp_test_radical", branch_type="radical")
        client = _client_for_role("editor", tmp_path, monkeypatch)
        client.post(
            f"/world-explorer/scenario/{old_id}/supersede",
            json={"superseded_by": new_id, "reason": "уточнение"},
        )

        # «Перезапуск сервера»: новые store и клиент, тот же каталог данных.
        restarted = _client_for_role("editor", tmp_path, monkeypatch)
        history = {s["id"]: s for s in self._list(restarted, include_history=True)}

        assert history[old_id]["status"] == "superseded"
        assert history[old_id]["superseded_by"] == new_id
        assert [s["id"] for s in self._list(restarted)] == [new_id]

    def test_reader_can_read_scenarios(self, tmp_path: Path, monkeypatch):
        self._propose(tmp_path, "hyp_test_conservative")
        reader = _client_for_role("reader", tmp_path, monkeypatch)

        assert [s["id"] for s in self._list(reader)] == ["hyp_test_conservative"]


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
