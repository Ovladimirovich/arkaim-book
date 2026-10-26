# -*- coding: utf-8 -*-
"""EDM-RES Level 2 (Context Resolution) — детерминированные правила W1–W3.

Покрытие утверждённого дизайна (GATE A, docs/ENTITY_RESOLUTION_RULES_2026-10-25.md):

- **W1** ``extract_intent``: таблица intents §3, правила I1–I4
  (триггеры, приоритет I2, fallback I3, намерение из ВОПРОСА I4);
- **W2** ``select_bundle``: правила R1–R4 (тип, бандл N=4, порядок §4.1,
  explicit gap B2), fallback по каталогу-индексу (§5.4), era-special,
  context-only (кандидат без карточки), Tier-2 связи в бандле;
- **W3** ``filter_claims``: правила C1–C6 (факты / реконструкции /
  art-model / explicit unknown / скрытие unknown / card-реконструкция);
- **W4** ``approved_relations``: fail-closed обёртка кросскока.

Синтетические каталоги — полная детерминированность без реальных данных;
интеграционные тесты — на реальном каталоге ENTITY_MODEL.

Запуск (из runtime/):
  .venv\\Scripts\\python -m pytest tests/test_edm_context.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # runtime/
CORE_DIR = ROOT.parent / "core" / "CORE"
for _p in (str(CORE_DIR), str(ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import shared_config  # noqa: E402
from core.services import edm_context  # noqa: E402
from core.services import edm_pilot  # noqa: E402

REAL_EDM_DIR = CORE_DIR / "ENTITY_MODEL"


def _card(eid: str, etype: str, names=(), claims=None, is_reconstruction: bool = False) -> dict:
    identity = {"canonical_id": eid, "type": etype, "names": list(names)}
    if is_reconstruction:
        identity["is_reconstruction"] = True
    return {
        "identity": identity,
        "claims": claims if claims is not None else [],
        "constraints": {},
    }


def _catalog(*cards: dict) -> dict[str, dict]:
    return {c["identity"]["canonical_id"]: c for c in cards}


# ── W1. extract_intent (I1–I4) ─────────────────────────────────────────


def test_extract_intent_specific_triggers_i1():
    cases = {
        "where": "Где расположен Аркаим?",
        "appearance": "Как выглядело поселение Аркаим?",
        "clothing": "Что носили воины?",
        "climate": "Какая погода была в степи?",
        "language": "На каком языке говорили?",
        "character": "Кто такой Велик?",
        "culture": "Чему верили люди?",
        "era": "Когда это было?",
        "cause": "Почему случилось?",
        "about": "Расскажи про Аркаим",
    }
    for expected, question in cases.items():
        assert edm_context.extract_intent(question) == expected, question


def test_extract_intent_priority_i2():
    # where + cause → where (выше в INTENT_PRIORITY).
    assert edm_context.extract_intent("Где и почему это было?") == "where"
    # appearance + era → appearance (выше в приоритете).
    assert edm_context.extract_intent("Когда выглядело укрепление?") == "appearance"


def test_extract_intent_fallback_i3():
    # Ни одного триггера → about (финальный fallback).
    assert edm_context.extract_intent("Привет") == "about"
    assert edm_context.extract_intent("") == "about"
    assert edm_context.extract_intent("Аркаим") == "about"


def test_extract_intent_is_question_not_answer_i4():
    # I4: намерение определяется ВОПРОСОМ — функция детерминирована и
    # не принимает никаких других входов (только question).
    import inspect

    params = list(inspect.signature(edm_context.extract_intent).parameters)
    assert params == ["question"]


# ── W2. select_bundle (R1–R4, §4.1, §5.4) ─────────────────────────────


def test_select_bundle_resolved_single_r1():
    catalog = _catalog(_card("loc_a", "location"), _card("char_a", "character"))
    out = edm_context.select_bundle(
        "Где находился объект?",
        [{"entity_id": "loc_a", "origin": "engine", "entity_type": "geography"}],
        catalog=catalog,
    )
    assert out["status"] == "RESOLVED"
    assert out["entity_ids"] == ["loc_a"]
    assert out["dropped"] == []
    assert out["gap"] is None


def test_select_bundle_ambiguous_r2():
    catalog = _catalog(_card("loc_a", "location"), _card("loc_b", "location"))
    out = edm_context.select_bundle(
        "Расскажи про поселение",
        [
            {"entity_id": "loc_a", "origin": "pilot"},
            {"entity_id": "loc_b", "origin": "pilot"},
        ],
        catalog=catalog,
    )
    # about (R4) — бандл всех названных; два → AMBIGUOUS, выбор не делается.
    assert out["status"] == "AMBIGUOUS"
    assert out["entity_ids"] == ["loc_a", "loc_b"]


def test_select_bundle_type_filter_by_intent():
    catalog = _catalog(_card("char_a", "character"), _card("loc_a", "location"))
    out = edm_context.select_bundle(
        "Где находился объект?",
        [{"entity_id": "char_a", "origin": "engine", "entity_type": "character"}],
        catalog=catalog,
    )
    # Кандидат не входит в желательные типы where → из бандла выходит;
    # пустой пул → fallback по каталогу (location), а не «не той» сущности.
    assert "char_a" not in out["entity_ids"]
    assert out["entity_ids"] == ["loc_a"]


def test_select_bundle_gap_about_no_candidates_r3_b2():
    catalog = _catalog(_card("loc_a", "location"))
    out = edm_context.select_bundle("Расскажи про поселение", [], catalog=catalog)
    # R3/B2: без названных — explicit gap, «не той» сущности нет.
    assert out["status"] == "GAP"
    assert out["entity_ids"] == []
    assert out["gap"]
    assert out["relations"] == []  # B1: без бандла — без связей


def test_select_bundle_catalog_fallback_v1():
    catalog = _catalog(_card("loc_a", "location"), _card("char_a", "character"))
    out = edm_context.select_bundle("Где находился объект?", [], catalog=catalog)
    # §5.4: единственный представитель типа в каталоге → R1 single.
    assert out["status"] == "RESOLVED"
    assert out["entity_ids"] == ["loc_a"]


def test_select_bundle_about_no_fallback():
    # about/cause — только названные: fallback не применяется, GAP.
    catalog = _catalog(_card("loc_a", "location"))
    out = edm_context.select_bundle("Расскажи про поселение", [], catalog=catalog)
    assert out["status"] == "GAP"


def test_select_bundle_limit_n4_and_dropped():
    catalog = _catalog(*(_card(f"loc_{i}", "location") for i in range(6)))
    out = edm_context.select_bundle(
        "Расскажи про поселение",
        [{"entity_id": f"loc_{i}", "origin": "pilot"} for i in range(6)],
        catalog=catalog,
    )
    assert len(out["entity_ids"]) == 4
    assert out["dropped"] == ["loc_4", "loc_5"]


def test_select_bundle_ordering_41_ranks(monkeypatch):
    catalog = _catalog(_card("loc_a", "location"), _card("loc_b", "location"))
    monkeypatch.setattr(edm_context, "_approved_canonical_ids", lambda: {"loc_b"})
    out = edm_context.select_bundle(
        "Расскажи про поселение",
        [
            {"entity_id": "loc_a", "origin": "examples"},  # ранг c
            {"entity_id": "loc_b", "origin": "catalog"},  # ранг a (approved)
        ],
        catalog=catalog,
    )
    # §4.1: (a) approved → (b) engine/pilot → (c) examples → (e) id asc.
    assert out["entity_ids"] == ["loc_b", "loc_a"]


def test_select_bundle_explicit_ids_strict_directive():
    catalog = _catalog(_card("loc_a", "location"), _card("char_a", "character"))
    # Явные ids — strict-директива вызывающего: без type-фильтра.
    out = edm_context.select_bundle(
        "Где находился объект?",
        [],
        catalog=catalog,
        explicit_ids=["char_a", "loc_a"],
    )
    assert out["entity_ids"] == ["char_a", "loc_a"]


def test_select_bundle_era_special_rule(monkeypatch):
    # «Эпоха установлена» — только если у карточки time.epoch_ref.
    card_era = _card("era_a", "event")
    card_era["time"] = {"epoch_ref": "kali_yuga"}
    catalog = _catalog(card_era, _card("era_b", "event"))
    monkeypatch.setattr(edm_context, "_origin_of", lambda eid, c: "catalog")
    out = edm_context.select_bundle("Когда это было?", [], catalog=catalog)
    assert out["entity_ids"] == ["era_a"]
    out2 = edm_context.select_bundle("Когда это было?", [], catalog=_catalog(_card("era_b", "event")))
    assert out2["status"] == "GAP"  # без эпохи — явная граница знания


def test_select_bundle_context_only_engine_candidate():
    catalog = _catalog(_card("loc_a", "location"))
    out = edm_context.select_bundle(
        "Расскажи про поселение",
        [
            {"entity_id": "loc_a", "origin": "pilot"},
            {"entity_id": "engine_only", "origin": "engine", "entity_type": "geography"},
        ],
        catalog=catalog,
    )
    # §4.2: engine-кандидат без EDM-карточки — «контекст без карточки».
    assert out["context_only"] == ["engine_only"]
    assert "engine_only" in out["entity_ids"]


def test_select_bundle_tier2_relations_attached():
    out = edm_context.select_bundle(
        "Расскажи про Аркаим",
        [
            {"entity_id": "region_arkaim", "origin": "pilot"},
            {"entity_id": "steppe_climate", "origin": "pilot"},
        ],
        catalog=edm_pilot.get_entities(),
    )
    ids = {r.get("id") for r in out["relations"]}
    assert "rel_has_climate_region_arkaim_steppe" in ids
    for r in out["relations"]:
        assert r.get("owner_reviewed") is True  # B1: только утверждённые
        assert r.get("status") == "APPROVED"


# ── W3. filter_claims (C1–C6) ──────────────────────────────────────────


def _rich_card() -> dict:
    return {
        "identity": {"canonical_id": "probe", "type": "location", "names": ["Probe"]},
        "claims": [
            {"path": "place.coordinates", "value": {"lat": 1, "lng": 2}, "status": "known", "provenance_class": "canon"},
            {"path": "architecture.style", "value": "stone", "status": "known", "provenance_class": "external_source"},
            {"path": "architecture.materials", "value": ["brick"], "status": "reconstructed", "provenance_class": "reconstruction"},
            {"path": "place.landscape", "value": "steppe", "status": "known", "provenance_class": "ai_model_artistic", "medium": True},
            {"path": "environment.weather", "value": None, "status": "unknown", "provenance_class": "none"},
            {"path": "environment.season", "value": None, "status": "unknown", "provenance_class": "none"},
        ],
        "constraints": {"required_unknown": ["environment.weather"]},
    }


def test_filter_claims_c1_facts():
    out = edm_context.filter_claims(_rich_card())
    rules = {c["path"]: c["c_rule"] for c in out}
    assert rules["place.coordinates"] == "C1"
    assert rules["architecture.style"] == "C1"
    assert all(c["show"] == "fact" for c in out if c["c_rule"] == "C1")


def test_filter_claims_c1_unknown_provenance_class_not_fact():
    # known с НЕутверждённым provenance-классом — не факт (C1 fail-closed).
    card = _rich_card()
    card["claims"].append({"path": "place.region", "value": "steppe", "status": "known", "provenance_class": "ai_inferred"})
    out = edm_context.filter_claims(card)
    assert "place.region" not in {c["path"] for c in out}


def test_filter_claims_c2_reconstruction():
    out = edm_context.filter_claims(_rich_card())
    c = next(x for x in out if x["path"] == "architecture.materials")
    assert c["c_rule"] == "C2"
    assert c["show"] == "reconstruction"


def test_filter_claims_c3_art_model_dialogue_vs_visual():
    dialogue = edm_context.filter_claims(_rich_card(), mode="dialogue")
    visual = edm_context.filter_claims(_rich_card(), mode="visual")
    d = next(x for x in dialogue if x["path"] == "place.landscape")
    v = next(x for x in visual if x["path"] == "place.landscape")
    # C3/G10: art-model — никогда как факт книги; dialogue — «визуальный
    # образ (допущение)», visual — с явной меткой.
    assert d["c_rule"] == "C3" and d["show"] == "visual_image"
    assert v["c_rule"] == "C3" and v["show"] == "labeled_visual"


def test_filter_claims_c4_explicit_unknown_only_required():
    out = edm_context.filter_claims(_rich_card())
    rules = {c["path"]: c["c_rule"] for c in out}
    # C4: unknown В required_unknown — явная граница знания.
    assert rules.get("environment.weather") == "C4"
    # C5: unknown вне required_unknown — не показывается.
    assert "environment.season" not in rules


def test_filter_claims_c6_card_reconstruction_flag():
    card = _rich_card()
    card["identity"]["is_reconstruction"] = True
    out = edm_context.filter_claims(card)
    assert out
    assert all(c["card_reconstruction"] is True for c in out)
    plain = edm_context.filter_claims(_rich_card())
    assert all(c["card_reconstruction"] is False for c in plain)


def test_filter_claims_non_dict_claim_skipped():
    card = _rich_card()
    card["claims"].append("broken-string")  # повреждённая запись не роняет фильтр
    out = edm_context.filter_claims(card)
    assert all(isinstance(c, dict) for c in out)


# ── W4. approved_relations (fail-closed B1) ────────────────────────────


def test_approved_relations_owner_reviewed():
    rels = edm_context.approved_relations()
    assert isinstance(rels, list)
    for r in rels:
        assert r.get("status") == "APPROVED"
        assert r.get("owner_reviewed") is True
        for k in ("id", "source_id", "relation", "target_id"):
            assert r.get(k)


def test_approved_relations_fail_closed(monkeypatch):
    import narrative_engine.world_model as wm

    def _boom():
        raise RuntimeError("crosswalk down")

    monkeypatch.setattr(wm, "_load_approved_relations", _boom)
    assert edm_context.approved_relations() == []  # мир не выдумывается


def test_relations_cache_stable():
    assert edm_context.approved_relations() is edm_context.approved_relations()


# ── Интеграция: реальный каталог ENTITY_MODEL ──────────────────────────


def test_real_catalog_fallback_where(monkeypatch):
    monkeypatch.setattr(shared_config.settings, "EDM_RES_DIR", str(REAL_EDM_DIR), raising=False)
    edm_pilot._reset_cache()
    catalog = edm_pilot.get_entities()
    out = edm_context.select_bundle("Где находился Аркаим?", [], catalog=catalog)
    # где-интент + пустой пул → fallback по location-типам каталога.
    assert out["status"] in ("RESOLVED", "AMBIGUOUS")
    for eid in out["entity_ids"]:
        assert catalog[eid]["identity"].get("type") == "location"
    edm_pilot._reset_cache()


def test_real_catalog_era_fallback(monkeypatch):
    monkeypatch.setattr(shared_config.settings, "EDM_RES_DIR", str(REAL_EDM_DIR), raising=False)
    edm_pilot._reset_cache()
    catalog = edm_pilot.get_entities()
    out = edm_context.select_bundle("Когда это было?", [], catalog=catalog)
    # era: только карточки с time.epoch_ref (у остальных — явный unknown).
    for eid in out["entity_ids"]:
        assert catalog[eid].get("time", {}).get("epoch_ref")
    assert out["status"] in ("RESOLVED", "AMBIGUOUS")
    edm_pilot._reset_cache()
