# -*- coding: utf-8 -*-
"""EDM description resolution (EDM-RES): RESOLVER + Dialogue / MediaPlan / LLM-brief projections.

Owner contract (25.10.2026):
- RESOLVER assembles an entity description for a given scope
  (world / era / place / scene / media_plan / frame, + optional temporal_ref)
  from ALL claims of a property, taking into account status priority, scope,
  time and confidence;
- priority (owner order): CANON (known, author_canon) > EXTERNAL (known,
  external_source) > DERIVED (inferred) > RECONSTRUCTION (reconstructed) >
  HYPOTHESIS (hypothesis) > ARTISTIC_MODEL > FICTION > UNKNOWN;
  a known+medium claim (an art-model value in ext-model) resolves at the
  ARTISTIC tier, never as a fact;
- a claim with `applies_to` is valid only inside its scope: resolving at the
  World Model level does NOT see scene/media_plan fills — the artistic layer
  never leaks into the base facts;
- projections:
  * :func:`to_mediaplan` — structured material for a visual task: separate
    blocks FACTS / DERIVED / RECONSTRUCTIONS / ARTISTIC_CHOICES / UNKNOWN
    (visual-ready values, medium always labelled);
  * :func:`to_dialogue` — honest layered answer: canon as fact, inference with
    a label, reconstruction as an assumption, the artistic choice as a choice
    with its scope, unknowns as «not established»;
  * :func:`to_llm_brief` — the material for an LLM: facts/reconstructions/
    artistic/unknown blocks + a strict instruction. EDM/Resolver decides WHAT
    may be said; the LLM only formulates it.
"""

from __future__ import annotations

import json

_SCOPE_KEYS = {"era": "era", "place": "place", "scene": "scene", "media_plan": "media_plan", "frame": "frame"}
_SCOPE_RANK = {"world": 0, "era": 1, "place": 2, "scene": 3, "media_plan": 4, "frame": 5}

_RANK = {
    "unknown": 6,
    "not_applicable": 6,
    "artistic_model": 4,
    "fiction": 5,
    "reconstructed": 2,
    "hypothesis": 3,
    "inferred": 1,
}

LLM_INSTRUCTION = (
    "Не выдумывай значения полей из блока UNKNOWN. "
    "Значения из RECONSTRUCTIONS/ARTISTIC_CHOICES/FICTION — не факт книги: "
    "показывай их с их меткой (реконструкция/художественный выбор/фикшн), "
    "DERIVED — как вывод. Факты из FACTS можно говорить прямо."
)


def _fmt_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if isinstance(value, dict):
        return ", ".join(f"{k}={v}" for k, v in value.items())
    return str(value)


def _rank(claim: dict) -> int:
    status = claim.get("status")
    if status == "known":
        # a known value that is an art-model (medium=true) is an ARTISTIC tier,
        # never a fact
        return 4 if claim.get("medium") else 0
    return _RANK.get(status, 6)


def _applicable(claim: dict, scope: dict) -> bool:
    a = claim.get("applies_to") or {}
    level = a.get("level", "world")
    if level != "world":
        sid = a.get("id")
        if scope.get(_SCOPE_KEYS[level]) != sid:
            return False
    temporal = a.get("temporal_ref")
    if temporal and scope.get("time") not in (None, temporal):
        return False
    return True


def _claim_sort_key(index: int, claim: dict) -> tuple:
    a = claim.get("applies_to") or {}
    level = a.get("level", "world")
    narrow = -_SCOPE_RANK.get(level, 0)  # the narrower the scope — the more specific — the higher the priority
    pclass = claim.get("provenance_class")
    pc = 0 if pclass == "author_canon" else (1 if pclass == "external_source" else 2)
    conf = claim.get("confidence")
    cf = -conf if isinstance(conf, (int, float)) else 1.0
    return (_rank(claim), narrow, pc, cf, index)


def _public(claim: dict) -> dict:
    return {
        "path": claim.get("path"),
        "value": claim.get("value"),
        "status": claim.get("status"),
        "provenance_class": claim.get("provenance_class"),
        "medium": bool(claim.get("medium", False)),
        "confidence": claim.get("confidence"),
        "applies_to": claim.get("applies_to"),
        "created_from": claim.get("created_from"),
        "source_ref": claim.get("source_ref"),
    }


