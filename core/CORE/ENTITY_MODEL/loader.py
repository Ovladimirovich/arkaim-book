# -*- coding: utf-8 -*-
"""EDM pilot loader: migration of extended_world cards to Entity Description Model.

Owner-approved pilot (block C-pilot, 25.10.2026): migrate a LIMITED set of real
extended_world entities (core/CORE/WORLD_MODEL/*.json), verify round-trip losslessness
(no knowledge lost: every property is either a claim, a time-block entry, or an
explicitly reported unmapped presentation field), then project to dialogue / MediaPlan.

EDM role (fixed by owner): EDM is NOT a new primary fact base. It is a structured
per-entity description ASSEMBLED from the world sources with provenance and status:
Knowledge Core says "what we know and where from", World Model says "what is
related to what and when", EDM says "the complete structured state of this entity".

Pure module: stdlib only. No production-code dependency.

Usage (generate pilot entities):
    python core/CORE/ENTITY_MODEL/loader.py
    -> core/CORE/ENTITY_MODEL/pilot/<card_id>.json
    -> core/CORE/ENTITY_MODEL/PILOT_ROUNDTRIP_REPORT.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
REPO_ROOT = BASE.parents[2]
EXT_MODEL_DIR = REPO_ROOT / "core" / "CORE" / "WORLD_MODEL"
PILOT_DIR = BASE / "pilot"

# ---------------------------------------------------------------------------
# Category -> EDM entity type
# ---------------------------------------------------------------------------
CATEGORY_ENTITY_TYPE = {
    "geography": "location",
    "climate": "climate",
    "architecture": "building",
    "civilizations": "culture",
    "daily_life": "culture",
    "social_structure": "culture",
    "religion": "culture",
    "rituals": "culture",
    "transport": "object",
}

# ---------------------------------------------------------------------------
# Property -> EDM claim path (per category). Unlisted property goes to the
# UNMAPPED registry (presentation/UI fields are NOT knowledge) or, as fallback,
# is reported as "unmapped:review" — never silently dropped.
# ---------------------------------------------------------------------------
PROP_PATH_MAP = {
    "geography": {
        "coordinates": "place.coordinates",
    },
    "climate": {
        "type": "climate.type",
        "temperature_range": "climate.temperature_range",
        "precipitation": "climate.precipitation",
        "seasons": "climate.seasons",
    },
    "architecture": {
        "type": "architecture.form",
        "style": "architecture.style",
        "materials": "architecture.materials",
    },
    "civilizations": {
        "values": "culture.values",
    },
    "daily_life": {
        "values": "culture.values",
    },
    "social_structure": {
        "values": "culture.values",
    },
    "religion": {
        "values": "culture.values",
    },
    "rituals": {
        "values": "culture.values",
    },
}

# Explicit non-knowledge fields (map rendering only) — documented exclusions.
UNMAPPED_PRESENTATION = {
    "geography": {
        "color": "presentation: map coloring, not knowledge",
        "icon": "presentation: UI icon, not knowledge",
        "type": "presentation: card classification tag, not migrated",
    },
}

# ---------------------------------------------------------------------------
# Deterministic provenance mapping (extended_world card fields -> EDM class).
# The pilot must prove: ARTISTIC_MODEL did not become CANON and vice versa.
# First matching rule wins; fallback is the last rule (None key).
# ---------------------------------------------------------------------------
PROVENANCE_RULES: list[tuple[dict | None, tuple[str, str, bool]]] = [
    # (card field predicates, (provenance_class, status, medium))
    (
        {"source_level": "CANON", "provenance_category": "AUTHOR_CANON"},
        ("author_canon", "known", False),
    ),
    (
        {"provenance_category": "RECONSTRUCTION"},
        ("reconstruction", "reconstructed", True),
    ),
    (
        {"source_level": "HISTORICAL", "provenance_category": "EXTERNAL_SOURCE"},
        ("external_source", "known", False),
    ),
    # fallback: auto-extracted / unknown provenance — never canon
    (None, ("derived", "inferred", False)),
]


def _match_provenance(card: dict) -> tuple[str, str, bool]:
    for predicates, result in PROVENANCE_RULES:
        if predicates is None:
            return result
        if all(predicates.get(k) == card.get(k) for k in predicates):
            return result
    return ("derived", "inferred", False)


# ---------------------------------------------------------------------------
# Time: era/epoch card properties go to the time block, not to claims.
# ---------------------------------------------------------------------------
TIME_PROPS = {"era", "epoch"}


def load_card(category: str, card_id: str) -> dict:
    """Read a single extended_world card (BOM-safe)."""
    raw = (EXT_MODEL_DIR / f"{category}.json").read_bytes().decode("utf-8-sig")
    data = json.loads(raw)
    cards = data if isinstance(data, list) else data.get(category, [])
    for card in cards:
        if card.get("id") == card_id:
            return card
    raise KeyError(
        f"{category}:{card_id} not found in {EXT_MODEL_DIR / f'{category}.json'}"
    )


# ---------------------------------------------------------------------------
# Pilot entity set + generated cross-references (documented derivations,
# provenance_class=derived, medium=false — never canon).
# ---------------------------------------------------------------------------
PILOT_ENTITIES: list[tuple[str, str, list[dict] | None]] = [
    ("geography", "region_arkaim", None),
    (
        "climate",
        "steppe_climate",
        [
            {
                "type": "climate_of",
                "target": "region_arkaim",
                "target_type": "location",
                "label": "Климат степи действует на территорию Аркаима (Южный Урал)",
                "provenance_class": "derived",
                "confidence": 0.6,
                "note": "generated during pilot: совпадение региона (Южный Урал) в описаниях обеих карточек; вывод, не канон",
            }
        ],
    ),
    (
        "architecture",
        "arkaim_settlement",
        [
            {
                "type": "located_in",
                "target": "region_arkaim",
                "target_type": "location",
                "label": "Круговое укрепленное поселение в регионе Аркаим",
                "provenance_class": "derived",
                "confidence": 0.8,
                "note": "generated during pilot: name match 'Аркаим' в обеих карточках; вывод, не канон",
            }
        ],
    ),
    ("civilizations", "civ_hyperborea", None),
    (
        "civilizations",
        "civ_arkaim_civilization",
        [
            {
                "type": "associated_with",
                "target": "civ_hyperborea",
                "target_type": "culture",
                "label": "Цивилизация потомков гипербореев (связь в описании карточки)",
                "provenance_class": "derived",
                "confidence": 0.7,
                "note": "generated during pilot: 'потомки гипербореев' из description; вывод, не канон",
            }
        ],
    ),
]


# ---------------------------------------------------------------------------
# E1 (план EDM-RES, фаза 4): native (owner-authored) pilot cards.
# Live in pilot/ ALONGSIDE the migrated cards but are NOT generated by this
# pipeline: they have no extended_world source card. The loader only checks
# structure + reports; content is the owner's artifact (fail-closed: unverified
# draft values are demoted to unknown-claims with the draft value kept in note).
# OWNER decision 2026-10-26: svetovit + location_temple retained (unconfirmed
# values stay unknown); person_velik added (genome char_003 confirmed);
# person_arkaim_elder (no source for a named character) and
# artifact_ankh (no source in the book; placeholder URL) removed from catalog.
# Full schema + semantic validation: python entity_model_validate.py pilot/.
# ---------------------------------------------------------------------------
NATIVE_CARDS: list[str] = [
    "svetovit",
    "location_temple",
    "person_velik",
]

_MEDIUM_STATUSES = {"reconstructed", "hypothesis", "artistic_model", "fiction"}


def _structural_issues(entity: dict) -> list[str]:
    """Stdlib-only structural sanity check for a native EDM card.

    Deliberately not the full validator (entity_model_validate.py needs
    jsonschema): this keeps the loader a pure module. Checks: required
    blocks, claim fields, unknown ⇒ value=null, known/inferred ⇒ source_ref,
    medium-required statuses ⇒ medium=true, relation fields, and that every
    constraints.required_unknown path has an unknown/not_applicable claim.
    """
    issues: list[str] = []
    for key in ("model", "identity", "claims"):
        if key not in entity:
            issues.append(f"missing required block: {key}")
    identity = entity.get("identity") or {}
    if not identity.get("canonical_id"):
        issues.append("identity.canonical_id missing/empty")
    if not identity.get("type"):
        issues.append("identity.type missing/empty")
    claims = entity.get("claims")
    if not isinstance(claims, list) or not claims:
        issues.append("claims must be a non-empty array")
        claims = []
    for claim in claims:
        for field in ("path", "status", "provenance_class"):
            if field not in claim:
                issues.append(f"claim missing field: {field}")
        if claim.get("status") == "unknown" and claim.get("value") is not None:
            issues.append(f"unknown claim {claim.get('path')!r} must carry value=null")
        if claim.get("status") in {"known", "inferred"} and not claim.get("source_ref"):
            issues.append(f"claim {claim.get('path')!r} ({claim.get('status')}) requires source_ref")
        if claim.get("status") in _MEDIUM_STATUSES and not claim.get("medium"):
            issues.append(f"claim {claim.get('path')!r} ({claim.get('status')}) requires medium=true")
    for relation in entity.get("relations") or []:
        for field in ("type", "target", "target_type"):
            if field not in relation:
                issues.append(f"relation missing field: {field} ({relation!r})")
    for required in (entity.get("constraints") or {}).get("required_unknown") or []:
        if not any(
            c.get("path") == required and c.get("status") in {"unknown", "not_applicable"} for c in claims
        ):
            issues.append(f"constraints.required_unknown {required!r} has no unknown claim")
    return issues


def collect_native_entities() -> tuple[list[dict], list[dict]]:
    """Load the E1 native cards from pilot/ + structural reports.

    Returns (entities, reports); each native report is
    {"category": "native", "card_id", "source_file", "issues"}.
    Unlike migrated reports there is no properties/round-trip map: a native
    card is authored, not migrated — losslessness is the schema contract.
    """
    entities: list[dict] = []
    reports: list[dict] = []
    for card_id in NATIVE_CARDS:
        path = PILOT_DIR / f"{card_id}.json"
        issues: list[str] = []
        entity: dict | None = None
        try:
            raw = path.read_bytes().decode("utf-8-sig")
            entity = json.loads(raw)
        except Exception as exc:  # missing/corrupt card must not kill the run
            issues.append(f"cannot load {path.name}: {exc}")
        if entity is not None:
            issues.extend(_structural_issues(entity))
            entities.append(entity)
        reports.append(
            {
                "category": "native",
                "card_id": card_id,
                "source_file": f"ENTITY_MODEL/pilot/{card_id}.json",
                "issues": issues,
            }
        )
    return entities, reports


def build_pilot_entities() -> tuple[list[dict], list[dict]]:
    """Return (entities, roundtrip_reports). Reports check losslessness."""
    entities: list[dict] = []
    reports: list[dict] = []
    for category, card_id, relations in PILOT_ENTITIES:
        card = load_card(category, card_id)
        entity = card_to_edm(card, category, relations)
        entities.append(entity)
        claims_by_path = {c["path"]: c for c in entity["claims"]}
        report: dict = {
            "category": category,
            "card_id": card_id,
            "properties": {},
            "issues": [],
        }
        for prop, value in (card.get("properties") or {}).items():
            mapping = entity["pilot"]["roundtrip_map"]["properties"].get(prop)
            if mapping is None:
                report["issues"].append(f"property {prop} not accounted for")
                continue
            if mapping.startswith("claim:"):
                path = mapping.split(":", 1)[1]
                ok = claims_by_path.get(path, {}).get("value") == value
                report["properties"][prop] = "ok" if ok else f"VALUE MISMATCH at {path}"
                if not ok:
                    report["issues"].append(f"value mismatch for {prop}")
            else:
                report["properties"][prop] = mapping
        # relationships losslessness: card relationships must be preserved verbatim
        card_rels = card.get("relationships") or []
        entity_rels = entity.get("relations", [])[: len(card_rels)]
        report["relationships_ok"] = entity_rels == card_rels
        if not report["relationships_ok"]:
            report["issues"].append("card relationships not preserved")
        reports.append(report)
    return entities, reports


def main(argv: list[str] | None = None) -> int:
    entities, reports = build_pilot_entities()
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    for entity in entities:
        card_id = entity["pilot"]["card_id"]
        out = PILOT_DIR / f"{card_id}.json"
        out.write_text(
            json.dumps(entity, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"wrote {out.relative_to(REPO_ROOT)}")
    # E1 native cards: authored artifacts — validate structure only, never regenerate.
    _native_entities, native_reports = collect_native_entities()
    all_reports = reports + native_reports
    # Report lives OUTSIDE pilot/ on purpose: the EDM validator globs *.json in
    # a directory as entity cards, and this file is a list (a report, not a card).
    report_path = BASE / "PILOT_ROUNDTRIP_REPORT.json"
    report_path.write_text(
        json.dumps(all_reports, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {report_path.relative_to(REPO_ROOT)}")
    issues = [i for r in all_reports for i in r["issues"]]
    print(
        f"round-trip report: {len(reports)} migrated + {len(native_reports)} native cards, "
        f"issues: {len(issues)}"
    )
    for i in issues:
        print("  -", i)
    print(
        "\nnote: native cards are owner-authored — content decisions "
        "stay with the owner; full validation: python entity_model_validate.py --strict pilot/"
    )
    return 1 if issues else 0


def card_to_edm(
    card: dict, category: str, generated_relations: list[dict] | None = None
) -> dict:
    """Convert one extended_world card into an EDM entity + round-trip report.

    Losslessness contract: every card property is accounted for in
    pilot.roundtrip_map.properties as "claim:<path>" | "time" | "unmapped:<reason>".
    """
    category_key = category.lower()
    entity_type = CATEGORY_ENTITY_TYPE.get(category_key, "object")
    pclass, status, medium = _match_provenance(card)
    confidence = card.get("confidence")
    source_ref = {
        "layer": "extended_world",
        "ref": f"{category}.{card.get('id')}",
        "path": "card",
    }

    claims: list[dict] = []
    roundtrip_props: dict[str, str] = {}

    for prop, value in (card.get("properties") or {}).items():
        if prop in TIME_PROPS:
            roundtrip_props[prop] = "time"
            continue
        target = PROP_PATH_MAP.get(category_key, {}).get(prop)
        if target:
            claims.append(
                {
                    "path": target,
                    "value": value,
                    "status": status,
                    "provenance_class": pclass,
                    "source_ref": {**source_ref, "path": f"properties.{prop}"},
                    "confidence": confidence,
                    **({"medium": True} if medium else {}),
                }
            )
            roundtrip_props[prop] = f"claim:{target}"
        elif prop in UNMAPPED_PRESENTATION.get(category_key, {}):
            roundtrip_props[prop] = (
                f"unmapped:{UNMAPPED_PRESENTATION[category_key][prop]}"
            )
        else:
            # Not presentation, not mapped: explicit review flag, NEVER silent loss.
            roundtrip_props[prop] = "unmapped:review"

    # Time block from era/epoch properties
    time_props = {
        p: v for p, v in (card.get("properties") or {}).items() if p in TIME_PROPS
    }
    time_block = {
        "epoch_ref": [str(v) for v in time_props.values()] if time_props else [],
        "start": None,
        "end": None,
        "temporal_links": [],
        "note": "era/epoch из карточки extended_world"
        if time_props
        else "эпоха не установлена в источнике",
    }

    # Explicit UNKNOWN boundary for locations (fail-open guard): weather/season are
    # NOT established by extended_world -> must stay null, never default "clear".
    constraints: dict = {}
    if entity_type == "location":
        for path in ("environment.weather", "environment.season"):
            claims.append(
                {
                    "path": path,
                    "value": None,
                    "status": "unknown",
                    "provenance_class": "none",
                    "note": "extended_world не устанавливает погоду/сезон — явная граница знания, не дефолт",
                }
            )
        constraints["required_unknown"] = ["environment.weather", "environment.season"]

    relations: list[dict] = list(card.get("relationships") or []) + list(
        generated_relations or []
    )

    names = [card.get("name") or ""]
    if card.get("name_ru") and card.get("name_ru") != card.get("name"):
        names.append(card["name_ru"])

    entity = {
        "model": {
            "model_id": "arkaim-entity-description",
            "model_version": "v0.1",
            "created_at": "2026-10-25",
            "schema_version": "1.0",
            "note": f"Pilot: автоматическая миграция extended_world карточки {category}.{card.get('id')}",
        },
        "identity": {
            "canonical_id": str(card.get("id")),
            "type": entity_type,
            "names": names,
            "aliases": [],
            "one_line": card.get("description") or "",
        },
        "time": time_block,
        "claims": claims,
        "relations": relations,
        "constraints": constraints,
        "pilot": {
            "source_card_file": f"WORLD_MODEL/{category}.json",
            "card_id": str(card.get("id")),
            "provenance_category": card.get("provenance_category"),
            "source_level": card.get("source_level"),
            "roundtrip_map": {
                "properties": roundtrip_props,
                "relationships": f"relations ({len(card.get('relationships') or [])} из карточки + {len(generated_relations or [])} generated)",
                "provenance": f"provenance_class={pclass}, medium={medium}",
                "source": "source_ref.layer=extended_world, source_ref.ref=<category>.<card_id>",
                "confidence": "claim.confidence = card.confidence",
            },
            "note": "Пилотный миграционный артефакт: не канон, не новая база фактов — проекция extended_world в EDM с сохранением provenance и статуса.",
        },
    }
    return entity


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
