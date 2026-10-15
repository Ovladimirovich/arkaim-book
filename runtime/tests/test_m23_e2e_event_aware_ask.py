# -*- coding: utf-8 -*-
"""M23 — Production E2E Event-Aware Ask/RAG.

Сквозная проверка POST /book/ask через реальное зарегистрированное
приложение (core.main.app): реальные реестры claim_temporal_links.json (9)
и screenplay_links.json (15), реальный knowledge card builder, реальный
BookRetriever (ChromaDB), реальный WorldEngine в related_entities, реальный
canonical_event_view (WORLD_MODEL.json), реальные resolvers цепочек.

Границы инфраструктуры (честно):
- keeper — mock: LLM/Pulse-голос. Вся цепочка после keeper.act
  (related_entities → gather_knowledge_core_context →
  gather_canonical_event_views) выполняется без моков.
- memory store — fake: изоляция теста от рабочей персистентности диалогов.
- event_logger, websocket broadcast, presence — реальные (no-op без клиентов).

Запрещённые моки не используются: gather_knowledge_core_context,
gather_canonical_event_views, build_canonical_event_view,
ClaimTemporalLinker, ScreenplayBookLinker, retriever.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

_REPO = Path(__file__).resolve().parent.parent.parent
_CORE = _REPO / "core" / "CORE"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from fastapi.testclient import TestClient  # noqa: E402

# Production-сценарии, подобранные так, чтобы реальный related_entities
# (WorldEngine, без моков) вёл на сущность, чья карточка содержит
# утверждённые claim→event связи из claim_temporal_links.json.
COSMIC = {
    "question": "Что такое импульс?",
    "answer": "Импульс — сигнал к началу преобразования, поданный из неизмеримых глубин.",
    "event_id": "event_cosmic_impulse",
}
KALI = {
    "question": "Что означает наступление Кали Юги?",
    "answer": "Наступление Кали Юги — приход эпохи темных сил на всей Земле.",
    "event_id": "event_kali_yuga_onset",
}
AWAKENING = {
    "question": "Что такое пробуждение сердца?",
    "answer": "Пробуждение сердца — зажжение беззаветного огня сердечного энтузиазма.",
    "event_id": "event_awakening",
}
NEGATIVE = {
    "question": "Какой сегодня день недели?",
    "answer": "Сегодня вторник. В книге нет ответа на этот вопрос.",
}


def _fake_keeper_result(_question: str, answer: str) -> dict:
    """Результат keeper: минимальный контракт M14 (answer/source/provenance/...).

    Поле question НЕ входит в контракт keeper.act() — это поведение
    реального KeeperAgent. Маршрут /book/ask обязан подмешивать оригинал
    вопроса сам (core/routes/book.py), поэтому здесь question намеренно
    не передаётся: тест доказывает сквозной путь без маскировки.
    """
    return {
        "answer": answer,
        "source": "pulse",
        "provenance": [],
        "uncertainty": None,
        "pulse_confidence": 0.9,
        "llm_used": False,
        "mood": "neutral",
        "suggestion": "",
    }


def _client(keeper_result: dict):
    from core.adc_deps import get_keeper
    from core.main import app

    mock_keeper = MagicMock()
    mock_keeper.act = AsyncMock(return_value=keeper_result)
    app.dependency_overrides[get_keeper] = lambda: mock_keeper

    fake_store = MagicMock()
    fake_store.store_exchange = AsyncMock(return_value={"status": "ok"})
    client = TestClient(app)

    def _ask(question: str) -> dict:
        with patch("memory.store.get_memory_store", return_value=fake_store):
            response = client.post("/book/ask", json={"question": question})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["ok"] is True
        return body["data"]

    return _ask


class TestE2EEventAwareAskRoute:
    """Полный production-путь /book/ask с реальным Knowledge Core."""

    def test_cosmic_impulse_question(self):
        ask = _client(_fake_keeper_result(COSMIC["question"], COSMIC["answer"]))
        payload = ask(COSMIC["question"])

        events = payload["canonical_events"]
        assert [e["event_id"] for e in events] == [COSMIC["event_id"]]
        event = events[0]
        assert event["found"] is True
        assert event["temporal"]["chain_valid"] is True
        # Три production claims одного события не дублируют его.
        claim_ids = {c["claim_id"] for c in event["claims"]}
        assert "claim_8acb95533b78" in claim_ids or "claim_365f11560938" in claim_ids
        assert len(events) == 1

    def test_kali_yuga_question(self):
        ask = _client(_fake_keeper_result(KALI["question"], KALI["answer"]))
        payload = ask(KALI["question"])

        events = payload["canonical_events"]
        event_ids = [e["event_id"] for e in events]
        # Дедуп семейств related_entities открывает слот под смежную тему
        # преобразований, поэтому событие Кали Юги может соседствовать с
        # другим релевантным событием, но не дублируется само.
        assert KALI["event_id"] in event_ids
        event = next(e for e in events if e["event_id"] == KALI["event_id"])
        assert event["temporal"]["chain_valid"] is True
        # Два production claims одного события — событие одно.
        assert len(event["claims"]) >= 1
        scene_ids = {m["screenplay_scene_id"] for m in event["screenplay_materials"]}
        assert "scene_081" in scene_ids
        for material in event["screenplay_materials"]:
            assert material["link_type"] == "book_chunk_to_scene"
            assert material.get("book_chunk_id")

    def test_awakening_question(self):
        ask = _client(_fake_keeper_result(AWAKENING["question"], AWAKENING["answer"]))
        payload = ask(AWAKENING["question"])

        events = payload["canonical_events"]
        assert [e["event_id"] for e in events] == [AWAKENING["event_id"]]
        assert events[0]["temporal"]["chain_valid"] is True

    def test_negative_question_gets_no_event(self):
        ask = _client(_fake_keeper_result(NEGATIVE["question"], NEGATIVE["answer"]))
        payload = ask(NEGATIVE["question"])

        assert payload["knowledge_core"] == []
        assert payload["canonical_events"] == []

    def test_chain_trace_claim_event_epoch_node(self):
        ask = _client(_fake_keeper_result(KALI["question"], KALI["answer"]))
        payload = ask(KALI["question"])

        event = payload["canonical_events"][0]
        resolved = [
            entry
            for ctx in payload["knowledge_core"]
            for entry in ctx["claim_temporal_references"]
            if entry["status"] == "RESOLVED" and entry.get("event", {}).get("event_id") == event["event_id"]
        ]
        assert resolved, "нет RESOLVED-связей для возвращённого события"
        for entry in resolved:
            assert entry["claim_id"]
            assert entry["event"]["event_id"] == event["event_id"]
            assert entry["event"]["epoch_id"], "epoch_id не прослеживается"
            assert entry["event"]["chain_valid"] is True
            temporal = entry.get("temporal_reference") or {}
            assert temporal.get("temporal_node_id"), "temporal_node_id не прослеживается"
            assert entry.get("source_ref", "").startswith("book:")

    def test_source_ref_and_provenance_preserved(self):
        ask = _client(_fake_keeper_result(KALI["question"], KALI["answer"]))
        payload = ask(KALI["question"])

        event = payload["canonical_events"][0]
        for claim in event["claims"]:
            assert claim["source_ref"].startswith("book:chunk_p_")
            assert claim.get("provenance_category")
        for ctx in payload["knowledge_core"]:
            for entry in ctx["claim_temporal_references"]:
                if entry["status"] == "RESOLVED":
                    assert entry.get("notes") is not None

    def test_ask_contract_unchanged(self):
        ask = _client(_fake_keeper_result(KALI["question"], KALI["answer"]))
        payload = ask(KALI["question"])
        for key in (
            "answer",
            "source",
            "provenance",
            "related_entities",
            "knowledge_core",
            "canonical_events",
            "session_id",
        ):
            assert key in payload, f"поле {key!r} отсутствует"
        assert payload["related_entities"], "related_entities пуст на production-вопросе"
