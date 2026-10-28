# -*- coding: utf-8 -*-
"""Q3: HTTP API очереди проверки кандидатов LLM.

Реальный цикл через TestClient(app):
    candidate → GET /api/candidates → approve/reject → GET → проверка состояния.

Покрытие:
- список (GET /api/candidates) и статистика (GET /api/candidates/stats);
- решения approve/reject/reopen через единственный движок Q2;
- ошибки: 401 без авторизации, 403 недостаточно прав, 404 нет кандидата,
  400 без комментария и 409 конфликт статуса;
- APPROVED не меняет provenance_category (SYSTEM_INTERPRETATION) — не канон.

Изоляция: роутер импортирует `scan_candidates`/`decide` на уровне модуля,
поэтому тест подменяет их на версии с tmp-каталогом (реальный KNOWLEDGE и
OS_DATA/review не затрагиваются; журнал и бэкапы тоже в tmp).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from core.main import app
from auth.rbac import get_current_user
from core.routes import review_queue as rq

from knowledge_expansion.review import (
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    decide as _decide,
    scan_candidates as _scan,
)

PENDING = STATUS_PENDING
APPROVED = STATUS_APPROVED
REJECTED = STATUS_REJECTED


def _meta(status: str = PENDING, **overrides) -> dict:
    meta = {
        "category": "DERIVED",
        "provenance_category": "SYSTEM_INTERPRETATION",
        "source_level": "SYSTEM_INTERPRETATION",
        "source": "LLM",
        "model": "GigaChat",
        "generated_at": "2026-10-28T12:00:00+00:00",
        "requires_author_review": True,
        "status": status,
    }
    meta.update(overrides)
    return meta


def _item(topic: str, literal: str = "Небесный круг", status: str = PENDING) -> dict:
    meta = _meta(status)
    return {
        "topic": topic,
        "content": "",
        "layers": {"literal": literal, "metaphorical": "путь восхождения"},
        "metadata": {"_provenance_metadata": dict(meta)},
        "_provenance_metadata": meta,
    }


def _wrapped(*items: dict) -> dict:
    return {"_provenance_metadata": {"category": "DERIVED"}, "items": list(items)}


def _write(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _role_user(role: str):
    async def _user():
        return {
            "user_id": f"test-{role}",
            "role": role,
            "provider": "test",
            "username": role,
            "display_name": f"Test {role}",
        }

    return _user


async def _no_auth():
    from fastapi import HTTPException

    raise HTTPException(status_code=401, detail="Не авторизован")


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _restore_auth_override():
    """Каждый тест стартует с admin-переопределением, после — восстановить прежнее.

    Меняем на setup+restore: исходная версия выставляла `_role_user("admin")`
    только в teardown, из-за чего user_id `test-admin` «протекал» в последующие
    тесты (14 flaky studio-тестов в полном прогоне). Теперь admin активен во
    время теста (как раньше), а после теста возвращается conftest-дефолт
    `_fake_user`.
    """
    saved = dict(app.dependency_overrides)
    app.dependency_overrides[get_current_user] = _role_user("admin")
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(saved)


@pytest.fixture
def isolated_queue(tmp_path: Path, monkeypatch):
    """Очередь на tmp-каталоге: роутер работает с изолированными данными."""
    knowledge = tmp_path / "KNOWLEDGE"
    knowledge.mkdir()
    _write(
        knowledge / "PHILOSOPHY_DEEP.json",
        _wrapped(_item("Сварга"), _item("Заря", "Новый рассвет")),
    )
    journal = tmp_path / "journal.jsonl"
    backups = tmp_path / "backups"

    def _scan_isolated():
        return _scan(knowledge_dir=knowledge)

    def _decide_isolated(candidate_id, action, **kwargs):
        return _decide(
            candidate_id,
            action,
            knowledge_dir=knowledge,
            journal_path=journal,
            backup_dir=backups,
            **kwargs,
        )

    monkeypatch.setattr(rq, "scan_candidates", _scan_isolated)
    monkeypatch.setattr(rq, "decide", _decide_isolated)
    return knowledge


# ═══════════════════════════════════════════════════════════
# 1. Список и статистика
# ═══════════════════════════════════════════════════════════


class TestCandidatesList:
    def test_list_returns_candidates(self, client, isolated_queue):
        resp = client.get("/api/candidates")

        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["total"] == 2
        topics = {item["topic"] for item in body["data"]}
        assert topics == {"Сварга", "Заря"}
        item = next(i for i in body["data"] if i["topic"] == "Сварга")
        assert item["status"] == PENDING
        assert item["source"] == "LLM"
        assert item["model"] == "GigaChat"
        assert item["requires_author_review"] is True
        assert item["provenance_category"] == "SYSTEM_INTERPRETATION"
        assert item["candidate_id"]
        assert item["locator"] == "PHILOSOPHY_DEEP.json#items[0]"

    def test_stats(self, client, isolated_queue):
        resp = client.get("/api/candidates/stats")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 2
        assert data["pending"] == 2
        assert data["by_status"][PENDING] == 2
        assert data["by_file"] == {"PHILOSOPHY_DEEP.json": 2}

    def test_filter_by_status(self, client, isolated_queue):
        _reject_first(client, isolated_queue)

        resp = client.get("/api/candidates", params={"status": REJECTED})

        assert resp.status_code == 200
        assert all(i["status"] == REJECTED for i in resp.json()["data"])

    def test_openapi_has_five_endpoints(self, client):
        schema = client.get("/openapi.json").json()
        found = [p for p in schema["paths"] if p.startswith("/api/candidates")]
        assert len(found) == 5, f"ожидалось 5 путей, есть: {found}"


def _first_id(client, isolated_queue) -> str:
    return client.get("/api/candidates").json()["data"][0]["candidate_id"]


def _reject_first(client, isolated_queue) -> str:
    cid = _first_id(client, isolated_queue)
    resp = client.post(f"/api/candidates/{cid}/reject", json={"comment": "Не из книги"})
    assert resp.status_code == 200, resp.text
    return cid


# ═══════════════════════════════════════════════════════════
# 2. Цикл решений: GET → approve/reject → GET
# ═══════════════════════════════════════════════════════════


class TestReviewCycle:
    def test_approve_cycle_through_api(self, client, isolated_queue):
        cid = _first_id(client, isolated_queue)

        resp = client.post(
            f"/api/candidates/{cid}/approve",
            json={"comment": "Согласуется с главой 4"},
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["candidate_id"] == cid
        assert data["status"] == APPROVED
        assert data["requires_author_review"] is False
        assert data["reviewed_by"] == "Test admin"
        assert data["provenance_category"] == "SYSTEM_INTERPRETATION"

        after = client.get("/api/candidates").json()["data"]
        updated = next(i for i in after if i["candidate_id"] == cid)
        assert updated["status"] == APPROVED

    def test_reject_keeps_record_with_explicit_status(self, client, isolated_queue):
        cid = _first_id(client, isolated_queue)

        resp = client.post(
            f"/api/candidates/{cid}/reject",
            json={"comment": "Формулировка не из книги"},
        )

        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == REJECTED

        after = client.get("/api/candidates").json()["data"]
        updated = next(i for i in after if i["candidate_id"] == cid)
        assert updated["status"] == REJECTED
        assert updated["requires_author_review"] is True
        assert updated["review_comment"] == "Формулировка не из книги"

    def test_reopen_returns_to_review(self, client, isolated_queue):
        cid = _reject_first(client, isolated_queue)

        resp = client.post(
            f"/api/candidates/{cid}/reopen",
            json={"comment": "Проверить ещё раз"},
        )

        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == PENDING

    def test_approve_does_not_rewrite_provenance_category(self, client, isolated_queue):
        """APPROVED остаётся SYSTEM_INTERPRETATION — не становится каноном."""
        cid = _first_id(client, isolated_queue)

        client.post(f"/api/candidates/{cid}/approve", json={"comment": "Одобрено"})

        file_body = json.loads((isolated_queue / "PHILOSOPHY_DEEP.json").read_text(encoding="utf-8"))
        record = file_body["items"][0]
        assert record["_provenance_metadata"]["provenance_category"] == "SYSTEM_INTERPRETATION"
        assert record["_provenance_metadata"]["status"] == APPROVED
        assert record["_provenance_metadata"]["requires_author_review"] is False


# ═══════════════════════════════════════════════════════════
# 3. Ошибки: 400 / 403 / 404 / 409 / 401
# ═══════════════════════════════════════════════════════════


class TestErrors:
    def test_401_without_auth(self, client, isolated_queue):
        app.dependency_overrides[get_current_user] = _no_auth

        resp = client.get("/api/candidates")

        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "HTTP_401"

    def test_403_reader_cannot_decide(self, client, isolated_queue):
        app.dependency_overrides[get_current_user] = _role_user("reader")
        cid = _first_id(client, isolated_queue)

        resp = client.post(
            f"/api/candidates/{cid}/approve",
            json={"comment": "Попытка читателя"},
        )

        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "HTTP_403"

    def test_400_approve_without_comment(self, client, isolated_queue):
        cid = _first_id(client, isolated_queue)

        resp = client.post(f"/api/candidates/{cid}/approve", json={})

        assert resp.status_code == 400
        assert "комментари" in resp.json()["error"]["message"]

    def test_400_approve_with_short_comment(self, client, isolated_queue):
        cid = _first_id(client, isolated_queue)

        resp = client.post(f"/api/candidates/{cid}/approve", json={"comment": "ok"})

        assert resp.status_code == 400

    def test_404_unknown_candidate(self, client, isolated_queue):
        resp = client.post(
            "/api/candidates/cand_000000000000/approve",
            json={"comment": "Обоснование здесь"},
        )

        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "HTTP_404"

    def test_409_invalid_transition(self, client, isolated_queue):
        cid = _reject_first(client, isolated_queue)

        resp = client.post(
            f"/api/candidates/{cid}/approve",
            json={"comment": "Передумал одобрить"},
        )

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "HTTP_409"

    def test_409_stale_expected_status(self, client, isolated_queue):
        cid = _first_id(client, isolated_queue)

        resp = client.post(
            f"/api/candidates/{cid}/approve",
            json={"comment": "Одобрено", "expected_status": APPROVED},
        )

        assert resp.status_code == 409
        assert "изменился" in resp.json()["error"]["message"]
