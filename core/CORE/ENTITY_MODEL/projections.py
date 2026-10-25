# -*- coding: utf-8 -*-
"""EDM projections: dialogue sentence + MediaPlan fragment from an EDM entity.

Proofs the owner's pilot question: does ONE entity description model feed
both consumers (dialogue and media plan) without per-consumer ad-hoc defaults?

Rules (mirror the semantic contract of entity_description.schema.json):
- known claims -> stated as fact (no label);
- inferred claims -> stated with explicit «(вывод)» label;
- reconstructed/hypothesis claims -> NEVER stated as fact; labelled
  «(реконструкция, художественное допущение)» and excluded from dialogue;
- unknown claims -> «не установлено» (explicit boundary, NEVER a default);
- medium claims never silently leak into mediaplan: they carry the label.
"""

from __future__ import annotations


def _label_for(status: str) -> str | None:
    if status == "inferred":
        return "(вывод)"
    if status in {"reconstructed", "hypothesis"}:
        return "(реконструкция, художественное допущение)"
    if status == "unknown":
        return "не установлено"
    return None


def _fmt_value(value) -> str:
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if isinstance(value, dict):
        return ", ".join(f"{k}={v}" for k, v in value.items())
    return str(value)


def to_dialogue_sentence(entity: dict) -> str:
    """Plain-language description: canon/known facts only (reconstructions excluded)."""
    name = (entity.get("identity") or {}).get(
        "names", [entity.get("identity", {}).get("canonical_id", "?")]
    )[0]
    parts = [f"{name} — {entity['identity'].get('one_line', '')}"]

    facts = []
    for claim in entity.get("claims", []):
        status = claim.get("status")
        if status in {"reconstructed", "hypothesis"}:
            continue  # reconstruction never mixes into the plain fact sentence
        label = _label_for(status)
        if status == "unknown":
            facts.append(f"{claim['path'].split('.', 1)[1]} {label}")
        else:
            text = _fmt_value(claim.get("value"))
            facts.append(f"{text} {label}".strip() if label else text)
    if facts:
        parts.append("; ".join(facts))
    return ". ".join(p for p in parts if p) + "."


def to_mediaplan_fragment(entity: dict) -> dict:
    """Structured fragment in the shape MediaPlan.location/environment consumes.

    Unknowns stay explicit ("UNKNOWN"), never replaced by defaults
    (fail-open guard: no 'clear' / 'late summer' here).
    """
    fragment: dict = {
        "entity_id": entity.get("identity", {}).get("canonical_id"),
        "entity_type": entity.get("identity", {}).get("type"),
        "structured_prompt": {},
        "negative_constraints": [],
        "unknown_fields": [],
        "medium_fields": [],
    }
    for claim in entity.get("claims", []):
        path = claim["path"]
        status = claim.get("status")
        top, _, rest = path.partition(".")
        if status == "unknown":
            fragment["unknown_fields"].append(path)
            fragment["structured_prompt"].setdefault(top, {})[rest] = "UNKNOWN"
        else:
            value = _fmt_value(claim.get("value"))
            if claim.get("medium"):
                fragment["medium_fields"].append(path)
                value = f"(MEDIUM) {value}"
            fragment["structured_prompt"].setdefault(top, {})[rest] = value
    # time block projection
    time_block = entity.get("time") or {}
    if time_block.get("epoch_ref"):
        fragment["temporal_context"] = {"epoch_ref": time_block["epoch_ref"]}
    elif time_block.get("note"):
        fragment["temporal_context"] = {"note": time_block["note"]}
    # provenance: every medium/derived fact stays traceable
    fragment["provenance"] = [
        {
            "path": c["path"],
            "class": c.get("provenance_class"),
            "medium": bool(c.get("medium", False)),
        }
        for c in entity.get("claims", [])
    ]
    return fragment


def project(entity: dict) -> dict:
    """Both projections at once (the pilot's «живой вопрос + живой MediaPlan»)."""
    return {
        "dialogue_sentence": to_dialogue_sentence(entity),
        "mediaplan_fragment": to_mediaplan_fragment(entity),
    }
