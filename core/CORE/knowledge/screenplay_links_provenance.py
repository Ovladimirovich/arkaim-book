"""M10-M12: Screenplay-book link records with provenance persistence.

The M10-M12 functional route:

1. **detection** - candidates over book / screenplay / genome sources
   (`knowledge.screenplay_link_candidates`, suggest-only gate, M10);
2. **disambiguation** - owner-approved decision (M16.1 base pairs + M20.1
   pairs, or `approve_link` for confirmed candidates);
3. **saving** - each record gets mandatory `_provenance_metadata`;
4. **re-reading** - verified via `ScreenplayBookLinker` (4-field contract
   + optional `provenance`) / `KnowledgeCardBuilder`.

The core of each record keeps the original 4 fields
(`screenplay_scene_id`, `book_chunk_id`, `confidence`, `notes`) - the
read-only contract of `screenplay_linker.py` is untouched. Audit fields go
under `_provenance_metadata`, so no existing consumer changes.

Single write path and data preservation:

- `save_screenplay_links` is the ONLY writer of the link file. It merges the
  input records with the on-disk registry, so owner `notes` and provenance
  metadata are never destroyed by regeneration.
- Base-pair metadata is deterministic (derivable from the pair itself), so
  `repair_provenance` / the `--repair` CLI self-heal a registry that was
  reverted to the plain 4-field format (e.g. by an external `git checkout`
  of the data file): provenance and notes are re-attached/kept without loss.
- `approve_link` persists owner-confirmed links (M10-M12 save step) after
  validating identifiers against the real source-of-truth data and the
  whole merged registry; the write is atomic.

`scripts/generate_screenplay_links.py` exposes the CLI: `--repair`,
`--candidates [SCENE...]` (suggest-only), `--approve S C`, `--out PATH`.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping

# core/KNOWLEDGE - the same location as screenplay_linker.SCREENPLAY_LINKS_PATH.
REPO_ROOT = Path(__file__).resolve().parents[3]
KNOWLEDGE_DIR = REPO_ROOT / "core" / "KNOWLEDGE"
SCREENPLAY_LINKS_PATH = KNOWLEDGE_DIR / "screenplay_links.json"

# Source-of-truth files referenced by the registry and by candidate detection.
SYNOPSIS_DOCUMENT_REL = "core/KNOWLEDGE/SYNOPSIS_DOCUMENT.json"
ENRICHED_CHUNKS_REL = "core/KNOWLEDGE/enriched_chunks.json"


# Files cited by a serialized link record (the trail of evidence).
LINK_EVIDENCE_FILES = (
    "core/KNOWLEDGE/PLOT.json",
    "core/KNOWLEDGE/SCENE_PROMPTS.json",
    "core/KNOWLEDGE/screenplay_extracts.json",
    "core/KNOWLEDGE/screenplay_links.json",
)

# Owner-approved pairs (M16.1 base set). Same content as
# tests/test_m16_1_screenplay_links.py::APPROVED_PAIRS (base part).
M16_1_APPROVED_PAIRS: frozenset[tuple[str, str]] = frozenset(
    {
        ("scene_003", "chunk_p_0006_104f39f72f26"),
        ("scene_006", "chunk_p_0010_77326a31efd2"),
        ("scene_014", "chunk_p_0027_4c6873e98b66"),
        ("scene_019", "chunk_p_0043_a5a83219bbd8"),
        ("scene_020", "chunk_p_0046_407df13f675f"),
        ("scene_021", "chunk_p_0047_387817db08e3"),
        ("scene_022", "chunk_p_0048_bbe88490fb62"),
        ("scene_027", "chunk_p_0049_9d39268ad94c"),
        ("scene_047", "chunk_p_0102_1d2e617e135e"),
    }
)

# Owner-approved pairs (M20.1). Same content as
# tests/test_m20_1_screenplay_links.py::M20_1_APPROVED_PAIRS.
M20_1_APPROVED_PAIRS: frozenset[tuple[str, str]] = frozenset(
    {
        ("scene_004", "chunk_p_0007_b812dfae0ff4"),
        ("scene_009", "chunk_p_0018_89a09e6d3d55"),
        ("scene_020", "chunk_p_0045_bc4a72fed70b"),
        ("scene_086", "chunk_p_0570_e94101594d2f"),
        ("scene_117", "chunk_p_0799_57e67fec2309"),
    }
)

# All owner-approved pairs (M16.1 + M20.1). The registry invariant is a
# unique (scene, chunk) pair — one scene may have several confirmed links
# (M20.1: scene_020 has both chunk_p_0045 and chunk_p_0046).
APPROVED_PAIRS: frozenset[tuple[str, str]] = M16_1_APPROVED_PAIRS | M20_1_APPROVED_PAIRS

SCENE_ID_RE = re.compile(r"^scene_\d{3}$")
CHUNK_ID_RE = re.compile(r"^chunk_p_\d{4}_[0-9a-f]{12}$")
EVIDENCE_REF_RE = re.compile(r"^book:chunk_p_\d{4}_[0-9a-f]{12}$")
SCENE_REF_RE = re.compile(r"^screenplay:scene:scene_\d{3}$")

ENRICHED_AT = "Milestone B"
RESOLVED_AT = "2026-10-13T00:00:00Z"
RESOLVED_BY = (
    "M16.1 owner-approved pairs (tests/test_m16_1_screenplay_links.APPROVED_PAIRS)"
)
RESOLVED_BY_M20_1 = "M20.1 owner-approved pairs (tests/test_m20_1_screenplay_links.py::M20_1_APPROVED_PAIRS)"


def load_existing_records(
    path: Path = SCREENPLAY_LINKS_PATH,
) -> dict[tuple[str, str], dict]:
    """Load the current link file, keyed by (scene, chunk) pair, keeping original quotes."""
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    by_pair: dict[tuple[str, str], dict] = {}
    for item in data:
        if isinstance(item, dict) and item.get("screenplay_scene_id"):
            scene_id = str(item["screenplay_scene_id"])
            chunk_id = str(item.get("book_chunk_id") or "")
            by_pair[(scene_id, chunk_id)] = item
    return by_pair


def merge_records(
    new_records: Iterable[dict], existing: Mapping[tuple[str, str], dict]
) -> list[dict]:
    """Merge input records with the on-disk registry; nothing is ever lost.

    - Every on-disk record survives (notes and ``_provenance_metadata`` included).
    - An input record updates the 4 core fields of its (scene, chunk) pair but
      an empty ``notes`` never clobbers an existing owner justification.
    - Approved-pair records (``APPROVED_PAIRS``) missing metadata get it
      re-attached deterministically; confirmed extra records keep theirs.
    - Unconfirmed records lacking metadata are kept but stay flagged by
      ``validate_screenplay_links`` (no provenance is invented for them).
    """
    merged: dict[tuple[str, str], dict] = {
        pair: dict(rec) for pair, rec in dict(existing).items()
    }
    for record in new_records:
        if not isinstance(record, Mapping):
            continue
        scene_id = str(record.get("screenplay_scene_id") or "")
        if not scene_id:
            continue
        chunk_id = str(record.get("book_chunk_id") or "")
        pair = (scene_id, chunk_id)
        prior = merged.get(pair, {})
        out: dict = dict(record)
        out.setdefault("confidence", prior.get("confidence", 1.0))
        if (
            not str(out.get("notes") or "").strip()
            and str(prior.get("notes") or "").strip()
        ):
            out["notes"] = prior["notes"]
        if not isinstance(out.get("_provenance_metadata"), dict):
            if pair in APPROVED_PAIRS:
                out["_provenance_metadata"] = _provenance_metadata_for(
                    scene_id, chunk_id
                )
            elif isinstance(prior.get("_provenance_metadata"), dict):
                out["_provenance_metadata"] = dict(prior["_provenance_metadata"])
        merged[pair] = out
    # Final pass: approved-pair metadata is deterministic — re-attach it to ANY
    # merged record that lost it (repair after an external revert, or a save
    # into a bare 4-field file). Extra (owner-confirmed) records keep theirs.
    for pair, rec in merged.items():
        if pair in APPROVED_PAIRS and not isinstance(
            rec.get("_provenance_metadata"), dict
        ):
            rec["_provenance_metadata"] = _provenance_metadata_for(pair[0], pair[1])
    return [dict(merged[pair]) for pair in sorted(merged)]


def _atomic_write(payload: list[dict], path: Path) -> Path:
    """Write the payload atomically (``.tmp`` + ``os.replace``)."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(tmp, path)
    return path


