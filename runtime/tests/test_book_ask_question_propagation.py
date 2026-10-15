# -*- coding: utf-8 -*-
"""Контроль, что /book/ask передаёт оригинал вопроса в related_entities.

Контракт keeper.act() не возвращает поле question — это поведение
реального KeeperAgent. Без явного подмешивания оригинала вопроса тематическое
отношение теряется: краткий Pulse-ответ, в котором отсутствует часть тем
вопроса, приводит к тому, что эти темы не попадают в related_entities и не
доходят до Knowledge Core.

Тест фиксирует, что маршрут /book/ask подмешивает оригинал вопроса
(авторитетный источник тем) ДО вызова resolve_related_entities, не изменяя
при этом контракт ответа (вопрос не утекает наружу).

Резолвер заменяется шпионом, чтобы не зависеть от состояния реального
WorldEngine/кэша: проверяется именно АРГУМЕНТ, который маршрут передаёт.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


class _QuestionSpy:
    """Заменяет core.routes.book._resolve_related_entities: фиксирует аргумент."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def __call__(self, payload: dict) -> list:
        self.calls.append(payload)
        return []


def _fake_keeper_result_no_question(answer: str) -> dict:
    """Минимальный контракт реального keeper: question не возвращается."""
    return {
        "answer": answer,
        "source": "pulse",
        "provenance": [],
        "llm_used": False,
    }


def _make_ask(keeper_result: dict, spy: _QuestionSpy):
    from fastapi.testclient import TestClient

    import core.routes.book as book_module
    from core.adc_deps import get_keeper
    from core.main import app

    spy_installed = book_module._resolve_related_entities
    book_module._resolve_related_entities = spy
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

    def _cleanup() -> None:
        book_module._resolve_related_entities = spy_installed
        app.dependency_overrides.pop(get_keeper, None)

    return _ask, _cleanup


def test_ask_passes_original_question_to_related_entities() -> None:
    spy = _QuestionSpy()
    question = "Как пробуждение сознания связано с путешествием Велика и Кали Югой?"
    brief_answer = "Духовное пробуждение — путь к осознанию."
    ask, cleanup = _make_ask(_fake_keeper_result_no_question(brief_answer), spy)
    try:
        payload = ask(question)
    finally:
        cleanup()

    assert spy.calls, "resolve_related_entities не вызывался"
    passed = spy.calls[0]
    # Весь оригинал вопроса (все его темы) передаётся в скоринг
    assert passed.get("question") == question, "оригинал вопроса не передаётся в related_entities"
    # Остальные поля приходят от keeper без искажений
    assert passed.get("answer") == brief_answer
    assert passed.get("source") == "pulse"
    # Контракт ответа не изменён: вопрос наружу не утекает
    assert "question" not in payload


def test_question_injection_preserves_answer_fields() -> None:
    spy = _QuestionSpy()
    question = "Что означает импульс?"
    ask, cleanup = _make_ask(_fake_keeper_result_no_question("Импульс — сигнал преобразования."), spy)
    try:
        payload = ask(question)
    finally:
        cleanup()

    assert spy.calls[0].get("question") == question
    assert payload["answer"] == "Импульс — сигнал преобразования."
    assert payload["related_entities"] == []
