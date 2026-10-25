# -*- coding: utf-8 -*-
"""EDM-RES tests: knowledge operations + resolver + Dialogue/MediaPlan projections.

Owner scenarios (25.10.2026):
A. place (Arkaim): facts + UNKNOWN + artistic fill (weather=clear@mp1) +
   reconstruction; the world model view must NOT know about the fill;
B. character (СВЕТОВИТ): art-model appearance, UNKNOWN clothing, DERIVE
   character.role;
C. clothing (warrior clothing): FACT known+medium, RECONSTRUCT form,
   HYPOTHESIS association with СВЕТОВИТ (confidence 0.2).

Contract: layered integrity (ARTISTIC/FICTION/RECONSTRUCT NEVER overwrite
CANON), multi-status ledger, pure operations, no world-model pollution.
"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EDM_DIR = ROOT / "core" / "CORE" / "ENTITY_MODEL"
EXAMPLES_DIR = EDM_DIR / "examples"
PILOT_DIR = EDM_DIR / "pilot"


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, EDM_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


val = _load_module("edm_res_val", "entity_model_validate.py")
ops = _load_module("edm_res_ops", "operations.py")
res = _load_module("edm_res_res", "resolutions.py")


@pytest.fixture(scope="module")
def schema() -> dict:
    return val.load_schema()


def _load(filename: str) -> dict:
    return json.loads((EDM_DIR / filename).read_bytes().decode("utf-8-sig"))


# base entity: the owner's conflict scenario (Arkaim weather)


@pytest.fixture(scope="module")
def arkaim_base() -> dict:
    """Minimal Arkaim-style place: known facts + UNKNOWN weather/season."""
    return {
        "model": {"model_id": "arkaim-entity-description", "model_version": "0.2"},
        "identity": {
            "canonical_id": "arkaim",
            "type": "location",
            "names": ["Аркаим"],
            "one_line": "кольцевое укрепление у реки Синара",
            "is_reconstruction": False,
        },
        "time": {"note": "бронзовый век"},
        "claims": [
            {"path": "architecture.form", "value": "кольцевое укрепление", "status": "known",
             "provenance_class": "external_source", "source_ref": {"layer": "extended_world", "ref": "reg_arkaim", "path": "form"},
             "confidence": 0.9},
            {"path": "architecture.walls", "value": "концентрические", "status": "known",
             "provenance_class": "external_source", "source_ref": {"layer": "extended_world", "ref": "reg_arkaim", "path": "walls"},
             "confidence": 0.9},
            {"path": "architecture.materials", "value": None, "status": "unknown", "provenance_class": "none"},
            {"path": "environment.weather", "value": None, "status": "unknown", "provenance_class": "none"},
            {"path": "environment.season", "value": None, "status": "unknown", "provenance_class": "none"},
        ],
        "constraints": {},
    }


@pytest.fixture(scope="module")
def arkaim_mp1(arkaim_base: dict) -> dict:
    """Arkaim + the owner's fill: artistic weather=clear for media_plan mp1."""
    out = ops.artistic_fill(arkaim_base, "environment.weather", "clear", scope_level="media_plan", scope_id="mp1")
    out = ops.reconstruct(out, "architecture.materials", "глины", created_from=["external:site_report"], confidence=0.4)
    return out


# 1. schema v0.2 contract


class TestSchemaContract:
    def test_artistic_model_claim_accepted(self, schema, arkaim_base, arkaim_mp1):
        assert val.validate_entity(arkaim_mp1, schema) == []

    def test_artistic_model_requires_scope(self, schema, arkaim_base):
        claim = {"path": "environment.weather", "value": "clear", "status": "artistic_model",
                 "provenance_class": "artistic_model", "medium": True}
        out = copy.deepcopy(arkaim_base)
        out["claims"].append(claim)
        errors = val.validate_entity(out, schema)
        assert any("applies_to" in e for e in errors), errors

    def test_artistic_model_requires_medium(self, schema, arkaim_base):
        claim = {"path": "environment.weather", "value": "clear", "status": "artistic_model",
                 "provenance_class": "artistic_model", "medium": False,
                 "applies_to": {"level": "media_plan", "id": "mp1"}}
        out = copy.deepcopy(arkaim_base)
        out["claims"].append(claim)
        errors = val.validate_entity(out, schema)
        assert any("medium" in e for e in errors), errors

    def test_inferred_requires_created_from(self, schema, arkaim_base):
        claim = {"path": "character.role", "value": "воин", "status": "inferred",
                 "provenance_class": "derived",
                 "source_ref": {"layer": "none", "ref": "derived", "path": "character.role"}}
        out = copy.deepcopy(arkaim_base)
        out["claims"].append(claim)
        errors = val.validate_entity(out, schema)
        assert any("created_from" in e for e in errors), errors

    def test_validator_allows_multi_status_same_path(self, schema, arkaim_base, arkaim_mp1):
        # weather carries BOTH unknown (world) and artistic_model (mp1) — the ledger
        errors = val.validate_entity(arkaim_mp1, schema)
        assert errors == []

    def test_validator_forbids_full_duplicate(self, schema, arkaim_base):
        out = copy.deepcopy(arkaim_base)
        out["claims"].append({"path": "environment.weather", "value": None, "status": "unknown", "provenance_class": "none"})
        errors = val.validate_entity(out, schema)
        assert any("duplicate" in e for e in errors), errors


