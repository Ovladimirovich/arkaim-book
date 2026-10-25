# -*- coding: utf-8 -*-
"""EDM operations: DERIVE / RECONSTRUCT / ARTISTIC_FILL / FICTION (EDM-RES).

Owner contract (25.10.2026): knowledge contract + four operations.

IMPORT      — already covered by loader.py (ext model -> EDM, CANON/EXTERNAL
              and existing provenance preserved).
DERIVE      — known facts -> logical inference            (status=inferred)
RECONSTRUCT — known facts + time + external knowledge      (status=reconstructed, medium)
ARTISTIC_FILL — known facts + world constraints + task of
                visualization                               (status=artistic_model, medium, scoped)
FICTION     — out-of-canon story value                     (status=fiction, medium, scoped)

Invariants:
- every operation is PURE: returns a NEW entity dict (deep copy); the input
  entity and its claims are NEVER modified;
- ARTISTIC_FILL and FICTION never write over knowledge: they add an additional
  scoped claim, while the original fact (e.g. weather=UNKNOWN) stays in place
  and stays the winner for the World Model scope;
- an artistic/fiction value never raises its own status to `known` and is
  valid only inside `applies_to` (scope: world/era/place/scene/media_plan/frame);
- DERIVE and RECONSTRUCT record `created_from` — the fact base of the value.
"""

from __future__ import annotations

import copy

SCOPES = ("world", "era", "place", "scene", "media_plan", "frame")


class EdmConflict(ValueError):
    """A new value contradicts an existing non-medium (fact) claim on the same path."""


def scope(level: str, id: str | None = None, temporal_ref: str | None = None) -> dict:
    """Build an `applies_to` block. A non-world level requires an id."""
    if level not in SCOPES:
        raise ValueError(f"unknown scope level {level!r}; expected one of {SCOPES}")
    if level != "world" and id is None:
        raise ValueError(f"scope level {level!r} requires an id")
    block: dict = {"level": level}
    if id is not None:
        block["id"] = id
    if temporal_ref is not None:
        block["temporal_ref"] = temporal_ref
    return block


def _claims(entity: dict) -> list[dict]:
    return entity.get("claims", [])


def _existing_fact_values(entity: dict, path: str) -> list[tuple[dict, object]]:
    """Non-medium claims with a concrete value on the path (the fact layer)."""
    out = []
    for c in _claims(entity):
        if c.get("path") != path or c.get("medium"):
            continue
        if c.get("value") is not None and c.get("status") not in {"unknown", "not_applicable"}:
            out.append((c, c.get("value")))
    return out


def _is_duplicate(claims: list[dict], path: str, status: str, applies_to: dict | None, value) -> bool:
    level = (applies_to or {}).get("level", "world")
    sid = (applies_to or {}).get("id")
    for c in claims:
        if c.get("path") != path or c.get("status") != status:
            continue
        ca = c.get("applies_to") or {}
        if ca.get("level", "world") == level and ca.get("id") == sid and c.get("value") == value:
            return True
    return False


def _add(
    entity: dict,
    path: str,
    value,
    status: str,
    pclass: str,
    medium: bool,
    confidence,
    applies_to: dict | None,
    created_from: list[str] | None,
    source_ref: dict | None,
    note: str | None,
) -> dict:
    out = copy.deepcopy(entity)
    claims = out.setdefault("claims", [])
    if _is_duplicate(claims, path, status, applies_to, value):
        return out  # idempotent: the same value at the same status+scope is stored once
    claim: dict = {"path": path, "value": value, "status": status, "provenance_class": pclass, "medium": medium}
    if source_ref is not None:
        claim["source_ref"] = source_ref
    claim["confidence"] = confidence
    if applies_to is not None:
        claim["applies_to"] = applies_to
    if created_from:
        claim["created_from"] = list(created_from)
    if note:
        claim["note"] = note
    claims.append(claim)
    return out


def derive(entity: dict, path: str, value, created_from: list[str], confidence: float = 0.5, note: str | None = None) -> dict:
    """DERIVE: a logical inference from known facts (status=inferred).

    `created_from` is mandatory — it is the fact base of the inference
    (the EDM-RES contract). The inference must not contradict a known fact
    on the same path (raises :class:`EdmConflict`); it may replace UNKNOWN.
    """
    if not created_from:
        raise ValueError("DERIVE requires created_from: the facts the inference is based on")
    for _c, fact_value in _existing_fact_values(entity, path):
        if fact_value != value:
            raise EdmConflict(
                f"DERIVE {path!r}={value!r} contradicts existing fact {fact_value!r} — "
                "a logical inference cannot contradict a known value"
            )
    return _add(
        entity,
        path,
        value,
        status="inferred",
        pclass="derived",
        medium=False,
        confidence=confidence,
        applies_to=None,
        created_from=list(created_from),
        source_ref={"layer": "none", "ref": f"derived:{path}", "path": path},
        note=note,
    )


def reconstruct(
    entity: dict,
    path: str,
    value,
    created_from: list[str] | None = None,
    confidence: float = 0.4,
    external_ref: dict | None = None,
    note: str | None = None,
) -> dict:
    """RECONSTRUCT: known facts + time + external knowledge (status=reconstructed, medium).

    Always carries `medium=true` and (if external knowledge is used) `created_from`.
    """
    source_ref = external_ref or {"layer": "reconstruction", "ref": f"reconstruction:{path}", "path": path}
    return _add(
        entity,
        path,
        value,
        status="reconstructed",
        pclass="reconstruction",
        medium=True,
        confidence=confidence,
        applies_to=None,
        created_from=created_from,
        source_ref=source_ref,
        note=note,
    )


def artistic_fill(
    entity: dict,
    path: str,
    value,
    scope_level: str = "media_plan",
    scope_id: str | None = None,
    confidence: float = 0.5,
    created_from: list[str] | None = None,
    temporal_ref: str | None = None,
    note: str | None = None,
) -> dict:
    """ARTISTIC FILL: a concrete visual choice for a task (status=artistic_model, medium, scoped).

    The value acts ONLY inside `applies_to` (e.g. media_plan mp_1) and never
    overwrites the original fact: the World Model view keeps the original
    claim (typically `unknown`).
    """
    if value is None:
        raise ValueError("ARTISTIC_FILL stores a concrete choice; an unknown boundary stays `unknown`")
    applies_to = scope(scope_level, scope_id, temporal_ref)
    if created_from and note is None:
        note = f"artistic fill @ {applies_to.get('level')}:{applies_to.get('id')}"
    return _add(
        entity,
        path,
        value,
        status="artistic_model",
        pclass="artistic_model",
        medium=True,
        confidence=confidence,
        applies_to=applies_to,
        created_from=created_from,
        source_ref=None,
        note=note,
    )


def fiction(
    entity: dict,
    path: str,
    value,
    scope_level: str = "scene",
    scope_id: str | None = None,
    confidence: float = 0.5,
    created_from: list[str] | None = None,
    temporal_ref: str | None = None,
    note: str | None = None,
) -> dict:
    """FICTION: an out-of-canon story value (status=fiction, medium, scoped).

    Lower priority than artistic_model in the resolver: fiction is for
    narrative tasks, not for world descriptions.
    """
    if value is None:
        raise ValueError("FICTION stores a concrete value; an unknown boundary stays `unknown`")
    applies_to = scope(scope_level, scope_id, temporal_ref)
    return _add(
        entity,
        path,
        value,
        status="fiction",
        pclass="fiction",
        medium=True,
        confidence=confidence,
        applies_to=applies_to,
        created_from=created_from,
        source_ref=None,
        note=note,
    )
