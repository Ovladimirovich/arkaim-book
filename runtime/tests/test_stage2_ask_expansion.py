# -*- coding: utf-8 -*-
"""
Stage 2 targeted tests — Managed Knowledge Expansion.

Покрытие:
- AskGapDetector (классификация статуса);
- AskExpansionOrchestrator: entity resolution (stem-matching),
  relation safety, editorial gate (внешний источник не авто-принимается),
  end-to-end expand() с изолированным knowledge-каталогом;
- validate_candidate (content-term проверка).
"""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "core" / "CORE"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.services.ask_gap_detector import detect_gap  # noqa: E402
from core.services.ask_expansion_orchestrator import (  # noqa: E402
    expand,
    make_decision,
    resolve_relation,
    resolve_subject_entity,
    validate_candidate,
)


@pytest.fixture()
def isolated_knowledge(tmp_path, monkeypatch):
    """KNOWLEDGE_DIR, очередь предложений и граф BookOS — в tmp.

    enriched_chunks.json копируется в tmp KNOWLEDGE; ASK_EXPANSIONS.json
    пишется в tmp ASK_EXPANSIONS_DIR (runtime-пространство, не канон);
    граф — в tmp OS_DATA через подмену EntityStore/RelationshipStore/FactStore
    в knowledge_store.
    """
    import shared_config
    from config import config as core_config
    import book_os.entity_store as entity_store_mod
    import book_os.relationship_store as relationship_store_mod
    import book_os.fact_store as fact_store_mod

    tmp_knowledge = tmp_path / "KNOWLEDGE"
    tmp_knowledge.mkdir(parents=True)
    chunks_src = Path(core_config.KNOWLEDGE_DIR) / "enriched_chunks.json"
    if chunks_src.exists():
        (tmp_knowledge / "enriched_chunks.json").write_bytes(chunks_src.read_bytes())

    tmp_proposals = tmp_path / "ask_expansions"
    tmp_proposals.mkdir(parents=True)

    monkeypatch.setattr(shared_config.settings, "KNOWLEDGE_DIR", tmp_knowledge)
    monkeypatch.setattr(shared_config.settings, "ASK_EXPANSIONS_DIR", tmp_proposals)

    # knowledge_store импортирует стори внутри save(); направляем их в tmp OS_DATA.
    os_data = tmp_path / "OS_DATA"
    orig_entity, orig_rel, orig_fact = (
        entity_store_mod.EntityStore,
        relationship_store_mod.RelationshipStore,
        fact_store_mod.FactStore,
    )

    def _entity_store(*a, **kw):
        kw.pop("data_dir", None)
        return orig_entity(os_data, *a, **kw)

    def _rel_store(*a, **kw):
        kw.pop("data_dir", None)
        return orig_rel(os_data, *a, **kw)

    def _fact_store(*a, **kw):
        kw.pop("data_dir", None)
        return orig_fact(os_data, *a, **kw)

    monkeypatch.setattr(entity_store_mod, "EntityStore", _entity_store)
    monkeypatch.setattr(relationship_store_mod, "RelationshipStore", _rel_store)
    monkeypatch.setattr(fact_store_mod, "FactStore", _fact_store)
    return {"knowledge_dir": tmp_knowledge, "proposals_dir": tmp_proposals}


# ── AskGapDetector ─────────────────────────────────────────────────────


def test_detect_gap_missing_without_contexts() -> None:
    report = detect_gap(
        "Кто такой Небылица?",
        related_entities=[],
        existing_knowledge_core=[],
    )
    assert report.status == "MISSING"
    assert report.source_search_required


def test_detect_gap_partially_known_with_single_fact() -> None:
    report = detect_gap(
        "Кто такой Кали?",
        related_entities=[{"name": "Кали"}],
        existing_knowledge_core=[
            {
                "entity_id": "калы",
                "entity_name": "Кали",
                "book_claims": [{"text": "Кали правил городом.", "source_ref": "book:chunk:x"}],
            }
        ],
    )
    assert report.status == "PARTIALLY_KNOWN"
    assert report.evidence_available == 1


def test_detect_gap_known_with_three_facts() -> None:
    claims = [{"text": "c%d" % i, "source_ref": "book:chunk:%d" % i} for i in range(3)]
    report = detect_gap(
        "Кто такой Кали?",
        related_entities=[{"name": "Кали"}],
        existing_knowledge_core=[{"entity_id": "калы", "book_claims": claims}],
    )
    assert report.status == "KNOWN"
    assert not report.source_search_required


# ── Entity Resolution (stem-matching) ─────────────────────────────────


