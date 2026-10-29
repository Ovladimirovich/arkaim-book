#!/usr/bin/env python3
"""Fill provenance for 6 CANON epochs and 6 CANON locations with AUTHOR_CANON.

This script updates the existing WORLD_MODEL.json in place, adding provenance
entries for entities that have source_level='CANON' but empty provenance arrays.

Run from project root: python scripts/fill_provenance.py
"""

import json
from pathlib import Path
from datetime import datetime, timezone

WM_PATH = Path("core/CORE/narrative_engine/data/WORLD_MODEL.json")

# Mapping of epoch_id -> provenance notes
EPOCH_PROVENANCE = {
    "кали_юга_и_сати_юга": {
        "notes": "Книга: упоминание циклов Юг и Сати Юги как фундаментальной хронологии",
        "confidence": 1.0,
    },
    "переходная_эпоха": {
        "notes": "Книга: описание времени смены эпох, совпадающего с космическими сроками (части 1-3)",
        "confidence": 1.0,
    },
    "эволюция_человека": {
        "notes": "Книга: процесс развития цивилизаций через смену эпох и культур (центральная тема)",
        "confidence": 1.0,
    },
    "кали_юга": {
        "notes": "Книга: тёмная эпоха после завершения культурных циклов (части 13-14, эпилог)",
        "confidence": 1.0,
    },
    "переход_к_новой_эре_(кали_юга)": {
        "notes": "Книга: описание планетарных изменений и перехода к новому этапу эволюции (части 13-16)",
        "confidence": 1.0,
    },
    "эпоха_кали_юги": {
        "notes": "Книга: период глубокого духовного упадка и блокады сознания (части 13-14)",
        "confidence": 1.0,
    },
}

# Mapping of location_id -> provenance notes
LOCATION_PROVENANCE = {
    "гиперборея": {
        "notes": "Книга: северная прародина, хранящая духовные истины (упоминается в частях 1-5, 10-11)",
        "confidence": 1.0,
    },
    "океания": {
        "notes": "Книга: древняя островная цивилизация, прародина Велика, переживающая упадок (части 3-4)",
        "confidence": 1.0,
    },
    "аркаим": {
        "notes": "Книга: священное место, центр духовного знания, основанное Наставниками (части 10-11)",
        "confidence": 1.0,
    },
    "tmutarakan": {
        "notes": "Книга: древний город на берегу моря, упомянутый в историческом контексте",
        "confidence": 1.0,
    },
    "sumer": {
        "notes": "Книга: колыбель цивилизации, упоминаемая в контексте ведической традиции",
        "confidence": 1.0,
    },
    "india": {
        "notes": "Книга: земля древних риши и ведической традиции, источник знания о Югах",
        "confidence": 1.0,
    },
}


def make_provenance_entry(notes: str, confidence: float) -> dict:
    """Create a standard AUTHOR_CANON provenance entry."""
    return {
        "source_level": "CANON",
        "category": "AUTHOR_CANON",
        "confidence": confidence,
        "notes": notes,
    }


def main():
    if not WM_PATH.exists():
        print(f"ERROR: {WM_PATH} not found")
        return 1

    # Backup
    backup_path = WM_PATH.with_suffix(
        f".json.backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    )
    WM_PATH.rename(backup_path)
    print(f"Backup created: {backup_path}")

    # Load
    with open(backup_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    updated_epochs = 0
    updated_locations = 0

    # Update epochs
    for epoch in data.get("epochs", []):
        eid = epoch.get("id")
        if (
            epoch.get("source_level") == "CANON"
            and not epoch.get("provenance")
            and eid in EPOCH_PROVENANCE
        ):
            prov = EPOCH_PROVENANCE[eid]
            epoch["provenance"] = [
                make_provenance_entry(prov["notes"], prov["confidence"])
            ]
            updated_epochs += 1
            print(f"  Updated epoch: {eid}")

    # Update locations
    for loc in data.get("locations", []):
        lid = loc.get("id")
        if (
            loc.get("source_level") == "CANON"
            and not loc.get("provenance")
            and lid in LOCATION_PROVENANCE
        ):
            prov = LOCATION_PROVENANCE[lid]
            loc["provenance"] = [
                make_provenance_entry(prov["notes"], prov["confidence"])
            ]
            updated_locations += 1
            print(f"  Updated location: {lid}")

    # Update updated_at
    data["updated_at"] = datetime.now(tz=timezone.utc).isoformat()

    # Save
    WM_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDone! Updated {updated_epochs} epochs, {updated_locations} locations.")
    print(f"Saved to: {WM_PATH}")

    # Verify
    with open(WM_PATH, "r", encoding="utf-8") as f:
        verify = json.load(f)

    canon_epochs_empty = sum(
        1
        for e in verify["epochs"]
        if e.get("source_level") == "CANON" and not e.get("provenance")
    )
    canon_locs_empty = sum(
        1
        for l in verify["locations"]
        if l.get("source_level") == "CANON" and not l.get("provenance")
    )
    print(
        f"\nVerification: {canon_epochs_empty} CANON epochs still empty, {canon_locs_empty} CANON locations still empty"
    )

    return 0


if __name__ == "__main__":
    exit(main())