def repair_provenance(path: Path = SCREENPLAY_LINKS_PATH) -> int:
    """Re-attach lost metadata (self-heal after an external revert).

    Deterministic case: a plain 4-field registry (e.g. restored from an
    old git revision) is re-enriched for the base pairs; owner notes are
    kept. Unconfirmed extra records are not re-enriched (nothing to
    re-attach) — they stay flagged by the validator. Returns the number
    of repaired records; the file is rewritten only when something
    changed.
    """
    existing = load_existing_records(path)
    payload = merge_records([], existing)
    # Count repaired as "had no metadata before the merge":
    before = {pair: rec.get("_provenance_metadata") for pair, rec in existing.items()}
    repaired = sum(
        1
        for record in payload
        if (
            str(record.get("screenplay_scene_id") or ""),
            str(record.get("book_chunk_id") or ""),
        )
        in APPROVED_PAIRS
        and not isinstance(
            before.get(
                (
                    str(record.get("screenplay_scene_id") or ""),
                    str(record.get("book_chunk_id") or ""),
                )
            ),
            dict,
        )
        and isinstance(record.get("_provenance_metadata"), dict)
    )
    if repaired:
        _atomic_write(payload, path)
    return repaired


def _approved_link_metadata(
    scene_id: str, chunk_id: str, resolved_by: str, resolved_at: str
) -> dict:
    """Audit fields of an owner-confirmed (M10-M12) link record."""
    return {
        "category": "AUTHOR_CANON",
        "source_level": "CANON",
        "source_title": "Screenplay",
        "evidence_ref": f"book:{chunk_id}",
        "screenplay_ref": f"screenplay:scene:{scene_id}",
        "evidence_files": list(LINK_EVIDENCE_FILES)
        + [SYNOPSIS_DOCUMENT_REL, ENRICHED_CHUNKS_REL],
        "resolved_by": resolved_by,
        "resolved_at": resolved_at,
        "confidence": 1.0,
        "enriched_at": ENRICHED_AT,
    }


