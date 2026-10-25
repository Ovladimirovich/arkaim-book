# -*- coding: utf-8 -*-
"""EDM → VisualContext feed (EDM-RES pilot, MediaPlan seam).

Owner contract (25.10.2026): the Entity Description Model feeds the
canonical Scene Context (VisualContext) so a MediaPlan is built from
PROVENANCE-LABELLED values instead of fail-open defaults.

Purity:
- operates on plain entity dicts + an injected resolver (same shape as
  ``resolutions.resolve_description(entity, scope)``) — no file imports,
  no production-code dependency (the runtime service loads this module
  by path, see runtime/core/services/edm_pilot.py);
- input entities are NEVER mutated (the resolver is pure; this module
  only reads its output) — the World Model layer stays untouched;
- only EXISTING VisualContext fields are filled (the frozen 15-dimension
  contract): unknown claim → explicit "UNKNOWN" sentinel for environment
  fields (fail-open guard: never a default like "clear"); claims without
  a ctx target are recorded, never guessed;
- layer isolation: resolving at world scope does NOT see scene/
  media_plan-scoped claims; task-scoped fills are visible ONLY when
  `scene_overrides` passes the matching scope id.

Report (returned by :func:`apply_edm`) — machine-readable provenance for
the route's `edm` response block:

    {
      "applied": bool,          # something actually landed on ctx
      "entity_ids": [...],
      "scope": {...},
      "fields": [{field, value, status, medium, provenance_class,
                  confidence, entity}],
      "unknown_fields": [{field, entity}],
      "medium_fields": [{field, value, scope, entity}],
      "skipped_paths": [{path, entity}],
    }
"""

from __future__ import annotations

# Explicit UNKNOWN boundary sentinel (matches projections.to_mediaplan_fragment).
UNKNOWN = "UNKNOWN"

# Existing ctx fields only (frozen contract — no new fields, no guessing).
_ARCH_FIELDS = {"style", "materials", "features", "age", "condition"}
_LANDSCAPE_FIELDS = {"terrain", "vegetation", "water", "sky"}
_ENV_FIELDS = {"weather", "season", "time_of_day", "temperature", "wind"}

_SCOPE_KEYS = ("era", "place", "scene", "media_plan", "frame", "time")


def _fmt(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if isinstance(value, dict):
        return ", ".join(f"{k}={v}" for k, v in value.items())
    return str(value)


def _target_field(section: str, leaf: str) -> str | None:
    """claim path "section.leaf" → VisualContext field, or None (no target)."""
    if section == "architecture" and leaf in _ARCH_FIELDS:
        return f"architecture.{leaf}"
    if section == "landscape" and leaf in _LANDSCAPE_FIELDS:
        return f"landscape.{leaf}"
    if section == "environment" and leaf in _ENV_FIELDS:
        return f"environment.{leaf}"
    return None

def _apply_architecture(ctx, leaf: str, value: str) -> None:
    setattr(ctx.architecture, leaf, value)
    setattr(ctx.location.architecture, leaf, value)


def _apply_landscape(ctx, leaf: str, value: str) -> None:
    setattr(ctx.landscape, leaf, value)
    setattr(ctx.location.landscape, leaf, value)


def apply_edm(
    ctx,
    entities: list[dict],
    resolver,
    scene_overrides: dict | None = None,
) -> dict:
    """Apply resolved EDM claims to a canonical Scene Context (in-place).

    `resolver` — ``(entity, scope) -> resolution`` (resolutions.resolve_description).
    `scene_overrides` — task-scope ids ({"media_plan": "mp_1"} / {"scene": ...}):
    when given, claims scoped to that level become visible; world resolution
    (None) keeps the layer isolation guarantee.
    """
    scope: dict = {"level": "world"}
    if scene_overrides:
        for key in _SCOPE_KEYS:
            if scene_overrides.get(key):
                scope[key] = scene_overrides[key]

    report: dict = {
        "applied": False,
        "entity_ids": [str((e.get("identity") or {}).get("canonical_id")) for e in entities],
        "scope": scope,
        "fields": [],
        "unknown_fields": [],
        "medium_fields": [],
        "skipped_paths": [],
    }
    if not entities:
        return report

    for entity in entities:
        entity_id = str((entity.get("identity") or {}).get("canonical_id") or "?")
        resolution = resolver(entity, scope)
        for path, prop in resolution.get("properties", {}).items():
            eff = prop.get("effective") or {}
            status = eff.get("status")
            value = eff.get("value")
            medium = bool(eff.get("medium"))
            section, _, leaf = path.partition(".")
            target = _target_field(section, leaf)
            if target is None:
                report["skipped_paths"].append({"path": path, "entity": entity_id})
                continue
            if status in {"unknown", "not_applicable"} or (value is None and status != "known"):
                # Explicit knowledge boundary: no default (fail-open guard).
                if section == "environment":
                    setattr(ctx.environment, leaf, UNKNOWN)
                report["unknown_fields"].append({"field": target, "entity": entity_id})
                continue
            text = _fmt(value)
            if not text:
                continue
            if section == "architecture":
                _apply_architecture(ctx, leaf, text)
            elif section == "landscape":
                _apply_landscape(ctx, leaf, text)
            else:
                setattr(ctx.environment, leaf, text)
            entry = {
                "field": target,
                "value": text,
                "status": status,
                "medium": medium,
                "provenance_class": eff.get("provenance_class"),
                "confidence": eff.get("confidence"),
                "entity": entity_id,
            }
            report["fields"].append(entry)
            if medium:
                report["medium_fields"].append(
                    {"field": target, "value": text, "scope": eff.get("applies_to"), "entity": entity_id}
                )

    # Provenance link into the plan: identifiers only (no content copy).
    extras = getattr(ctx, "scene_extras", None)
    refs = getattr(extras, "source_refs", None) if extras is not None else None
    if refs is not None:
        for eid in report["entity_ids"]:
            ref = f"edm:{eid}"
            if eid != "?" and ref not in refs.entity_refs:
                refs.entity_refs.append(ref)

    report["applied"] = bool(report["fields"] or report["unknown_fields"])
    return report


__all__ = ["apply_edm", "UNKNOWN"]

