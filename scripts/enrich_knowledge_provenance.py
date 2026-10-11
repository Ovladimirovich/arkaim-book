"""Enrich KNOWLEDGE JSON files with _provenance_metadata.

Classification rules:
- AUTHOR_CANON: Direct from КНИГА.md or GENOME (BOOK_DOCUMENT, SYNOPSIS_DOCUMENT, AUTHOR_INTENT)
- DERIVED: Extracted from GENOME or derived concepts (PHILOSOPHY, CHARACTERS, SYMBOLS, etc.)
- EXTERNAL_SOURCE: External academic/archaeological references (ACADEMIC_CONFIRMATIONS, MAP_DATA)
- HYPOTHESIS: Esoteric/speculative connections (ESOTERIC_CONNECTIONS, CROSS_REFERENCES)
- UNKNOWN: Files with empty or unclassifiable content

Usage: python scripts/enrich_knowledge_provenance.py
"""
from __future__ import annotations

import json
from pathlib import Path

# Classification rules: file_name -> (category, source, notes)
KNOWLEDGE_CLASSIFICATION: dict[str, tuple[str, str, str]] = {
    # Direct book sources — AUTHOR_CANON
    "BOOK_DOCUMENT.json": ("AUTHOR_CANON", "CANON", "Direct book text document"),
    "SYNOPSIS_DOCUMENT.json": ("AUTHOR_CANON", "CANON", "Direct synopsis from book"),
    "AUTHOR_INTENT.json": ("AUTHOR_CANON", "CANON", "Author's stated intent from КНИГА.md"),
    "SCREENPLAY_EXTRACTS.json": ("AUTHOR_CANON", "CANON", "Screenplay extracts from book"),

    # GENOME-derived — DERIVED
    "PHILOSOPHY.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Extracted from GENOME themes/concepts"),
    "PHILOSOPHY_DEEP.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Deep expansion of PHILOSOPHY from GENOME"),
    "CHARACTERS.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Character profiles extracted from GENOME"),
    "CHARACTER_PROFILES.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Canonical character profiles from GENOME"),
    "DEEP_CHARACTERS.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Deep character profiles derived from GENOME"),
    "CHARACTER_DEEP_PROFILES.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Extended character biographies from GENOME"),
    "VALUES.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Values extracted from GENOME"),
    "SYMBOLS.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Symbol meanings from GENOME"),
    "SYMBOLS_DEEP.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Deep symbol analysis from GENOME"),
    "SYMBOLS_EXPANDED.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Expanded symbols derived from GENOME"),
    "PLOT.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Plot summary derived from GENOME"),
    "CROSS_REFERENCES.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Cross-references derived from GENOME"),
    "CROSS_REFERENCES_DEEP.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Deep cross-references from GENOME"),
    "THEMES_DEEP.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Deep theme analysis from GENOME"),
    "THEMES_EXPANDED.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Expanded themes from GENOME"),
    "PATTERNS.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Structural patterns derived from GENOME"),
    "MEANING_TREE.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Meaning tree derived from GENOME"),
    "ESOTERIC_CONNECTIONS.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Esoteric connections interpreted from GENOME"),
    "HIERARCHY_OF_LIGHT.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Hierarchy derived from GENOME teachings"),
    "SPIRITUAL_TRANSFORMATION.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Spiritual concepts from GENOME"),
    "ENERGY_OF_PLACES.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Energy interpretations from GENOME"),
    "ARCHETYPES_EXPANDED.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Archetypes expanded from GENOME"),
    "QUESTIONS_FOR_READER.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Reader questions derived from GENOME"),
    "EPOCH_PALETTES.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Epoch palettes from GENOME temporal data"),
    "COSMOLOGY.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Cosmology derived from GENOME"),
    "COSMOLOGY_DEEP.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Deep cosmology from GENOME"),

    # Archaeological/external sources — EXTERNAL_SOURCE
    "ACADEMIC_CONFIRMATIONS.json": ("EXTERNAL_SOURCE", "HISTORICAL", "Academic confirmations from external sources"),
    "ARCHAEOLOGY.json": ("EXTERNAL_SOURCE", "HISTORICAL", "Archaeological facts from external sources"),
    "ARCHAEOLOGY_DEEP.json": ("EXTERNAL_SOURCE", "HISTORICAL", "Deep archaeological data from external sources"),
    "GEOGRAPHY.json": ("EXTERNAL_SOURCE", "HISTORICAL", "Geographic data from external sources"),
    "MAP_DATA.json": ("EXTERNAL_SOURCE", "HISTORICAL", "Map data from external sources"),
    "LANGUAGE.json": ("EXTERNAL_SOURCE", "HISTORICAL", "Linguistic data from external sources"),
    "TECHNOLOGY.json": ("EXTERNAL_SOURCE", "HISTORICAL", "Technological data from external sources"),
    "TRANSPORT.json": ("EXTERNAL_SOURCE", "HISTORICAL", "Transport data from external sources"),
    "CLIMATE.json": ("EXTERNAL_SOURCE", "HISTORICAL", "Climate data from external sources"),
    "ARCHITECTURE.json": ("EXTERNAL_SOURCE", "HISTORICAL", "Architectural data from external sources"),

    # Mythological/ritual — mix of DERIVED and UNKNOWN
    "MYTHOLOGY.json": ("UNKNOWN", "UNKNOWN", "Empty descriptions — requires author classification"),
    "RELIGION.json": ("UNKNOWN", "UNKNOWN", "Empty descriptions — requires author classification"),
    "RITUALS.json": ("UNKNOWN", "UNKNOWN", "Empty descriptions — requires author classification"),
    "SOCIAL_STRUCTURE.json": ("UNKNOWN", "UNKNOWN", "Requires author classification"),
    "DAILY_LIFE.json": ("UNKNOWN", "UNKNOWN", "Insufficient data for classification"),

    # Deep content — DERIVED
    "DEEP_CONCEPTS.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Deep concepts derived from GENOME"),
    "DEEP_DAILY_LIFE.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Daily life derived from GENOME"),

    # Media/scenes — UNKNOWN (needs author decision)
    "SCENE_PROMPTS.json": ("UNKNOWN", "UNKNOWN", "Scene prompts — needs author classification"),

    # RAG output — DERIVED (auto-generated)
    "ENRICHED_CATALOG.json": ("DERIVED", "SYSTEM_INTERPRETATION", "RAG-enriched catalog from book text"),
    "ENRICHED_CHUNKS.json": ("DERIVED", "SYSTEM_INTERPRETATION", "RAG-enriched chunks from book text"),

    # Profile files — DERIVED
    "BOOK_PROFILE.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Book profile metadata from GENOME"),
    "SYNOPSIS_PROFILE.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Synopsis profile from GENOME"),
    "CIVILIZATION_PROFILES.json": ("DERIVED", "SYSTEM_INTERPRETATION", "Civilization profiles from GENOME"),
}