def _validate_identifiers(scene_id: str, chunk_id: str) -> None:
    """Id formats + existence in the real source-of-truth data (no fabricated links)."""
    if not SCENE_ID_RE.match(scene_id):
        raise ValueError(
            f"screenplay_scene_id={scene_id!r} не соответствует формату scene_###"
        )
    if not CHUNK_ID_RE.match(chunk_id):
        raise ValueError(
            f"book_chunk_id={chunk_id!r} не соответствует формату chunk_p_####_<12hex>"
        )
    from knowledge.screenplay_link_candidates import valid_chunk_ids, valid_scene_ids

    if scene_id not in valid_scene_ids():
        raise ValueError(
            f"scene_id {scene_id!r} отсутствует в нормативном источнике сцен (SYNOPSIS_DOCUMENT.json)"
        )
    if chunk_id not in valid_chunk_ids():
        raise ValueError(
            f"chunk_id {chunk_id!r} отсутствует в книжном реестре фрагментов (enriched_chunks.json)"
        )


def approve_link(
    scene_id: str,
    chunk_id: str,
    notes: str = "",
    resolved_by: str = "",
    resolved_at: str = "",
    path: Path = SCREENPLAY_LINKS_PATH,
) -> dict:
    """Owner confirmation path (M10-M12): persist a confirmed link with provenance.

    Guards: scene/chunk formats, both identifiers exist in the real data,
    the (scene, chunk) pair is not linked yet (a scene may hold several
    confirmed links — M20.1). The merged payload is validated BEFORE the
    atomic write, so the registry can never end up broken.
    Returns the persisted record.
    """
    _validate_identifiers(scene_id, chunk_id)
    existing = load_existing_records(path)
    prior = existing.get((scene_id, chunk_id))
    if prior is not None:
        raise ValueError(
            f"сцена {scene_id!r} уже имеет подтверждённую связь "
            f"с {chunk_id!r}; повторное подтверждение требует решения владельца"
        )
    notes = (
        notes
        or "Подтверждённая OWNER-связь M10-M12 (текстовое соответствие, не идентичность событий)"
    ).strip()
    resolved_by = resolved_by or f"M10-M12 owner confirmation ({scene_id} → {chunk_id})"
    resolved_at = resolved_at or datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    record: dict = {
        "screenplay_scene_id": scene_id,
        "book_chunk_id": chunk_id,
        "confidence": 1.0,
        "notes": notes,
    }
    record["_provenance_metadata"] = _approved_link_metadata(
        scene_id, chunk_id, resolved_by, resolved_at
    )
    payload = merge_records([record], existing)
    errors = validate_screenplay_links(payload)
    if errors:
        raise ValueError("валидация слияния не прошла: " + "; ".join(errors))
    _atomic_write(payload, path)
    return record


