# -*- coding: utf-8 -*-
"""Tests for the standalone EDM validator (core/CORE/ENTITY_MODEL).

EDM — новая структурная модель описательного знания (см. docs/ENTITY_DESCRIPTION_MODEL_2026-10-25.md).
Стандарты: jsonschema-валидность + семантические правила (unknown/medium/provenance).
"""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EDM_DIR = ROOT / "core" / "CORE" / "ENTITY_MODEL"
EXAMPLES = EDM_DIR / "examples"

spec = importlib.util.spec_from_file_location(
    "ed_validator", EDM_DIR / "entity_model_validate.py"
)
ed = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(ed)


@pytest.fixture(scope="module")
def schema() -> dict:
    return ed.load_schema()


@pytest.fixture(scope="module")
def arkaim() -> dict:
    return ed.load_entity(EXAMPLES / "arkaim_location.json")


def _errors(entity: dict, schema: dict) -> list[str]:
    return ed.validate_entity(entity, schema)


def _claim(entity: dict, path: str) -> dict:
    for c in entity["claims"]:
        if c["path"] == path:
            return c
    raise KeyError(path)


# --- позитивные: контрольные примеры прошли ----------------------------------

@pytest.mark.parametrize("name", ["arkaim_location.json", "svetovit_character.json", "warrior_clothing.json"])
def test_examples_pass(schema, name):
    assert _errors(ed.load_entity(EXAMPLES / name), schema) == []


# --- negative: fail-open дефолт НЕ проходит -----------------------------------

def test_unknown_must_not_carry_value(arkaim, schema):
    """Регрессия на fail-open: weather='clear' как fact запрещён — unknown требует value=null."""
    bad = copy.deepcopy(arkaim)
    c = _claim(bad, "environment.weather")
    c["status"] = "known"
    c["value"] = "clear"
    c["provenance_class"] = "external_source"
    c["source_ref"] = {"layer": "extended_world", "ref": "CLIMATE.steppe_climate", "path": "defaults"}
    errs = _errors(bad, schema)
    # карточка в целом теперь противоречит constraints.required_unknown
    assert any("required_unknown" in e for e in errs)


def test_unknown_with_value_fails(arkaim, schema):
    bad = copy.deepcopy(arkaim)
    c = _claim(bad, "environment.weather")
    c["value"] = "clear"
    errs = _errors(bad, schema)
    assert any("unknown requires value=null" in e for e in errs)


def test_unknown_with_non_none_provenance_fails(arkaim, schema):
    bad = copy.deepcopy(arkaim)
    c = _claim(bad, "environment.weather")
    c["provenance_class"] = "external_source"
    errs = _errors(bad, schema)
    assert any("unknown must have provenance_class=none" in e for e in errs)


# --- negative: medium/provenance дисциплина -----------------------------------

def test_medium_requires_ai_provenance(arkaim, schema):
    bad = copy.deepcopy(arkaim)
    c = _claim(bad, "place.landscape")
    c["provenance_class"] = "external_source"
    errs = _errors(bad, schema)
    assert any("medium=true requires AI provenance class" in e for e in errs)


def test_reconstructed_requires_medium(arkaim, schema):
    bad = copy.deepcopy(arkaim)
    c = _claim(bad, "architecture.materials")
    c["medium"] = False
    errs = _errors(bad, schema)
    assert any("must be medium=true" in e for e in errs)


def test_forbid_medium_blocks_medium_on_path(arkaim, schema):
    """forbid_medium: базовые факты (place.region) не могут быть medium."""
    bad = copy.deepcopy(arkaim)
    c = _claim(bad, "place.region")
    c["medium"] = True
    c["provenance_class"] = "ai_model_artistic"
    c.pop("source_ref", None)
    c["status"] = "known"
    errs = _errors(bad, schema)
    assert any("forbid_medium" in e for e in errs)


def test_missing_required_unknown_fails(arkaim, schema):
    bad = copy.deepcopy(arkaim)
    bad["claims"] = [c for c in bad["claims"] if c["path"] != "environment.weather"]
    errs = _errors(bad, schema)
    assert any("required_unknown" in e and "weather" in e for e in errs)


def test_duplicate_claim_fails(arkaim, schema):
    # v0.2 ledger: a FULL duplicate (same path + status + scope) is still forbidden
    bad = copy.deepcopy(arkaim)
    bad["claims"].append(copy.deepcopy(_claim(bad, "environment.weather")))
    errs = _errors(bad, schema)
    assert any("duplicate" in e for e in errs)


def test_multi_status_same_path_allowed(arkaim, schema):
    """v0.2: one property may carry several claims of different status/scope.

    Owner scenario G: environment.weather=UNKNOWN (world) +
    environment.weather=clear@ARTISTIC_MODEL (media_plan) live side by side.
    """
    ok = copy.deepcopy(arkaim)
    ok["claims"].append(
        {
            "path": "environment.weather",
            "value": "clear",
            "status": "artistic_model",
            "provenance_class": "artistic_model",
            "medium": True,
            "applies_to": {"level": "media_plan", "id": "mp1"},
        }
    )
    assert _errors(ok, schema) == []


# --- relations ----------------------------------------------------------------

def test_wears_must_target_character(arkaim, schema):
    bad = copy.deepcopy(arkaim)
    bad["relations"].append(
        {"type": "wears", "target": "x", "target_type": "building"}
    )
    errs = _errors(bad, schema)
    assert any("wears" in e and "character" in e for e in errs)


# --- schema-level: broken enum / required --------------------------------------

def test_bad_type_fails_schema(arkaim, schema):
    bad = copy.deepcopy(arkaim)
    bad["identity"]["type"] = "weather_station"
    errs = _errors(bad, schema)
    assert any("schema:" in e for e in errs)


def test_known_claim_without_source_ref_fails(arkaim, schema):
    bad = copy.deepcopy(arkaim)
    c = _claim(bad, "place.region")
    c.pop("source_ref")
    errs = _errors(bad, schema)
    assert any("requires source_ref" in e for e in errs)


def test_examples_are_valid_json():
    """Минимальная гигиена: все примеры парсятся (в т.ч. без BOM-сюрпризов)."""
    for p in sorted(EXAMPLES.glob("*.json")):
        json.loads(p.read_bytes().decode("utf-8-sig"))