# 2. operations: purity + idempotence + conflict guard


class TestOperations:
    def test_operations_pure(self, arkaim_base):
        before = copy.deepcopy(arkaim_base)
        out = ops.artistic_fill(arkaim_base, "environment.weather", "clear", "media_plan", "mp1")
        assert arkaim_base == before, "operations must not mutate the input entity"
        assert out is not arkaim_base
        assert len(out["claims"]) == len(arkaim_base["claims"]) + 1

    def test_artistic_fill_idempotent(self, arkaim_base):
        once = ops.artistic_fill(arkaim_base, "environment.weather", "clear", "media_plan", "mp1")
        twice = ops.artistic_fill(once, "environment.weather", "clear", "media_plan", "mp1")
        assert len(twice["claims"]) == len(once["claims"]) == len(arkaim_base["claims"]) + 1

    def test_derive_requires_created_from(self, arkaim_base):
        with pytest.raises(ValueError):
            ops.derive(arkaim_base, "architecture.materials", "глина", created_from=[])

    def test_derive_conflict_with_fact_raises(self, arkaim_base):
        # walls is a known non-medium fact: DERIVE must not contradict it
        with pytest.raises(ops.EdmConflict):
            ops.derive(arkaim_base, "architecture.walls", "сплошные", created_from=["x"])

    def test_derive_replaces_unknown(self, arkaim_base):
        out = ops.derive(arkaim_base, "architecture.materials", "глина",
                         created_from=["architecture.form=кольцевое укрепление"], confidence=0.6)
        derived = [c for c in out["claims"] if c["path"] == "architecture.materials" and c["status"] == "inferred"]
        assert len(derived) == 1
        assert derived[0]["created_from"] == ["architecture.form=кольцевое укрепление"]
        assert derived[0]["medium"] is False

    def test_artistic_fill_value_not_none(self, arkaim_base):
        with pytest.raises(ValueError):
            ops.artistic_fill(arkaim_base, "environment.weather", None, "media_plan", "mp1")

    def test_fiction_requires_scope_id_for_non_world(self, arkaim_base):
        with pytest.raises(ValueError):
            ops.fiction(arkaim_base, "environment.weather", "ливень", "scene", None)


# 3. resolver: priority chain