def _provenance_metadata_for(scene_id: str, chunk_id: str) -> dict:
    """Audit fields of a single link record (M16.3, Milestone B)."""
    if (scene_id, chunk_id) in M20_1_APPROVED_PAIRS:
        resolved_by = RESOLVED_BY_M20_1
    else:
        resolved_by = RESOLVED_BY
    return {
        "category": "AUTHOR_CANON",
        "source_level": "CANON",
        "source_title": "Screenplay",
        "evidence_ref": f"book:{chunk_id}",
        "screenplay_ref": f"screenplay:scene:{scene_id}",
        "evidence_files": list(LINK_EVIDENCE_FILES),
        "resolved_by": resolved_by,
        "resolved_at": RESOLVED_AT,
        "confidence": 1.0,
        "enriched_at": ENRICHED_AT,
    }


def build_approved_link_records(
    approved_pairs: Iterable[tuple[str, str]] = APPROVED_PAIRS,
    existing: Mapping[tuple[str, str], dict] | None = None,
) -> list[dict]:
    """Approved-pair records: core 4 fields + nested _provenance_metadata.

    `notes` are preserved from the currently persisted file, so the
    owner-approved justifications survive regeneration.
    """
    by_pair = load_existing_records() if existing is None else dict(existing)
    records: list[dict] = []
    for scene_id, chunk_id in sorted(approved_pairs):
        record: dict = {
            "screenplay_scene_id": scene_id,
            "book_chunk_id": chunk_id,
            "confidence": 1.0,
            "notes": str(by_pair.get((scene_id, chunk_id), {}).get("notes", "")),
        }
        record["_provenance_metadata"] = _provenance_metadata_for(scene_id, chunk_id)
        records.append(record)
    return records


