"""Read-only registry for canonical external locators from existing artifacts.

The registry adapts existing Knowledge Card artifacts to the M2
``external:<source_id>:<locator>`` provider contract. It does not persist or
mutate claims, evidence, WorldModel, or source files.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from evidence.resolver import ExternalLocatorSource


_ARTIFACTS = (
    ("ARCHAEOLOGY.json", "archaeology"),
    ("ACADEMIC_CONFIRMATIONS.json", "academic"),
)


def _slug(value: str) -> str:
    import re

    return re.sub(r"[^a-zA-Z0-9а-яА-Я]+", "_", str(value or "").strip().lower()).strip("_") or "unknown"


def canonical_external_locator(source_ref: str) -> str | None:
    """Convert only known Knowledge Card artifact refs to M2 locators."""
    ref = str(source_ref or "")
    for artifact, source_id in _ARTIFACTS:
        prefix = f"{artifact}:"
        if ref.startswith(prefix):
            locator = ref[len(prefix) :]
            return f"external:{source_id}:{locator}" if locator else None
    if ref.startswith("external:"):
        body = ref[len("external:") :]
        source_id, separator, locator = body.partition(":")
        return ref if separator and source_id and locator else None
    return None


def _versioned(path: Path) -> tuple[str, str]:
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    return f"{path.name}@{digest[:12]}", digest


def _add(fragments: dict[str, dict[str, Any]], locator: str, text: Any, version: str, digest: str) -> None:
    if not text:
        return
    fragments[locator] = {
        "text": str(text),
        "source_version": version,
        "content_hash": digest,
    }


def _register_archaeology(path: Path, fragments: dict[str, dict[str, Any]]) -> None:
    version, digest = _versioned(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    for site in data.get("sites", []) if isinstance(data, dict) else []:
        if not isinstance(site, dict):
            continue
        site_id = str(site.get("id") or _slug(site.get("name", "site")))
        for field in ("location", "dating"):
            _add(fragments, f"external:archaeology:{site_id}:{field}", site.get(field), version, digest)
        facts = site.get("facts", {})
        if isinstance(facts, dict):
            for key, value in facts.items():
                text = ", ".join(str(item) for item in value) if isinstance(value, (list, tuple, set)) else value
                _add(fragments, f"external:archaeology:{site_id}:facts.{key}", text, version, digest)
        connection = site.get("book_connection")
        if isinstance(connection, dict):
            _add(fragments, f"external:archaeology:{site_id}:book_connection", connection.get("text"), version, digest)
        for index, hypothesis in enumerate(site.get("hypothetical_claims", [])):
            if isinstance(hypothesis, dict):
                _add(fragments, f"external:archaeology:{site_id}:hypothetical.{index}", hypothesis.get("text"), version, digest)
        significance = site.get("significance")
        if isinstance(significance, dict):
            _add(fragments, f"external:archaeology:{site_id}:significance", significance.get("text"), version, digest)


def _register_academic(path: Path, fragments: dict[str, dict[str, Any]]) -> None:
    version, digest = _versioned(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    for confirmation in data.get("confirmations", []) if isinstance(data, dict) else []:
        if not isinstance(confirmation, dict):
            continue
        title = str(confirmation.get("category") or "academic")
        base = f"external:academic:{_slug(title)}"
        for index, source in enumerate(confirmation.get("academic_sources", [])):
            if isinstance(source, dict):
                text = f"{source.get('culture', 'Источник')}: {source.get('text', '')}"
                _add(fragments, f"{base}:source.{index}", text, version, digest)


def build_external_locator_source(knowledge_dir: Path) -> ExternalLocatorSource:
    """Build the read-only provider source from existing artifacts."""
    fragments: dict[str, dict[str, Any]] = {}
    for artifact, register in (
        ("ARCHAEOLOGY.json", _register_archaeology),
        ("ACADEMIC_CONFIRMATIONS.json", _register_academic),
    ):
        path = knowledge_dir / artifact
        if not path.is_file():
            continue
        try:
            register(path, fragments)
        except (OSError, ValueError, TypeError):
            continue
    return ExternalLocatorSource(fragments=fragments)


__all__ = ["build_external_locator_source", "canonical_external_locator"]