def test_resolve_subject_entity_stem_variant_matches_canonical() -> None:
    """'Гиперборея' (вопрос) ~ 'Гипербореи' (каноник) по 8-символьному стемену."""
    entity_id, method, flags = resolve_subject_entity("Гиперборея", [])
    assert entity_id == "гипербореи"
    assert method == "name_resolver"
    assert flags["known_alias"] is True
    assert not flags.get("unknown_entity")


def test_resolve_subject_entity_unknown_entity_flagged() -> None:
    entity_id, method, flags = resolve_subject_entity("Квэблз", [])
    assert entity_id == ""
    assert method == "none"
    assert flags.get("unknown_entity")


def test_resolve_subject_entity_world_model_priority() -> None:
    entities = [
        {"name": "Радомир", "entity_id": "wm_radomir"},
    ]
    entity_id, method, flags = resolve_subject_entity("Радомир", entities)
    assert entity_id == "wm_radomir"
    assert method == "world_model_match"


# ── Relation Safety (no invented fact) ────────────────────────────────


def test_neutral_marker_with_strong_predicate_unsupported() -> None:
    rel = resolve_relation("Велик находился рядом с Кали.", "participates_in")
    assert rel["supported"] is False
    assert rel["neutral_markers_only"] is True


def test_positive_marker_supports_strong_predicate() -> None:
    rel = resolve_relation("Велик принял участие в событиях.", "participates_in")
    assert rel["supported"] is True


# ── Editorial Gate ────────────────────────────────────────────────────


def _mk_validation(score: float, reasons: list, relation_supported: bool = True) -> dict:
    return {
        "validation_score": score,
        "reasons": reasons,
        "entity_id": "калы",
        "entity_method": "name_resolver",
        "entity_flags": {"canonical_name": "Кали", "known_alias": True, "aliases": []},
        "relation": {"supported": relation_supported},
        "conflict_with_knowledge_core": None,
    }


def test_external_source_never_auto_accepted() -> None:
    """Внешний источник с высоким score -> REVIEW, авто-принятие запрещено."""
    decision = make_decision(
        _mk_validation(0.9, []),
        {"subject": "Кали", "predicate": "mentioned_in", "priority": "EXTERNAL"},
    )
    assert decision.status == "REVIEW"
    assert "авто-принятие запрещено" in decision.reason


def test_relation_not_supported_blocks_accept() -> None:
    decision = make_decision(
        _mk_validation(0.8, ["relation_not_supported_by_evidence"], relation_supported=False),
        {"subject": "Кали", "predicate": "participates_in"},
    )
    assert decision.status == "REVIEW"


def test_conflict_with_knowledge_core_always_review() -> None:
    validation = _mk_validation(0.9, ["conflict_with_knowledge_core"])
    validation["conflict_with_knowledge_core"] = {"note": "x", "resolution": "UNRESOLVED"}
    decision = make_decision(validation, {"subject": "Кали", "predicate": "mentioned_in"})
    assert decision.status == "REVIEW"


def test_neutral_marker_with_weak_predicate_ok() -> None:
    rel = resolve_relation("Велик находился рядом с Кали.", "mentioned_in")
    assert rel["supported"] is True


# ── E2E expand() on real book chunks (isolated knowledge dir) ─────────


@pytest.mark.asyncio
async def test_expand_book_evidence_accepts_and_saves_idempotently(isolated_knowledge) -> None:
    r1 = await expand("Гиперборея", related_entities=[], knowledge_contexts=[])
    assert len(r1.accepted) >= 1, "книжные находки должны дать ACCEPT-кандидаты"
    assert not r1.review, "книжные находки не должны уходить на REVIEW без причины: %s" % [d.reason for d in r1.decisions]
    assert r1.gap_recheck["gap_closed"] is True

    # Provenance обязателен на каждом принятом кандидате.
    for claim in r1.accepted:
        prov = claim.provenance
        assert prov["source_ref"].startswith("book:chunk:"), prov["source_ref"]
        assert prov["priority"] == "BOOK"
        assert prov.get("validation"), "в каждом кандидате должна быть валидация"
        assert claim.evidence_fingerprint

    # Storage в очередь предложений (вне канона).
    out = isolated_knowledge["proposals_dir"] / "ASK_EXPANSIONS.json"
    assert out.exists()
    items = json.loads(out.read_text(encoding="utf-8"))
    assert len(items) == len(r1.accepted)

    # Idempotency: повторный запуск — 0 новых сохранений.
    r2 = await expand("Гиперборея", related_entities=[], knowledge_contexts=[])
    assert r2.storage["items_saved"] == 0
    assert r2.storage["items_skipped"] == len(r2.accepted)
    assert len(json.loads(out.read_text(encoding="utf-8"))) == len(items)