def validate_screenplay_links(data: object) -> list[str]:
    """Validate a parsed JSON document. Returns a list of errors (empty = OK)."""
    errors: list[str] = []
    if not isinstance(data, list):
        return ["screenplay_links.json must be a JSON array"]

    for idx, item in enumerate(data):
        where = f"item[{idx}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: not an object")
            continue
        scene_id = item.get("screenplay_scene_id")
        chunk_id = item.get("book_chunk_id")
        if not SCENE_ID_RE.match(str(scene_id or "")):
            errors.append(
                f"{where}.screenplay_scene_id={scene_id!r}, expected scene_###"
            )
        if not CHUNK_ID_RE.match(str(chunk_id or "")):
            errors.append(
                f"{where}.book_chunk_id={chunk_id!r}, expected chunk_p_####_<12hex>"
            )
        notes = item.get("notes")
        if not isinstance(notes, str) or not notes.strip():
            errors.append(f"{where}.notes missing or empty")
        meta = item.get("_provenance_metadata")
        if not isinstance(meta, dict):
            errors.append(f"{where}: _provenance_metadata missing or not a dict")
            continue
        for key in (
            "category",
            "source_level",
            "evidence_ref",
            "screenplay_ref",
            "evidence_files",
            "resolved_by",
            "resolved_at",
            "confidence",
            "enriched_at",
        ):
            if key not in meta:
                errors.append(f"{where}._provenance_metadata missing key: {key}")
        if meta.get("category") != "AUTHOR_CANON":
            errors.append(
                f"{where}._provenance_metadata.category={meta.get('category')!r}, expected AUTHOR_CANON"
            )
        if meta.get("source_level") != "CANON":
            errors.append(
                f"{where}._provenance_metadata.source_level={meta.get('source_level')!r}, expected CANON"
            )
        if meta.get("confidence") != 1.0:
            errors.append(
                f"{where}._provenance_metadata.confidence={meta.get('confidence')!r}, expected 1.0"
            )
        if meta.get("enriched_at") != ENRICHED_AT:
            errors.append(
                f"{where}._provenance_metadata.enriched_at={meta.get('enriched_at')!r}, expected {ENRICHED_AT!r}"
            )
        if meta.get("evidence_ref") != f"book:{chunk_id}":
            errors.append(
                f"{where}._provenance_metadata.evidence_ref={meta.get('evidence_ref')!r}, expected book:{chunk_id}"
            )
        if meta.get("screenplay_ref") != f"screenplay:scene:{scene_id}":
            errors.append(
                f"{where}._provenance_metadata.screenplay_ref={meta.get('screenplay_ref')!r}, expected screenplay:scene:{scene_id}"
            )
        files = meta.get("evidence_files")
        if not isinstance(files, list) or not files:
            errors.append(
                f"{where}._provenance_metadata.evidence_files missing or empty"
            )
        else:
            for f in files:
                if not isinstance(f, str) or not (REPO_ROOT / f).exists():
                    errors.append(
                        f"{where}._provenance_metadata.evidence_file not found: {f!r}"
                    )

    pairs = {
        (i.get("screenplay_scene_id"), i.get("book_chunk_id"))
        for i in data
        if isinstance(i, dict)
    }
    approved = set(APPROVED_PAIRS)
    missing = approved - pairs
    if missing:
        errors.append(f"pair set differs from approved: missing={sorted(missing)}")
    # Confirmed extra records (M10-M12 approvals) are allowed ONLY with a
    # complete, valid _provenance_metadata; bare extras stay flagged.
    for extra in sorted(pairs - approved):
        record = next(
            i
            for i in data
            if isinstance(i, dict)
            and (i.get("screenplay_scene_id"), i.get("book_chunk_id")) == extra
        )
        if not isinstance(record.get("_provenance_metadata"), dict):
            errors.append(f"unapproved pair without _provenance_metadata: {extra}")
    # The registry invariant is a unique (scene, chunk) pair: one scene may
    # hold several confirmed links (M20.1: scene_020 → two chunks), but the
    # same pair must never appear twice.
    pair_list = [
        (i.get("screenplay_scene_id"), i.get("book_chunk_id"))
        for i in data
        if isinstance(i, dict)
    ]
    if len(pair_list) != len(set(pair_list)):
        errors.append("duplicate screenplay pair (screenplay_scene_id, book_chunk_id)")
    return errors