def resolve_description(entity: dict, scope: dict | None = None) -> dict:
    """Per-property resolution result for a scope.

    `properties` maps a path to `effective` (the winner by the priority chain)
    and `layers` (all applicable claims, most authoritative first). If two
    claims of the top tier have different values — a `conflicts` entry
    (an explicit signal, never a silent overwrite).
    """
    scope = dict(scope or {})
    claims = [c for c in entity.get("claims", []) if _applicable(c, scope)]
    per_path: dict[str, list] = {}
    for i, c in enumerate(claims):
        per_path.setdefault(c["path"], []).append((i, c))

    properties: dict[str, dict] = {}
    conflicts: list[dict] = []
    for path in sorted(per_path):
        group = sorted(per_path[path], key=lambda ic: _claim_sort_key(ic[0], ic[1]))
        winner = group[0][1]
        top_rank = _rank(winner)
        top_tier = [c for _i, c in group if _rank(c) == top_rank]
        distinct = {json.dumps(c.get("value"), sort_keys=True, ensure_ascii=False) for c in top_tier}
        is_conflict = len(distinct) > 1
        if is_conflict:
            conflicts.append({"path": path, "values": [c.get("value") for c in top_tier]})
        properties[path] = {
            "effective": _public(winner),
            "layers": [_public(c) for _i, c in group],
            "conflict": is_conflict,
        }
    identity = entity.get("identity") or {}
    return {
        "entity_id": identity.get("canonical_id"),
        "entity_type": identity.get("type"),
        "scope": scope,
        "properties": properties,
        "conflicts": conflicts,
    }


def _material_blocks(resolution: dict) -> dict:
    facts: list[dict] = []
    derived: list[dict] = []
    reconstructions: list[dict] = []
    artistic: list[dict] = []
    unknowns: list[str] = []
    for path, prop in resolution["properties"].items():
        eff = prop["effective"]
        status = eff["status"]
        entry = {
            "property": path,
            "value": eff["value"],
            "confidence": eff["confidence"],
            "provenance_class": eff["provenance_class"],
        }
        if status in {"unknown", "not_applicable"}:
            unknowns.append(path)
        elif status == "inferred":
            entry["created_from"] = eff.get("created_from")
            derived.append(entry)
        elif status in {"reconstructed", "hypothesis"}:
            entry["created_from"] = eff.get("created_from")
            reconstructions.append(entry)
        elif eff["medium"]:  # artistic_model / fiction / known+medium (art-model)
            entry["scope"] = eff.get("applies_to")
            entry["created_from"] = eff.get("created_from")
            artistic.append(entry)
        else:
            facts.append(entry)
    return {
        "facts": facts,
        "derived": derived,
        "reconstructions": reconstructions,
        "artistic_choices": artistic,
        "unknown": unknowns,
    }


def _temporal_context(entity: dict, resolution: dict) -> dict | None:
    time_block = entity.get("time") or {}
    ctx: dict = {}
    if time_block.get("epoch_ref"):
        ctx["epoch_ref"] = time_block["epoch_ref"]
    if resolution["scope"].get("time"):
        ctx["temporal_ref"] = resolution["scope"]["time"]
    elif time_block.get("note"):
        ctx["note"] = time_block["note"]
    return ctx or None


def to_mediaplan(entity: dict, scope: dict | None = None) -> dict:
    """Visual-ready material for a task (the owner's «MediaPlan» projection).

    `structured_prompt` — plain values for facts; medium values carry a
    `(MEDIUM)` label; unknowns stay `"UNKNOWN"` (never a default).
    `material` — separate blocks: facts / derived / reconstructions /
    artistic_choices (with their scope) / unknown.
    """
    resolution = resolve_description(entity, scope)
    material = _material_blocks(resolution)

    structured: dict[str, dict] = {}
    medium_fields: list[str] = []
    for path, prop in resolution["properties"].items():
        eff = prop["effective"]
        top, _, rest = path.partition(".")
        if eff["status"] in {"unknown", "not_applicable"}:
            structured.setdefault(top, {})[rest] = "UNKNOWN"
        else:
            text = _fmt_value(eff["value"])
            if eff["medium"]:
                medium_fields.append(path)
                text = f"(MEDIUM) {text}"
            structured.setdefault(top, {})[rest] = text

    relations = []
    for rel in entity.get("relations", []):
        relations.append(
            {
                "type": rel.get("type"),
                "target": rel.get("target") or rel.get("target_id") or rel.get("label"),
                "label": rel.get("label"),
                "provenance_class": rel.get("provenance_class"),
                "confidence": rel.get("confidence"),
            }
        )

    fragment = {
        "entity_id": resolution["entity_id"],
        "entity_type": resolution["entity_type"],
        "scope": resolution["scope"] or {"level": "world"},
        "structured_prompt": structured,
        "negative_constraints": list((entity.get("constraints") or {}).get("forbid_medium", [])),
        "unknown_fields": material["unknown"],
        "medium_fields": medium_fields,
        "material": material,
        "relations": relations,
        "conflicts": resolution["conflicts"],
    }
    temporal = _temporal_context(entity, resolution)
    if temporal:
        fragment["temporal_context"] = temporal
    fragment["provenance"] = [
        {
            "path": path,
            "class": prop["effective"]["provenance_class"],
            "status": prop["effective"]["status"],
            "medium": prop["effective"]["medium"],
        }
        for path, prop in resolution["properties"].items()
    ]
    return fragment