class TestPriority:
    def test_known_beats_everything(self, arkaim_mp1):
        res_ = res.resolve_description(arkaim_mp1, {"media_plan": "mp1"})
        walls = res_["properties"]["architecture.walls"]["effective"]
        assert walls["value"] == "концентрические"
        assert walls["status"] == "known"

    def test_artistic_beats_unknown_in_its_scope(self, arkaim_mp1):
        res_ = res.resolve_description(arkaim_mp1, {"media_plan": "mp1"})
        weather = res_["properties"]["environment.weather"]["effective"]
        assert weather["value"] == "clear"
        assert weather["status"] == "artistic_model"

    def test_artistic_does_not_win_at_world_scope(self, arkaim_mp1):
        res_ = res.resolve_description(arkaim_mp1)
        weather = res_["properties"]["environment.weather"]["effective"]
        assert weather["status"] == "unknown"
        assert weather["value"] is None

    def test_chain_without_known(self, arkaim_base):
        out = ops.derive(arkaim_base, "environment.season", "лето", created_from=["klima"])
        out = ops.reconstruct(out, "environment.season", "середина лета", created_from=["ext_klimat"])
        out = ops.artistic_fill(out, "environment.season", "жаркое лето", "media_plan", "mp1")
        out = ops.fiction(out, "environment.season", "осеннее", "scene", "s1")
        # priority chain: DERIVED beats ARTISTIC/FICTION regardless of scope
        for scope in (None, {"media_plan": "mp1"}, {"scene": "s1"}, {"media_plan": "mp1", "scene": "s1"}):
            eff = res.resolve_description(out, scope)["properties"]["environment.season"]["effective"]
            assert eff["status"] == "inferred", (scope, eff)
        # layers carry the full picture for the consumer
        layers = res.resolve_description(out, {"media_plan": "mp1"})["properties"]["environment.season"]["layers"]
        assert [layer["status"] for layer in layers] == ["inferred", "reconstructed", "artistic_model", "unknown"]

    def test_narrower_scope_wins_between_fills(self, arkaim_base):
        out = ops.artistic_fill(arkaim_base, "environment.weather", "туман", "scene", "s2")
        out = ops.artistic_fill(out, "environment.weather", "закат", "media_plan", "mp1")
        both = res.resolve_description(out, {"scene": "s2", "media_plan": "mp1"})
        assert both["properties"]["environment.weather"]["effective"]["value"] == "закат"
        scene_only = res.resolve_description(out, {"scene": "s2"})
        assert scene_only["properties"]["environment.weather"]["effective"]["value"] == "туман"

    def test_temporal_ref_mismatch_excludes(self, arkaim_base):
        out = ops.artistic_fill(arkaim_base, "environment.weather", "ясно", "media_plan", "mp1", temporal_ref="summer")
        winter = res.resolve_description(out, {"media_plan": "mp1", "time": "winter"})
        assert winter["properties"]["environment.weather"]["effective"]["status"] == "unknown"
        summer = res.resolve_description(out, {"media_plan": "mp1", "time": "summer"})
        assert summer["properties"]["environment.weather"]["effective"]["status"] == "artistic_model"

    def test_known_medium_resolves_as_artistic(self, arkaim_base):
        out = copy.deepcopy(arkaim_base)
        claim = {
            "path": "environment.season", "value": "summer landscape (art-model)", "status": "known",
            "provenance_class": "ai_model_artistic", "medium": True, "confidence": 0.3,
        }
        out["claims"].append(claim)
        res_ = res.resolve_description(out)
        eff = res_["properties"]["environment.season"]["effective"]
        assert eff["status"] == "known" and eff["medium"] is True
        mp = res.to_mediaplan(out)
        assert mp["structured_prompt"]["environment"]["season"] == "(MEDIUM) summer landscape (art-model)"
        # facts keep their own properties; the art-tier value goes to ARTISTIC_CHOICES, never to facts
        assert [f["property"] for f in mp["material"]["facts"]] == ["architecture.form", "architecture.walls"]
        assert [a["property"] for a in mp["material"]["artistic_choices"]] == ["environment.season"]


# 4. conflict scenario (owner, verbatim) + no world-model pollution


class TestConflictScenario:
    def test_world_model_view(self, arkaim_mp1):
        mp = res.to_mediaplan(arkaim_mp1)
        assert mp["structured_prompt"]["environment"]["weather"] == "UNKNOWN"
        assert "clear" not in json.dumps(mp, ensure_ascii=False, default=str)

    def test_mediaplan_view_gets_the_choice_labelled(self, arkaim_mp1):
        mp = res.to_mediaplan(arkaim_mp1, {"media_plan": "mp1"})
        assert mp["structured_prompt"]["environment"]["weather"] == "(MEDIUM) clear"
        choice = mp["material"]["artistic_choices"]
        assert choice and choice[0]["value"] == "clear"
        assert choice[0]["scope"]["level"] == "media_plan"

    def test_world_model_facts_untouched(self, arkaim_base, arkaim_mp1):
        res_ = res.resolve_description(arkaim_mp1)
        for p in ("architecture.form", "architecture.walls"):
            eff = res_["properties"][p]["effective"]
            assert eff["status"] == "known"
            assert eff["medium"] is False
        assert arkaim_base["claims"][3]["value"] is None, "UNKNOWN fact must survive in the base entity"

    def test_llm_brief_separates_layers(self, arkaim_mp1):
        brief = res.to_llm_brief(arkaim_mp1, {"media_plan": "mp1"})
        assert [f["property"] for f in brief["FACTS"]] == ["architecture.form", "architecture.walls"]
        assert "environment.weather" not in brief["UNKNOWN"]
        assert [a["property"] for a in brief["ARTISTIC_CHOICES"]] == ["environment.weather"]
        recon = [a["property"] for a in brief["RECONSTRUCTIONS"]]
        assert "architecture.materials" in recon
        assert "UNKNOWN" in brief["instruction"]