@pytest.mark.asyncio
async def test_expand_mixed_question_only_book_evidence_accepted(isolated_knowledge) -> None:
    """'Гиперборея и Атлантида': принимается только то, что реально в книге."""
    r = await expand("Гиперборея и Атлантида", related_entities=[], knowledge_contexts=[])
    accepted_subjects = {c.subject.lower() for c in r.accepted}
    assert "атлантида" not in accepted_subjects, "нет доказательств по Атлантиде в книге — она не принимается"
    assert "гиперборея" in accepted_subjects


@pytest.mark.asyncio
async def test_expand_external_only_candidates_reviewed(isolated_knowledge, monkeypatch) -> None:
    """Вопрос без книжных доказательств: внешние кандидаты только на REVIEW."""
    import core.services.ask_expansion_orchestrator as orch

    async def _fake_book_sources(terms, limit=8):
        return []

    monkeypatch.setattr(orch, "search_book_sources", _fake_book_sources)
    fake_external = [
        {
            "kind": "external",
            "priority": "EXTERNAL",
            "score": 0.7,
            "source_ref": "external:academic",
            "title": "Философские исследования: Фронтик",
            "snippet": "Фронтик упоминается в академическом контексте.",
        }
    ]
    monkeypatch.setattr(
        orch,
        "search_external_sources",
        lambda q, entity_type="concept": fake_external,
    )

    r = await expand("Фронтик", related_entities=[], knowledge_contexts=[])
    assert r.accepted == [], "внешний источник никогда не авто-принимается"
    assert len(r.review) == 1
    assert r.review[0].source == "external:academic"
    assert r.storage == {}
    assert not r.gap_recheck["gap_closed"]


@pytest.mark.asyncio
async def test_expand_known_question_skips_expansion(isolated_knowledge) -> None:
    """Если Knowledge Core уже знает (3+ фактов) — расширение не запускается."""
    claims = [{"text": "c%d" % i, "source_ref": "book:chunk:%d" % i} for i in range(3)]
    contexts = [{"entity_id": "калы", "entity_name": "Кали", "book_claims": claims}]
    r = await expand(
        "Кали",
        related_entities=[{"name": "Кали", "entity_id": "калы"}],
        knowledge_contexts=contexts,
    )
    assert r.summary
    assert r.accepted == []
    assert r.storage == {}


# ── validate_candidate: content-term validation ───────────────────────


def test_validate_subject_evidenced_by_stem_variant() -> None:
    """Стемен 'гиперборея' находит 'Гипербореи' в evidence."""
    cand = {
        "subject": "гиперборея",
        "predicate": "mentioned_in",
        "evidence": "Он прожил на землях Гипербореи, пережив безысходность.",
        "source_ref": "book:chunk:xyz",
        "priority": "BOOK",
    }
    v = validate_candidate(cand, [], [])
    assert "subject_not_evidenced_in_source" not in v["reasons"], v["reasons"]


def test_validate_subject_not_in_evidence_penalized() -> None:
    cand = {
        "subject": "фронтик",
        "predicate": "mentioned_in",
        "evidence": "Она сказала что-то о судьбе.",
        "source_ref": "external:academic",
        "priority": "EXTERNAL",
    }
    v = validate_candidate(cand, [], [])
    assert "unknown_entity" in v["reasons"]
    assert v["validation_score"] < 0.8


# ── /book/ask integration ─────────────────────────────────────────────


def _make_ask_client() -> tuple:
    """TestClient с mock keeper/memory (как test_book_ask_question_propagation)."""
    from fastapi.testclient import TestClient
    from unittest.mock import AsyncMock, MagicMock

    import core.routes.book as book_module
    from core.adc_deps import get_keeper
    from core.main import app

    mock_keeper = MagicMock()
    mock_keeper.act = AsyncMock(return_value={"answer": "test", "source": "pulse", "llm_used": False})
    app.dependency_overrides[get_keeper] = lambda: mock_keeper
    fake_store = MagicMock()
    fake_store.store_exchange = AsyncMock(return_value={"status": "ok"})
    client = TestClient(app)
    return client, book_module, fake_store, app


@pytest.fixture()
def stage2_on(monkeypatch):
    """Включить Stage 2 (OWNER-GATE) на время теста."""
    import shared_config

    monkeypatch.setattr(shared_config.settings, "STAGE2_ENABLED", True)
    return True