def enrich_file(file_path: Path) -> dict | None:
    """Add _provenance_metadata to a KNOWLEDGE JSON file.

    Returns the updated data dict, or None if no change needed.
    """
    try:
        text = file_path.read_text(encoding="utf-8-sig")
        data = json.loads(text)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    if "_provenance_metadata" in data:
        return None

    filename = file_path.name
    classification = KNOWLEDGE_CLASSIFICATION.get(filename)

    if classification is None:
        # Default to DERIVED for unknown files
        category = "DERIVED"
        source_level = "SYSTEM_INTERPRETATION"
        notes = "Auto-classified as DERIVED (unknown source)"
    else:
        category, source_level, notes = classification

    metadata = {
        "_provenance_metadata": {
            "category": category,
            "source_level": source_level,
            "notes": notes,
            "enriched_at": "Milestone B",
        }
    }

    if isinstance(data, dict):
        enriched = {**metadata, **data}
    elif isinstance(data, list):
        enriched = {
            **metadata,
            "items": data,
            "item_count": len(data),
        }
    else:
        return None

    return enriched


def main():
    """Enrich all KNOWLEDGE JSON files with provenance metadata."""
    knowledge_dir = Path(__file__).resolve().parents[1] / "core" / "KNOWLEDGE"
    if not knowledge_dir.exists():
        knowledge_dir = Path(__file__).resolve().parents[2] / "core" / "KNOWLEDGE"

    print(f"Enriching KNOWLEDGE files in: {knowledge_dir}")

    json_files = sorted(knowledge_dir.glob("*.json"))
    enriched_count = 0
    skipped_count = 0
    errors = []

    for file_path in json_files:
        try:
            result = enrich_file(file_path)
            if result is None:
                skipped_count += 1
                continue

            # Write back with formatting
            text = json.dumps(result, ensure_ascii=False, indent=2)
            file_path.write_text(text, encoding="utf-8")
            enriched_count += 1
            print(f"  [OK] {file_path.name}")
        except Exception as e:
            errors.append((file_path.name, str(e)))
            print(f"  [FAIL] {file_path.name}: {e}")

    print(f"\nEnriched: {enriched_count}")
    print(f"Skipped (already has metadata): {skipped_count}")
    if errors:
        print(f"Errors: {len(errors)}")
        for name, err in errors[:5]:
            print(f"  - {name}: {err}")

    return enriched_count


if __name__ == "__main__":
    main()