# 5. owner scenario B: СВЕТОВИТ (character)


@pytest.fixture(scope="module")
def svetovit() -> dict:
    return _load("examples/svetovit_character.json")


@pytest.fixture(scope="module")
def clothing() -> dict:
    return _load("examples/warrior_clothing.json")


class TestSvetovitScenario:
    def test_dialogue_honest_about_appearance(self, svetovit):
        text = res.to_dialogue(svetovit)
        # art-model values are phrased as a choice, never as book facts
        assert "художественный выбор" in text, text
        assert "не установлено" in text.lower(), text
        brief = res.to_llm_brief(svetovit)
        fact_props = {f["property"] for f in brief["FACTS"]}
        art_props = {a["property"] for a in brief["ARTISTIC_CHOICES"]}
        assert "character.face" not in fact_props
        assert "character.face" in art_props
        assert "character.objects" in brief["UNKNOWN"]

    def test_derive_role_becomes_inference(self, svetovit):
        out = ops.derive(svetovit, "character.role", "воин, лидер общины",
                         created_from=["canonical_world:characters_living.satya_yuga"], confidence=0.6)
        mp = res.to_mediaplan(out)
        assert [d["property"] for d in mp["material"]["derived"]] == ["character.role"]
        brief = res.to_llm_brief(out)
        assert [d["property"] for d in brief["DERIVED"]] == ["character.role"]

    def test_unknown_clothing_boundary(self, svetovit):
        mp = res.to_mediaplan(svetovit)
        assert "character.objects" in mp["unknown_fields"]
        assert mp["structured_prompt"]["character"]["objects"] == "UNKNOWN"
        brief = res.to_llm_brief(svetovit)
        assert "character.objects" in brief["UNKNOWN"]


# 6. owner scenario C: warrior clothing


class TestWarriorClothingScenario:
    def test_art_model_fact_stays_medium_in_mediaplan(self, clothing):
        mp = res.to_mediaplan(clothing)
        assert "leather tunic" in mp["structured_prompt"]["clothing"]["items"]
        assert mp["structured_prompt"]["clothing"]["items"].startswith("(MEDIUM)")
        assert "clothing.items" in mp["medium_fields"]
        # the FACT block must NOT contain medium values
        assert mp["material"]["facts"] == []

    def test_relation_hypothesis_is_labelled_in_dialogue(self, clothing):
        text = res.to_dialogue(clothing)
        assert "световит" in text.lower(), text
        assert "(гипотеза" in text.lower(), text

    def test_mediaplan_relations_block(self, clothing):
        mp = res.to_mediaplan(clothing)
        wore = [r for r in mp["relations"] if r["type"] == "wears"]
        assert wore and wore[0]["confidence"] == 0.2
        assert wore[0]["target"] == "svetovit"


# 7. regression: examples + pilot still valid against v0.2; no data migrated yet


@pytest.fixture(scope="module")
def all_entities(schema: dict) -> list[tuple[str, dict]]:
    items: list[tuple[str, dict]] = []
    for p in sorted(EXAMPLES_DIR.glob("*.json")):
        items.append((f"example:{p.stem}", json.loads(p.read_bytes().decode("utf-8-sig"))))
    for p in sorted(PILOT_DIR.glob("*.json")):
        items.append((f"pilot:{p.stem}", json.loads(p.read_bytes().decode("utf-8-sig"))))
    return items


class TestRegression:
    def test_examples_and_pilot_pass_schema(self, all_entities, schema):
        failures = {}
        for name, entity in all_entities:
            errors = val.validate_entity(entity, schema)
            if errors:
                failures[name] = errors
        assert failures == {}, failures

    def test_no_artistic_or_fiction_claims_migrated_into_data(self, all_entities):
        """The mechanism exists, but no entity data carries artistic_model/fiction yet."""
        for name, entity in all_entities:
            statuses = {c.get("status") for c in entity.get("claims", [])}
            assert statuses.isdisjoint({"artistic_model", "fiction"}), f"{name}: unexpected new statuses"