def _relation_sentence(rel: dict) -> str | None:
    label = rel.get("label") or rel.get("target")
    if not label:
        return None
    pclass = rel.get("provenance_class")
    conf = rel.get("confidence")
    if pclass in {"ai_model", "ai_model_artistic", "artistic_model"}:
        return f"{label} (художественная модель)"
    if pclass == "reconstruction":
        return f"{label} (реконструкция, художественное допущение)"
    if conf is not None and conf < 0.5:
        return f"{label} (гипотеза, уверенность {conf})"
    if pclass in {"none", "derived"} and conf is None:
        return f"{label} (гипотеза)"
    if pclass == "derived":
        return f"{label} (вывод)"
    return f"Связь: {label}"


def to_dialogue(entity: dict, scope: dict | None = None) -> str:
    """An honest layered answer (the owner's «Dialogue» projection).

    Canon — as fact; inference — with a «(inference)» label; reconstruction /
    hypothesis — as an assumption with a label; the artistic choice — as a
    choice with its scope; unknown — «not established». An art-model value is
    never presented as a book fact.
    """
    resolution = resolve_description(entity, scope)
    identity = entity.get("identity") or {}
    name = (identity.get("names") or [identity.get("canonical_id") or "?"])[0]

    canon, external, derived_lines, assumption_lines, choice_lines, unknown_names = [], [], [], [], [], []
    for path, prop in resolution["properties"].items():
        eff = prop["effective"]
        short = path.split(".", 1)[1]
        if eff["status"] in {"unknown", "not_applicable"}:
            unknown_names.append(short)
            continue
        text = _fmt_value(eff["value"])
        if eff["status"] == "known" and not eff["medium"]:
            item = f"{short} — {text}"
            if eff["provenance_class"] == "author_canon":
                canon.append(item)
            else:
                external.append(item)
        elif eff["status"] == "inferred":
            derived_lines.append(f"{short} — {text} (вывод)")
        elif eff["status"] in {"reconstructed", "hypothesis"}:
            assumption_lines.append(f"{short} — {text} (реконструкция, художественное допущение)")
        else:  # medium tier: artistic_model / fiction / known+medium
            a = eff.get("applies_to") or {}
            level = a.get("level")
            scope_txt = "world" if not level or level == "world" else f"{level}:{a.get('id')}"
            choice_lines.append(f"{short} — {text} (художественный выбор, scope {scope_txt})")

    parts = [f"{name} — {identity.get('one_line', '')}"]
    blocks: list[str] = []
    if canon:
        blocks.append("Книга описывает: " + "; ".join(canon) + ".")
    if external:
        blocks.append("По внешним источникам: " + "; ".join(external) + ".")
    if derived_lines:
        blocks.append(" ".join(derived_lines) + ".")
    if assumption_lines:
        blocks.append(" ".join(assumption_lines) + ".")
    if choice_lines:
        blocks.append(" ".join(choice_lines) + ".")
    relation_lines = [s for s in (_relation_sentence(r) for r in entity.get("relations", [])) if s]
    if relation_lines:
        blocks.append(" ".join(relation_lines) + ".")
    if unknown_names:
        blocks.append("Не установлено: " + ", ".join(unknown_names) + ".")
    parts.extend(blocks)
    return " ".join(p for p in parts if p)


def to_llm_brief(entity: dict, scope: dict | None = None) -> dict:
    """The material for an LLM (the owner's «LLM receives prepared material»).

    EDM/Resolver decides WHAT may be said (the block composition + instruction);
    the LLM only formulates it.
    """
    resolution = resolve_description(entity, scope)
    material = _material_blocks(resolution)
    identity = entity.get("identity") or {}
    return {
        "entity": (identity.get("names") or [identity.get("canonical_id") or "?"])[0],
        "entity_type": identity.get("type"),
        "scope": resolution["scope"] or {"level": "world"},
        "FACTS": material["facts"],
        "DERIVED": material["derived"],
        "RECONSTRUCTIONS": material["reconstructions"],
        "ARTISTIC_CHOICES": material["artistic_choices"],
        "UNKNOWN": material["unknown"],
        "conflicts": resolution["conflicts"],
        "instruction": LLM_INSTRUCTION,
    }
