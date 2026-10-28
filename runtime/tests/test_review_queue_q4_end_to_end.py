# -*- coding: utf-8 -*-
"""Q4: приёмочный сквозной сценарий очереди проверки (без загрязнения данных).

Сценарий: 5 кандидатов → экран/очередь (GET) → APPROVE одного → REJECT одного
→ проверка статусов → APPROVED проходит в RAG (ExpansionLoader) и в
WORLD MODEL (world_extraction.provenance) → подтверждение APPROVED ≠ CANON.

Всё на tmp-каталоге: реальный KNOWLEDGE и журнал не трогаются. Гейты
«APPROVED видно потребителям / PENDING-REJECTED спрятаны» проверяются
через те же функции, которыми их читают RAG и мир.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from core.routes import review_queue as rq
from knowledge_expansion.expansion_loader import ExpansionLoader
from knowledge_expansion.provenance_gate import record_is_unverified
from knowledge_expansion.review import scan_candidates as _scan
from world_extraction import provenance as world_prov


# ── Данные: 5 кандидатов + 1 «проверенный» контроль ─────────────────────

CANDIDATES = [
    "Сварга",
    "Заря",
    "Бесовская гора",
    "Путь в горы",
    "Небесный круг",
]
CANON_TOPIC = "Городище Аркаим"


def _meta(status: str, **overrides) -> dict:
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


def _candidate_item(topic: str, status: str = "PENDING_REVIEW") -> dict:
    meta = _meta(status)
    return {
        "topic": topic,
        "content": "",
        "layers": {"literal": f"слоёвый слой: {topic}", "metaphorical": "смысл"},
        "metadata": {"_provenance_metadata": dict(meta)},
        "_provenance_metadata": meta,
    }


def _canon_item(topic: str = CANON_TOPIC) -> dict:
    """Проверенное знание без провенанса — «канон», который проходит всегда."""
    return {
        "topic": topic,
        "content": "Запись из книги, не требует проверки",
        "layers": {"literal": "городище", "metaphorical": "целостность"},
    }


def _write(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


@pytest.fixture
def q4_env(tmp_path: Path, monkeypatch):
    """Изолированный KNOWLEDGE + журнал + бэкапы; роутер работает с ними."""
    knowledge = tmp_path / "KNOWLEDGE"
    knowledge.mkdir()
    items = [_candidate_item(t) for t in CANDIDATES] + [_canon_item()]
    _write(
        knowledge / "PHILOSOPHY_DEEP.json",
        {"_provenance_metadata": {"category": "DERIVED"}, "items": items},
    )
    journal = tmp_path / "decisions.jsonl"
    backups = tmp_path / "backups"
    backups.mkdir()

    def _scan_isolated():
        return _scan(knowledge_dir=knowledge)

    from knowledge_expansion.review import decide as _decide

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

    from auth.rbac import get_current_user
    from core.main import app

    async def _admin():
        return {
            "user_id": "test-admin",
            "role": "admin",
            "provider": "test",
            "username": "admin",
            "display_name": "Владелец",
        }

    # monkeypatch снимает переопределение после теста и возвращает дефолт
    # conftest (`_fake_user`), иначе user_id `test-admin` «протекал» бы в
    # последующие тесты (14 flaky studio-тестов в полном прогоне).
    monkeypatch.setitem(app.dependency_overrides, get_current_user, _admin)

    return SimpleNamespace(
        knowledge=knowledge,
        journal=journal,
        backups=backups,
        file=knowledge / "PHILOSOPHY_DEEP.json",
    )


def _client(q4_env):
    from fastapi.testclient import TestClient
    from core.main import app

    return TestClient(app)


def _by_topic(client, topic: str) -> dict:
    data = client.get("/api/candidates").json()["data"]
    for item in data:
        if item["topic"] == topic:
            return item
    raise AssertionError(f"Тема {topic!r} не найдена в очереди")


def _world_result(source_file: Path, topics: list[str]):
    """Минимальный результат экстрактора мира для гейта 6e."""
    return SimpleNamespace(
        source_files=[source_file],
        items_count=len(topics),
        items=[SimpleNamespace(name=t, name_ru=t, source=source_file.name) for t in topics],
    )


class TestAcceptanceScenario:
    def test_queue_lists_five_candidates(self, q4_env):
        client = _client(q4_env)
        data = client.get("/api/candidates").json()["data"]
        topics = {item["topic"] for item in data}
        assert topics == set(CANDIDATES)
        # Канон-запись без провенанса в очередь не попадает.
        assert CANON_TOPIC not in topics
        assert all(item["status"] == "PENDING_REVIEW" for item in data)

    def test_full_acceptance_cycle(self, q4_env):
        client = _client(q4_env)

        # 1) Approve первой темы с обязательным комментарием.
        approved = _by_topic(client, CANDIDATES[0])
        resp = client.post(
            f"/api/candidates/{approved['candidate_id']}/approve",
            json={"comment": "Согласуется с главой 4"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["status"] == "APPROVED"

        # 2) Reject второй темы (также с комментарием).
        rejected = _by_topic(client, CANDIDATES[1])
        resp = client.post(
            f"/api/candidates/{rejected['candidate_id']}/reject",
            json={"comment": "Формулировка не из книги"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["status"] == "REJECTED"

        # 3) Статусы: одобренный APPROVED, отклонённый REJECTED, остальные PENDING.
        assert _by_topic(client, CANDIDATES[0])["status"] == "APPROVED"
        assert _by_topic(client, CANDIDATES[1])["status"] == "REJECTED"
        assert _by_topic(client, CANDIDATES[2])["status"] == "PENDING_REVIEW"

        stats = client.get("/api/candidates/stats").json()["data"]
        assert stats["by_status"]["APPROVED"] == 1
        assert stats["by_status"]["REJECTED"] == 1
        assert stats["by_status"]["PENDING_REVIEW"] == len(CANDIDATES) - 2

        # 4) APPROVED проходит в RAG (ExpansionLayer).
        loader = ExpansionLoader(knowledge_dir=q4_env.knowledge)
        loader.load()
        assert loader.get(CANDIDATES[0].lower()) is not None, "одобренная запись не в RAG"
        # 5) APPROVED проходит в WORLD MODEL (гейт 6e).
        world = _world_result(q4_env.file, [CANDIDATES[0], CANON_TOPIC])
        dropped = world_prov.filter_extraction_result(world)
        world_names = [item.name for item in world.items]
        assert CANDIDATES[0] in world_names, "одобренная запись не в мире"
        assert CANON_TOPIC in world_names, "канон должен быть в мире"
        assert dropped == 0

    def test_pending_and_rejected_are_hidden_from_rag_and_world(self, q4_env):
        client = _client(q4_env)

        # Отклонить две темы — они не должны попасть в RAG и мир.
        for topic in (CANDIDATES[0], CANDIDATES[1]):
            item = _by_topic(client, topic)
            client.post(
                f"/api/candidates/{item['candidate_id']}/reject",
                json={"comment": "Не согласовано"},
            )

        loader = ExpansionLoader(knowledge_dir=q4_env.knowledge)
        loader.load()
        for topic in (CANDIDATES[0], CANDIDATES[1]):
            assert loader.get(topic.lower()) is None, f"REJECTED виден в RAG: {topic}"
        # Канон при этом виден.
        assert loader.get(CANON_TOPIC.lower()) is not None

        world = _world_result(q4_env.file, CANDIDATES + [CANON_TOPIC])
        world_prov.filter_extraction_result(world)
        kept = [item.name for item in world.items]
        for topic in (CANDIDATES[0], CANDIDATES[1]):
            assert topic not in kept, f"REJECTED попал в мир: {topic}"
        assert CANON_TOPIC in kept, "канон должен остаться в мире"

    def test_approved_is_not_canon(self, q4_env):
        client = _client(q4_env)
        item = _by_topic(client, CANDIDATES[0])
        client.post(
            f"/api/candidates/{item['candidate_id']}/approve",
            json={"comment": "Согласовано"},
        )

        body = json.loads(q4_env.file.read_text(encoding="utf-8"))
        record = body["items"][0]
        meta = record["_provenance_metadata"]
        assert meta["status"] == "APPROVED"
        assert meta["requires_author_review"] is False
        # APPROVED ≠ CANON: категория не меняется на AUTHOR_CANON.
        assert meta["provenance_category"] == "SYSTEM_INTERPRETATION"

    def test_record_gate_sees_approved_as_verified(self, q4_env):
        client = _client(q4_env)
        item = _by_topic(client, CANDIDATES[0])
        client.post(
            f"/api/candidates/{item['candidate_id']}/approve",
            json={"comment": "Согласовано"},
        )

        pending_record = {
            "_provenance_metadata": _meta("PENDING_REVIEW"),
        }
        approved_record = json.loads(q4_env.file.read_text(encoding="utf-8"))["items"][0]
        assert record_is_unverified(pending_record) is True
        assert record_is_unverified(approved_record) is False