def test_book_ask_known_status_does_not_expand(stage2_on) -> None:

    client, book_module, fake_store, app = _make_ask_client()

    def _fake_detect_gap(question, **kw):
        class _R:
            status = "KNOWN"
            source_search_required = False

        return _R()

    with (
        patch("core.services.ask_gap_detector.detect_gap", _fake_detect_gap),
        patch("core.services.ask_expansion_orchestrator.expand", MagicMock()) as p,
        patch("memory.store.get_memory_store", return_value=fake_store),
    ):
        response = client.post("/book/ask", json={"question": "Кали"})
    data = response.json().get("data", {})
    assert data.get("knowledge_expansion", {}).get("gap_status") == "KNOWN"
    assert not p.called, "expand must not be called when KNOWN"


def test_book_ask_missing_status_triggers_expansion(stage2_on) -> None:
    from core.services.ask_expansion_orchestrator import ExpansionResult, CandidateClaim

    client, book_module, fake_store, app = _make_ask_client()

    question = "Гиперборея"
    expansion_result = ExpansionResult(question=question)
    claim = CandidateClaim(
        subject="гиперборея",
        predicate="mentioned_in",
        object="book:chunk:test",
        source="book:chunk:test",
        evidence="Он прожил на землях Гипербореи.",
        provenance={"source_ref": "book:chunk:test", "priority": "BOOK"},
        temporal_context={},
        confidence=0.8,
        evidence_fingerprint="abc123",
    )
    expansion_result.accepted.append(claim)
    expansion_result.gap_recheck = {"gap_closed": True}

    def _fake_detect_gap(q, **kw):
        class _R:
            status = "MISSING"
            source_search_required = True

        return _R()

    with (
        patch("core.services.ask_gap_detector.detect_gap", _fake_detect_gap),
        patch(
            "core.services.ask_expansion_orchestrator.expand",
            AsyncMock(return_value=expansion_result),
        ) as expand_spy,
        patch("memory.store.get_memory_store", return_value=fake_store),
    ):
        response = client.post("/book/ask", json={"question": question})
    data = response.json().get("data", {})
    ke = data.get("knowledge_expansion", {})
    assert ke.get("gap_status") == "MISSING"
    assert ke.get("accepted") == 1
    assert ke.get("gap_closed") is True
    expand_spy.assert_called_once()


# ── OWNER-GATE: Stage 2 выключен по умолчанию ───────────────────────────


def test_book_ask_contract_unchanged_when_stage2_disabled(monkeypatch) -> None:
    """Пока STAGE2_ENABLED выключен, публичный контракт /book/ask не меняется."""
    import shared_config

    monkeypatch.setattr(shared_config.settings, "STAGE2_ENABLED", False)

    client, book_module, fake_store, app = _make_ask_client()

    with (
        patch("core.services.ask_gap_detector.detect_gap", MagicMock()) as gap_spy,
        patch("core.services.ask_expansion_orchestrator.expand", MagicMock()) as expand_spy,
        patch("memory.store.get_memory_store", return_value=fake_store),
    ):
        response = client.post("/book/ask", json={"question": "Гиперборея"})

    assert response.status_code == 200, response.text
    data = response.json().get("data", {})
    assert "knowledge_expansion" not in data, "выключенный Stage 2 не меняет контракт ответа"
    assert not gap_spy.called, "gap-детектор не запускается при выключенном Stage 2"
    assert not expand_spy.called, "расширение не запускается при выключенном Stage 2"


def test_stage2_disabled_by_default(monkeypatch) -> None:
    """Флаг по умолчанию выключен (в shared_config — STAGE2_ENABLED=false)."""
    import shared_config

    assert getattr(shared_config.settings, "STAGE2_ENABLED", False) is False


@pytest.mark.asyncio
async def test_expand_writes_proposal_queue_not_canon(isolated_knowledge) -> None:
    """Stage 2 пишет предложения в runtime-пространство, а не в core/KNOWLEDGE."""
    from config import config as core_config

    r = await expand("Гиперборея", related_entities=[], knowledge_contexts=[])
    assert r.accepted, "должен быть хотя бы один принятый кандидат по книге"

    proposals = isolated_knowledge["proposals_dir"] / "ASK_EXPANSIONS.json"
    assert proposals.exists(), "очередь предложений создана"
    saved = json.loads(proposals.read_text(encoding="utf-8"))
    assert isinstance(saved, list) and saved, "предложения — плоский список"

    canon = Path(core_config.KNOWLEDGE_DIR) / "ASK_EXPANSIONS.json"
    assert not canon.exists(), "Stage 2 не пишет в каноническую папку core/KNOWLEDGE"
