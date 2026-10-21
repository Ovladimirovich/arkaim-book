# -*- coding: utf-8 -*-
"""Option B — Knowledge → Dialogue context (t1): правило на примерах.

Условия владельца, проверяемые ДО подключения смешанного контекста к ответу:

1. В Dialogue попадает компактная проекция релевантных фактов, а не всё
   содержимое Knowledge Core (project_dialogue_facts: релевантность + лимиты).
2. Происхождение фактов не смешивается: каждая категория сохраняется как
   есть, апгрейда нет (HYPOTHESIS не становится каноном), в блоке для
   voice_prompt каждая строка несёт свою метку и правила атрибуции.
3. t1-сбор — чистая функция, сбой не роняет ответ; metadata-дельта
   переиспользует t1-контексты (Knowledge Core не считается дважды).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from core.services.knowledge_core_context import (  # noqa: E402
    attribution_category,
    build_dialogue_context,
    merge_knowledge_core,
    project_dialogue_facts,
    render_dialogue_facts_block,
)


def _claim(text: str, category: str = "AUTHOR_CANON", confidence: float = 1.0) -> dict:
    return {"text": text, "source_ref": "book:chunk_x", "provenance": {"category": category, "confidence": confidence}}


def _ctx(entity_id: str, name: str, book_claims: list[dict]) -> dict:
    return {"entity_id": entity_id, "entity_name": name, "book_claims": book_claims}


QUESTION = "Кто такой Велик?"
LAYER_TEXT = "Велик — вождь и учитель, он отправился в великое путешествие."


# ── Условие 1: проекция релевантна и компактна ──────────────────────────────


def test_projection_keeps_only_relevant_facts() -> None:
    """В проекцию попадают только claims, релевантные вопросу/слою."""
    contexts = [
        _ctx(
            "velik",
            "Велик",
            [
                _claim("Велик отправился в великое путешествие через степи."),
                _claim("Корабль плыл сквозь туманность и не видел берега."),
            ],
        )
    ]
    facts = project_dialogue_facts(contexts, question=QUESTION, layer_text=LAYER_TEXT)

    texts = [fact["text"] for fact in facts]
    assert any("Велик отправился" in text for text in texts), "релевантный факт потерялся"
    assert not any("Корабль плыл" in text for text in texts), "нерелевантный факт просочился в проекцию"


def test_projection_respects_max_facts_limit() -> None:
    """Лимит количества фактов соблюдается (не всё содержимое Core)."""
    claims = [_claim(f"Велик говорил о вещи номер {i} своему ученику.") for i in range(20)]
    facts = project_dialogue_facts([_ctx("velik", "Велик", claims)], question=QUESTION, layer_text=LAYER_TEXT, max_facts=3)
    assert len(facts) <= 3


def test_projection_respects_max_chars_limit() -> None:
    """Лимит символов соблюдается (кроме первого факта — порог не режет контекст в ноль)."""
    long_text = "Велик " * 400
    claims = [_claim(f"{long_text} номер {i}.") for i in range(5)]
    facts = project_dialogue_facts([_ctx("velik", "Велик", claims)], question=QUESTION, layer_text=LAYER_TEXT, max_chars=500)
    assert facts, "первый факт допускается даже при жёстком лимите"
    assert len(facts) < 5
    total = sum(len(fact["text"]) for fact in facts[1:])
    assert total <= 500


def test_projection_empty_without_contexts_or_stems() -> None:
    assert project_dialogue_facts([], question=QUESTION, layer_text=LAYER_TEXT) == []
    assert project_dialogue_facts([_ctx("x", "X", [_claim("Велик")])], question="", layer_text="") == []


# ── Условие 2: происхождение фактов не смешивается ──────────────────────────


def test_mixed_categories_survive_projection_unchanged() -> None:
    """Смешанные provenance-категории копируются в проекцию без изменений."""
    canon = {"category": "AUTHOR_CANON", "confidence": 1.0}
    hypothesis = {"category": "HYPOTHESIS", "confidence": 0.4}
    reconstruction = {"category": "RECONSTRUCTION", "confidence": 0.6}
    contexts = [
        _ctx(
            "velik",
            "Велик",
            [
                _claim("Велик учит путников мудрости.", "AUTHOR_CANON", 1.0),
                _claim("Возможно, Велик был основан на мифе о Велиусмусе.", "HYPOTHESIS", 0.4),
                _claim("Реконструкция облика Велика опирается на находки.", "RECONSTRUCTION", 0.6),
            ],
        )
    ]
    facts = project_dialogue_facts(contexts, question=QUESTION, layer_text=LAYER_TEXT)

    categories = sorted(attribution_category(fact["provenance"]) for fact in facts)
    assert categories == ["AUTHOR_CANON", "HYPOTHESIS", "RECONSTRUCTION"]
    # Provenance не мутирован и не «повышен»
    by_text = {fact["text"]: fact["provenance"] for fact in facts}
    assert by_text["Возможно, Велик был основан на мифе о Велиусмусе."] == hypothesis
    assert by_text["Велик учит путников мудрости."] == canon
    assert by_text["Реконструкция облика Велика опирается на находки."] == reconstruction


def test_render_block_keeps_per_fact_attribution_labels() -> None:
    """Каждая строка блока несёт свою метку; правило атрибуции присутствует."""
    contexts = [
        _ctx(
            "velik",
            "Велик",
            [
                _claim("Велик учит путников мудрости.", "AUTHOR_CANON"),
                _claim("Возможно, Велик был основан на мифе о Велиусмусе.", "HYPOTHESIS"),
                _claim("Реконструкция облика Велика опирается на находки.", "RECONSTRUCTION"),
            ],
        )
    ]
    facts = project_dialogue_facts(contexts, question=QUESTION, layer_text=LAYER_TEXT)
    block = render_dialogue_facts_block(facts)

    assert "- [канон книги] Велик учит" in block
    assert "- [гипотеза] Возможно, Велик был основан" in block
    assert "- [реконструкция] Реконструкция облика" in block
    # Правило атрибуции: запрет выдавать не-канон за канон + обозначение словами
    assert "не выдавай за канон книги" in block
    assert "«по гипотезе»" in block


def test_no_canon_upgrade_for_hypothesis_line() -> None:
    """Строка гипотезы не может быть помечена как канон."""
    facts = project_dialogue_facts(
        [_ctx("velik", "Велик", [_claim("Возможно, Велик был основан на мифе.", "HYPOTHESIS")])],
        question=QUESTION,
        layer_text=LAYER_TEXT,
    )
    block = render_dialogue_facts_block(facts)
    hypothesis_lines = [line for line in block.splitlines() if "Возможно, Велик был основан" in line]
    assert hypothesis_lines
    assert all("[гипотеза]" in line for line in hypothesis_lines)
    assert not any("[канон книги]" in line for line in hypothesis_lines)


def test_render_block_empty_when_no_facts() -> None:
    assert render_dialogue_facts_block([]) == ""


def test_attribution_category_handles_unknown_provenance() -> None:
    assert attribution_category(None) == "UNKNOWN"
    assert attribution_category("не dict") == "UNKNOWN"
    assert attribution_category({}) == "UNKNOWN"
    assert attribution_category({"category": "EXTERNAL_SOURCE"}) == "EXTERNAL_SOURCE"


# ── t1-сбор и metadata-дельта ───────────────────────────────────────────────


def test_build_dialogue_context_returns_payload_keys() -> None:
    """build_dialogue_context отдаёт contexts/facts/facts_block (t1-контракт)."""
    ctx = _ctx("velik", "Велик", [_claim("Велик учит путников мудрости.")])
    with (
        patch("core.services.related_entities.resolve_related_entities", return_value=[{"entity_id": "velik", "name": "Велик"}]),
        patch("core.services.knowledge_core_context.gather_knowledge_core_context", return_value=[ctx]),
    ):
        payload = build_dialogue_context(QUESTION, LAYER_TEXT)

    assert isinstance(payload, dict)
    assert payload["contexts"] == [ctx]
    assert len(payload["facts"]) == 1
    assert "Дополнительные материалы Knowledge Core" in payload["facts_block"]


def test_build_dialogue_context_returns_none_on_failure() -> None:
    """Сбой t1-сбора не роняет ответ: None, без исключения наружу."""
    with (
        patch("core.services.related_entities.resolve_related_entities", return_value=[{"entity_id": "velik"}]),
        patch("core.services.knowledge_core_context.gather_knowledge_core_context", side_effect=RuntimeError("card broken")),
    ):
        assert build_dialogue_context(QUESTION, LAYER_TEXT) is None


def test_merge_reuses_t1_contexts_and_collects_delta_only() -> None:
    """Сущности уже с t1 не пересчитываются; дельта собирается отдельно."""
    t1_ctx = _ctx("velik", "Велик", [_claim("Велик учит путников.")])
    delta_ctx = _ctx("kali_yuga", "Кали Юга", [_claim("Кали Юга приходит.")])
    related = [{"entity_id": "velik", "name": "Велик"}, {"entity_id": "kali_yuga", "name": "Кали Юга"}]

    calls: list[list[dict]] = []

    def _spy(entities: list[dict]) -> list[dict]:
        calls.append(entities)
        return [delta_ctx]

    with patch("core.services.knowledge_core_context.gather_knowledge_core_context", side_effect=_spy):
        merged = merge_knowledge_core([t1_ctx], related)

    # gather вызван ТОЛЬКО по дельте (kali_yuga), а не по всем сущностям
    assert len(calls) == 1
    assert [entity["entity_id"] for entity in calls[0]] == ["kali_yuga"]
    # Порядок — порядок related_entities; контексты не потеряны
    assert [context["entity_id"] for context in merged] == ["velik", "kali_yuga"]


def test_merge_without_t1_behaves_like_gather() -> None:
    """Пустой t1 → прежняя семантика: сбор по всех related в прежнем порядке."""
    ctx = _ctx("arkaim", "Аркаим", [_claim("Аркаим — городище.")])
    related = [{"entity_id": "arkaim", "name": "Аркаим"}]

    with patch("core.services.knowledge_core_context.gather_knowledge_core_context", return_value=[ctx]) as gather:
        merged = merge_knowledge_core([], related)

    assert merged == [ctx]
    assert gather.call_count == 1


def test_merge_with_empty_related_returns_empty_without_gather() -> None:
    with patch("core.services.knowledge_core_context.gather_knowledge_core_context") as gather:
        assert merge_knowledge_core([_ctx("velik", "Велик", [])], []) == []
    gather.assert_not_called()


# ── Интеграция /book/ask: внутренний канал не утекает наружу ────────────────


def test_ask_route_strips_internal_dialogue_context_key() -> None:
    """`_dialogue_context` снимается роутом до публичного payload и metadata."""
    from unittest.mock import AsyncMock, MagicMock

    from fastapi.testclient import TestClient

    import core.routes.book as book_module
    from core.adc_deps import get_keeper
    from core.main import app

    keeper_result = {
        "answer": "Велик — вождь и учитель.",
        "source": "pulse",
        "provenance": [],
        "_dialogue_context": [_ctx("velik", "Велик", [])],
    }
    spy_installed = book_module._resolve_related_entities

    def _empty_resolve(payload: dict) -> list:
        return []

    book_module._resolve_related_entities = _empty_resolve
    mock_keeper = MagicMock()
    mock_keeper.act = AsyncMock(return_value=keeper_result)
    app.dependency_overrides[get_keeper] = lambda: mock_keeper
    fake_store = MagicMock()
    fake_store.store_exchange = AsyncMock(return_value={"status": "ok"})
    try:
        with patch("memory.store.get_memory_store", return_value=fake_store):
            client = TestClient(app)
            response = client.post("/book/ask", json={"question": "Кто такой Велик?"})
    finally:
        book_module._resolve_related_entities = spy_installed
        app.dependency_overrides.pop(get_keeper, None)

    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    # Внутренний ключ снят: не виден клиенту и не попал в metadata-словарь
    assert "_dialogue_context" not in payload
    # Публичные ключи контракта на месте
    for key in ("answer", "related_entities", "knowledge_core", "canonical_events"):
        assert key in payload, f"field {key!r} missing"
    # t1-контекст передан в merge, но пустой related → knowledge_core = []
    assert payload["knowledge_core"] == []
