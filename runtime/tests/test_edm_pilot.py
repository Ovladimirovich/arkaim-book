# -*- coding: utf-8 -*-
"""EDM pilot tests: extended_world -> EDM migration with reverse comparison.

Owner-approved pilot (25.10.2026): 5 real extended_world entities migrated to EDM,
then verified round-trip: nothing lost, provenance preserved, relations preserved,
temporal preserved, UNKNOWN not turned into values, RECONSTRUCTION not turned into CANON.
Projections: dialogue + MediaPlan generated from the same model.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EDM_DIR = ROOT / "core" / "CORE" / "ENTITY_MODEL"
PILOT_DIR = EDM_DIR / "pilot"
EXT_MODEL_DIR = ROOT / "core" / "CORE" / "WORLD_MODEL"


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, EDM_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


val = _load_module("edm_pilot_val", "entity_model_validate.py")
loader = _load_module("edm_pilot_loader", "loader.py")
projections = _load_module("edm_pilot_proj", "projections.py")


@pytest.fixture(scope="module")
def schema() -> dict:
    return val.load_schema()


@pytest.fixture(scope="module")
def pilot_entities() -> dict[str, dict]:
    """Loaded pilot EDM entities (the generated artifacts)."""
    entities = {}
    for p in sorted(PILOT_DIR.glob("*.json")):
        entities[p.stem] = json.loads(p.read_bytes().decode("utf-8-sig"))
    return entities


def _load_ext_card(category: str, card_id: str) -> dict:
    raw = loader.card_file(category).read_bytes().decode("utf-8-sig")
    data = json.loads(raw)
    cards = data if isinstance(data, list) else data.get(category, [])
    for card in cards:
        if card.get("id") == card_id:
            return card
    raise KeyError(f"{category}:{card_id}")


def _claim(entity: dict, path: str) -> dict:
    for c in entity["claims"]:
        if c["path"] == path:
            return c
    raise KeyError(path)


def _fmt(value) -> str:
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if isinstance(value, dict):
        return ", ".join(f"{k}={v}" for k, v in value.items())
    return str(value)


# ---------------------------------------------------------------------------
# 1. All pilot entities pass the validator (schema + semantics)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "name",
    ["region_arkaim", "steppe_climate", "arkaim_settlement", "civ_hyperborea", "civ_arkaim_civilization"],
)
def test_pilot_entities_validate(pilot_entities, schema, name):
    assert val.validate_entity(pilot_entities[name], schema) == []


# ---------------------------------------------------------------------------
# 2. Round-trip losslessness: every card property accounted for
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "card_name,category,card_id",
    [
        # Original E1 pilot (5 entities)
        ("region_arkaim", "geography", "region_arkaim"),
        ("steppe_climate", "climate", "steppe_climate"),
        ("arkaim_settlement", "architecture", "arkaim_settlement"),
        ("civ_hyperborea", "civilizations", "civ_hyperborea"),
        ("civ_arkaim_civilization", "civilizations", "civ_arkaim_civilization"),
        # E4 bulk migration (12 categories) - using card IDs that exist in
        # both the pilot entities and the WORLD_MODEL JSON files.
        ("communal_living", "daily_life", "communal_living"),
        ("agricultural_life", "daily_life", "agricultural_life"),
        ("lang_предыстория_человечества", "language", "lang_предыстория_человечества"),
        ("myth_гиперборея", "mythology", "myth_гиперборея"),
        ("myth_аркаим", "mythology", "myth_аркаим"),
        ("phil_предыстория_человечества", "philosophy", "phil_предыстория_человечества"),
        ("ritual_герметизм", "religion", "ritual_герметизм"),
        # rituals: та же карточка, что и в religion (дубль категории) — артефакт
        # один, поэтому сверяем с победившей проекцией religion (см. тест
        # test_duplicate_projection_kept_once_without_loss ниже).
        ("ritual_пифагорейство", "religion", "ritual_пифагорейство"),
        ("role_main", "social_structure", "role_main"),
        ("horse_travel", "transport", "horse_travel"),
        ("river_boats", "transport", "river_boats"),
    ],
)
def test_roundtrip_every_property_accounted(pilot_entities, card_name, category, card_id):
    card = _load_ext_card(category, card_id)
    entity = pilot_entities[card_name]
    rt_map = entity["pilot"]["roundtrip_map"]["properties"]
    # every card property has an explicit destination
    assert set(rt_map.keys()) == set((card.get("properties") or {}).keys())
    # claim-mapped properties carry the exact source value (no silent edits)
    claims_by_path = {c["path"]: c for c in entity["claims"]}
    for prop, mapping in rt_map.items():
        if mapping.startswith("claim:"):
            target = mapping.split(":", 1)[1]
            assert claims_by_path[target]["value"] == card["properties"][prop], f"{prop} value mangled"


def test_no_silent_property_loss_regression():
    """If a property ever has no destination, build_pilot_entities must flag it."""
    entities, reports = loader.build_pilot_entities()
    # Check all entities for property loss - not just the original 5
    for report in reports:
        assert report["issues"] == [], f"{report['card_id']}: {report['issues']}"
        assert report["relationships_ok"], f"{report['card_id']}: relationships not preserved"


def test_duplicate_projection_kept_once_without_loss():
    """Дубль категории (religion/rituals) не «побеждает последним» и не теряется.

    RELIGION.json и RITUALS.json — две проекции одного источника, card_id у них
    совпадает, а артефакт pilot/ именуется по card_id. Поэтому:
    - у каждой исходной карточки ровно одна запись в отчёте (ничего не исчезло);
    - ровно одна проекция каждой пары попадает в pilot/ (status="migrated"),
      вторая честно помечена status="duplicate_skipped" + duplicate_of;
    - победитель не беднее проигравшего, иначе дедупликация теряет знание.
    """
    entities, reports = loader.build_pilot_entities()
    # каждая карточка источника учтена ровно один раз
    keys = [(r["category"], r["card_id"]) for r in reports]
    assert len(keys) == len(set(keys)), "one report per source card, no duplicates"
    skipped = [r for r in reports if r.get("status") == "duplicate_skipped"]
    assert skipped, "religion/rituals projections must be deduplicated"
    assert len(entities) == len(reports) - len(skipped)
    # card_id уникален: имя артефакта = card_id, иначе файлы перезаписывают друг друга
    artifact_ids = [e["pilot"]["card_id"] for e in entities]
    assert len(artifact_ids) == len(set(artifact_ids))
    by_id = {e["pilot"]["card_id"]: e for e in entities}
    for report in skipped:
        assert report["issues"] == [], report["issues"]
        assert report["relationships_ok"], report["card_id"]
        winner_cat, _, winner_id = report["duplicate_of"].partition(":")
        assert winner_id == report["card_id"]
        assert winner_cat != report["category"], "skipped report must point at the other projection"
        winner = _load_ext_card(winner_cat, winner_id)
        loser = _load_ext_card(report["category"], report["card_id"])
        assert loader._projection_weight(winner) >= loader._projection_weight(loser)
        assert set((loser.get("properties") or {})) <= set((winner.get("properties") or {}))
        assert (loser.get("relationships") or []) == (winner.get("relationships") or [])
        kept = by_id[report["card_id"]]["pilot"]
        assert kept["source_card_file"].endswith(f"{winner_cat}.json"), kept["source_card_file"]


# ---------------------------------------------------------------------------
# 3. Provenance discipline: nothing became CANON that is not canon
# ---------------------------------------------------------------------------
def test_canon_stays_canon(pilot_entities):
    """civ_hyperborea is CANON/AUTHOR_CANON -> author_canon, NOT medium, NOT reconstruction."""
    for c in pilot_entities["civ_hyperborea"]["claims"]:
        assert c["provenance_class"] == "author_canon"
        assert c.get("medium", False) is False
        assert c["status"] == "known"


def test_reconstruction_stays_reconstruction(pilot_entities):
    """civ_arkaim_civilization is RECONSTRUCTION -> reconstructed + medium=true (G10)."""
    for c in pilot_entities["civ_arkaim_civilization"]["claims"]:
        assert c["provenance_class"] == "reconstruction"
        assert c.get("medium", False) is True, "reconstruction must be medium (artistic assumption)"
        assert c["status"] == "reconstructed"


def test_external_stays_external(pilot_entities):
    """External/HISTORICAL cards -> external_source, never author_canon."""
    for name in ("region_arkaim", "steppe_climate", "arkaim_settlement"):
        for c in pilot_entities[name]["claims"]:
            if c["status"] != "unknown":  # unknown boundary claims carry provenance_class=none
                assert c["provenance_class"] == "external_source", f"{name}: {c['path']}"


def test_generated_relations_are_derived_not_canon(pilot_entities):
    for name in ("steppe_climate", "arkaim_settlement", "civ_arkaim_civilization"):
        for rel in pilot_entities[name]["relations"]:
            assert rel["provenance_class"] == "derived", f"{name}: relation {rel['type']} must be derived"
            assert "generated during pilot" in rel.get("note", ""), "generated relations must be labelled as non-canon"


# ---------------------------------------------------------------------------
# 4. UNKNOWN not turned into values (fail-open guard)
# ---------------------------------------------------------------------------
def test_location_weather_season_are_unknown(pilot_entities):
    entity = pilot_entities["region_arkaim"]
    for path in ("environment.weather", "environment.season"):
        c = _claim(entity, path)
        assert c["status"] == "unknown"
        assert c["value"] is None, f"{path} must be null, got {c['value']!r}"
        assert c["provenance_class"] == "none"
    assert "environment.weather" in entity["constraints"]["required_unknown"]
    assert "environment.season" in entity["constraints"]["required_unknown"]


def test_unknown_not_materialized_in_mediaplan(pilot_entities):
    fragment = projections.to_mediaplan_fragment(pilot_entities["region_arkaim"])
    assert fragment["structured_prompt"]["environment"]["weather"] == "UNKNOWN"
    assert fragment["structured_prompt"]["environment"]["season"] == "UNKNOWN"
    dumped = json.dumps(fragment, ensure_ascii=False).lower()
    assert "clear" not in dumped
    assert "late summer" not in dumped
    assert "environment.weather" in fragment["unknown_fields"]


def test_unknown_not_materialized_in_dialogue(pilot_entities):
    sentence = projections.to_dialogue_sentence(pilot_entities["region_arkaim"])
    assert "не установлено" in sentence
    assert "clear" not in sentence.lower()


# ---------------------------------------------------------------------------
# 5. Temporal preserved
# ---------------------------------------------------------------------------
def test_temporal_preserved(pilot_entities):
    """If the card carried era/epoch, the time block must carry it; if not, it stays empty (not invented)."""
    expected = {
        "region_arkaim": ["~4000-3700 до н.э."],
        "steppe_climate": [],
        "arkaim_settlement": ["Bronze Age, 3500 BC"],
        "civ_hyperborea": ["~7000-3000 до н.э."],
        "civ_arkaim_civilization": ["~4000-2000 до н.э."],
    }
    pairs = [
        ("region_arkaim", "geography", "region_arkaim"),
        ("steppe_climate", "climate", "steppe_climate"),
        ("arkaim_settlement", "architecture", "arkaim_settlement"),
        ("civ_hyperborea", "civilizations", "civ_hyperborea"),
        ("civ_arkaim_civilization", "civilizations", "civ_arkaim_civilization"),
    ]
    for name, category, card_id in pairs:
        card = _load_ext_card(category, card_id)
        card_time = [str(v) for p, v in (card.get("properties") or {}).items() if p in loader.TIME_PROPS]
        time_block = pilot_entities[name].get("time") or {}
        assert time_block.get("epoch_ref") == card_time == expected[name], f"{name}: temporal mismatch"


# ---------------------------------------------------------------------------
# 6. Relations preserved
# ---------------------------------------------------------------------------
def test_card_relationships_preserved_verbatim():
    """Pilot cards carry relationships=[]; migration must not invent card-level relations."""
    entities, _ = loader.build_pilot_entities()
    for category, card_id, _gen in loader.PILOT_ENTITIES:
        card = _load_ext_card(category, card_id)
        card_rels = card.get("relationships") or []
        entity = next(e for e in entities if e["pilot"]["card_id"] == card_id)
        assert entity["relations"][: len(card_rels)] == card_rels


def test_generated_relations_are_usable(pilot_entities):
    """A consumer can ask 'which climate applies to region_arkaim' via relations."""
    targets = {r["target"] for r in pilot_entities["steppe_climate"]["relations"] if r["type"] == "climate_of"}
    assert "region_arkaim" in targets
    settlement_targets = {r["target"] for r in pilot_entities["arkaim_settlement"]["relations"] if r["type"] == "located_in"}
    assert "region_arkaim" in settlement_targets


# ---------------------------------------------------------------------------
# 7. Projections: dialogue + mediaplan from the same model
# ---------------------------------------------------------------------------
def test_dialogue_does_not_assert_reconstruction_as_fact(pilot_entities):
    entity = pilot_entities["civ_arkaim_civilization"]
    sentence = projections.to_dialogue_sentence(entity)
    # reconstruction claims are medium=true: their values must appear ONLY with the
    # explicit label, never as plain facts; plain_facts must not contain them
    label = "(реконструкция, художественное допущение)"
    plain = projections.plain_facts(entity)
    for c in entity["claims"]:
        if c.get("medium") and c.get("status") in {"reconstructed", "hypothesis"}:
            value_text = _fmt(c["value"])
            if not value_text:
                continue
            assert value_text not in plain, f"reconstructed value {value_text!r} leaked into plain dialogue facts"
            assert f"{value_text} {label}" in sentence, f"reconstructed value {value_text!r} must carry the label in dialogue"


def test_mediaplan_labels_medium_facts(pilot_entities):
    fragment = projections.to_mediaplan_fragment(pilot_entities["civ_arkaim_civilization"])
    medium_paths = [p["path"] for p in fragment["provenance"] if p["medium"]]
    assert medium_paths, "medium facts must be flagged in mediaplan provenance"
    structured = json.dumps(fragment["structured_prompt"], ensure_ascii=False)
    assert "(MEDIUM)" in structured, "reconstructed values must carry the (MEDIUM) label in mediaplan"


def test_mediaplan_temporal_context(pilot_entities):
    fragment = projections.to_mediaplan_fragment(pilot_entities["civ_hyperborea"])
    assert fragment["temporal_context"]["epoch_ref"] == ["~7000-3000 до н.э."]


# ---------------------------------------------------------------------------
# 8. E1 (фаза 4 плана): native (owner-authored) cards — schema + fail-closed
# ---------------------------------------------------------------------------
NATIVE_NAMES = ["svetovit", "location_temple", "person_velik"]


@pytest.mark.parametrize("name", NATIVE_NAMES)
def test_native_cards_validate(pilot_entities, schema, name):
    """Native cards must pass the full schema + semantic contract."""
    assert val.validate_entity(pilot_entities[name], schema) == []


def test_native_cards_structural_report():
    """Loader registry: every native card loads, structural reports are clean."""
    entities, nreports = loader.collect_native_entities()
    assert [r["card_id"] for r in nreports] == loader.NATIVE_CARDS
    assert len(entities) == len(loader.NATIVE_CARDS)
    for r in nreports:
        assert r["category"] == "native"
        assert r["issues"] == [], f"{r['card_id']}: {r['issues']}"


def test_native_fail_closed_unverified_draft_not_materialized(pilot_entities):
    """Unverified draft values must not survive as fact claims or relations."""
    forbidden = [
        "chief_priest",
        "9th_century",
        "915",
        "arheim",
        "holy_lands",
        "river_sun_wheel",
        "circular",
        "concentric",
        "stone_earth",
        "150_people",
        "east_west",
    ]
    for name in NATIVE_NAMES:
        entity = pilot_entities[name]
        fact_claims = [c for c in entity["claims"] if c["status"] not in {"unknown", "not_applicable"}]
        facts_text = json.dumps(fact_claims, ensure_ascii=False)
        relations_text = json.dumps(entity.get("relations") or [], ensure_ascii=False)
        for bad in forbidden:
            assert bad not in facts_text, f"{name}: draft value {bad!r} materialized as a fact claim"
            assert bad not in relations_text, f"{name}: draft value {bad!r} materialized as a relation"
        for c in fact_claims:
            assert c.get("source_ref"), f"{name}: fact claim {c['path']} without source_ref"


def test_native_owner_confirmed_claims(pilot_entities):
    """Решение владельца 2026-10-26: в утверждённых карточках known только то, что подтверждено источниками."""
    svet = pilot_entities["svetovit"]
    assert svet["identity"]["names"] == ["Световит"]
    by_path = {c["path"]: c for c in svet["claims"]}
    assert by_path["character.existence"]["status"] == "known"
    assert by_path["character.role"]["status"] == "unknown"  # draft 'chief_priest' — не факт
    svet_rel_targets = {r["target"] for r in svet["relations"]}
    assert "civ_hyperborea" in svet_rel_targets
    assert "char_010" in svet_rel_targets  # «Старший брат Славного» (char_009)

    velik = pilot_entities["person_velik"]
    v_by_path = {c["path"]: c for c in velik["claims"]}
    assert v_by_path["character.existence"]["status"] == "known"
    assert v_by_path["character.role"]["value"] == "главный герой"
    assert v_by_path["character.role"]["status"] == "known"
    assert v_by_path["character.role"].get("source_ref")
    assert v_by_path["character.age_range"]["status"] == "unknown"
    assert v_by_path["character.build"]["status"] == "unknown"
    assert v_by_path["character.movement"]["status"] == "unknown"
    v_rel_targets = {r["target"] for r in velik["relations"]}
    assert {"civ_hyperborea", "char_006", "char_004"} <= v_rel_targets

    temple = pilot_entities["location_temple"]
    t_by_path = {c["path"]: c for c in temple["claims"]}
    assert t_by_path["identity.one_line"]["status"] == "inferred"  # базовый факт FORM-карточки
    assert t_by_path["architecture.form"]["status"] == "unknown"
    assert temple["relations"] == []


def test_native_no_silent_loss_in_reports():
    """Migrated + native reports: nothing lost silently (unified report, main contract)."""
    entities, reports = loader.build_pilot_entities()
    # Check all entities for property loss - not just the original 5
    for report in reports:
        assert report["issues"] == [], f"{report['card_id']}: {report['issues']}"
        assert report["relationships_ok"], f"{report['card_id']}: relationships not preserved"
    native_entities, native_reports = loader.collect_native_entities()
    assert len(native_entities) == len(loader.NATIVE_CARDS)
    for report in native_reports:
        assert report["issues"] == [], f"{report['card_id']}: {report['issues']}"
    for report in reports:
        assert report["relationships_ok"]
