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
    raw = (EXT_MODEL_DIR / f"{category}.json").read_bytes().decode("utf-8-sig")
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
        ("region_arkaim", "geography", "region_arkaim"),
        ("steppe_climate", "climate", "steppe_climate"),
        ("arkaim_settlement", "architecture", "arkaim_settlement"),
        ("civ_hyperborea", "civilizations", "civ_hyperborea"),
        ("civ_arkaim_civilization", "civilizations", "civ_arkaim_civilization"),
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
    assert len(entities) == 5
    for report in reports:
        assert report["issues"] == [], f"{report['card_id']}: {report['issues']}"
        assert report["relationships_ok"]


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
    # reconstruction claims are medium=true: their values must NOT appear as plain facts
    plain = sentence.replace("(реконструкция, художественное допущение)", "")
    for c in entity["claims"]:
        if c.get("medium") and c.get("status") in {"reconstructed", "hypothesis"}:
            value_text = _fmt(c["value"])
            if value_text:
                assert value_text not in plain, f"reconstructed value {value_text!r} leaked into plain dialogue"


def test_mediaplan_labels_medium_facts(pilot_entities):
    fragment = projections.to_mediaplan_fragment(pilot_entities["civ_arkaim_civilization"])
    medium_paths = [p["path"] for p in fragment["provenance"] if p["medium"]]
    assert medium_paths, "medium facts must be flagged in mediaplan provenance"
    structured = json.dumps(fragment["structured_prompt"], ensure_ascii=False)
    assert "(MEDIUM)" in structured, "reconstructed values must carry the (MEDIUM) label in mediaplan"


def test_mediaplan_temporal_context(pilot_entities):
    fragment = projections.to_mediaplan_fragment(pilot_entities["civ_hyperborea"])
    assert fragment["temporal_context"]["epoch_ref"] == ["~7000-3000 до н.э."]