def save_screenplay_links(
    records: Iterable[dict], path: Path = SCREENPLAY_LINKS_PATH
) -> Path:
    """Atomically persist the registry: input records merged with on-disk records.

    Merge semantics (see ``merge_records``): owner notes and provenance metadata
    on disk are never lost; base-pair metadata is re-attached when missing.
    This is the single write path for ``screenplay_links.json`` — regeneration
    can no longer destroy provenance or confirmed information.
    """
    payload = merge_records(records, load_existing_records(path))
    return _atomic_write(payload, path)


def main(argv: list[str] | None = None) -> int:
    """CLI for the M10-M12 link flow. Exit code 0 = OK.

    Default mode: regenerate base pairs idempotently, merge with on-disk
    records (provenance/notes never lost), re-validate.
      --repair            re-attach lost base-pair metadata only (self-heal)
      --candidates [ID]   print top-5 candidates (suggest-only, no writes)
      --approve S C       owner confirmation: persist S→C with provenance
      --notes / --resolved-by   provenance fields for --approve
      --out PATH          alternate target path (regenerate/repair modes)
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="M10-M12 screenplay-book link flow (generate/repair/approve)"
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="alternate target path (default: the working knowledge file)",
    )
    parser.add_argument(
        "--repair",
        action="store_true",
        help="re-attach lost base-pair metadata (self-heal, no pair changes)",
    )
    parser.add_argument(
        "--candidates",
        nargs="*",
        default=None,
        metavar="SCENE_ID",
        help="print top-5 candidates (suggest-only, no writes)",
    )
    parser.add_argument(
        "--approve",
        nargs=2,
        default=None,
        metavar=("SCENE_ID", "CHUNK_ID"),
        help="owner confirmation of a candidate link",
    )
    parser.add_argument("--notes", default="", help="owner justification for --approve")
    parser.add_argument(
        "--resolved-by", default="", help="provenance author for --approve"
    )
    args = parser.parse_args(argv)

    if args.candidates is not None:
        from knowledge.screenplay_link_candidates import candidates_for_scene

        if not args.candidates:
            print("pass scene ids: --candidates scene_000 scene_005 ...")
            return 0
        for scene_id in args.candidates:
            found = candidates_for_scene(scene_id, top_k=5)
            print(f"candidates for {scene_id} (suggest-only, {len(found)}):")
            for cand in found:
                print(f"  {cand.to_dict()}")
        return 0

    target = args.out or SCREENPLAY_LINKS_PATH

    if args.approve:
        scene_id, chunk_id = args.approve
        record = approve_link(
            scene_id,
            chunk_id,
            notes=args.notes,
            resolved_by=args.resolved_by,
            path=target,
        )
        print(f"approved        : {scene_id} → {chunk_id}")
        print(f"resolved_by     : {record['_provenance_metadata']['resolved_by']}")
        data = json.loads(target.read_text(encoding="utf-8"))
        errs = validate_screenplay_links(data)
        print(f"validation      : {'OK' if not errs else 'FAILED'}")
        for e in errs:
            print("  -", e)
        print(f"path            : {target}")
        return 0 if not errs else 1

    if args.repair:
        repair_target = target if target.exists() else SCREENPLAY_LINKS_PATH
        repaired = repair_provenance(repair_target)
        print(f"records repaired: {repaired} (base-pair metadata re-attached)")
        data = json.loads(repair_target.read_text(encoding="utf-8"))
        errs = validate_screenplay_links(data)
        print(f"validation      : {'OK' if not errs else 'FAILED'}")
        for e in errs:
            print("  -", e)
        print(f"path            : {repair_target}")
        return 0 if not errs else 1

    existing = load_existing_records()
    records = build_approved_link_records(existing=existing)
    save_screenplay_links(records, target)

    data = json.loads(target.read_text(encoding="utf-8"))
    errs = validate_screenplay_links(data)
    print(f"records written : {len(data)} (approved pairs: {len(APPROVED_PAIRS)})")
    print(f"validation      : {'OK' if not errs else 'FAILED'}")
    for e in errs:
        print("  -", e)
    print(f"path            : {target}")
    return 0 if not errs else 1


if __name__ == "__main__":
    raise SystemExit(main())
