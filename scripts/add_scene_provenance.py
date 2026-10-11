"""Add provenance_breakdown to each scene in SCENE_PROMPTS.json.

Based on forensic audit (2026-09-16):
- description: AUTHOR_CANON for confirmed book scenes, UNKNOWN for unverified
- prompt, palette, emotion, style: ARTISTIC_MODEL (system-generated)
- characters, chapter, title: AUTHOR_CANON
- location: AUTHOR_CANON or EXTERNAL_SOURCE (scene_09 uses archaeological fact)
"""
from pathlib import Path
import json

KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "core" / "KNOWLEDGE"
FILE = KNOWLEDGE_DIR / "SCENE_PROMPTS.json"

# Provenance mapping per scene ID
# description: "canon" = confirmed in КНИГА.md, "unknown" = not found / interpretive
# location_extra: additional note for mixed provenance locations
SCENE_PROVENANCE = {
    "scene_01": {
        "description": "AUTHOR_CANON",
        "location": "AUTHOR_CANON",
        "notes": "Пролог: фигура в пещере + самозаконсервация — BOOK_DOCUMENT.json:44,244,258"
    },
    "scene_02": {
        "description": "AUTHOR_CANON",
        "location": "AUTHOR_CANON",
        "notes": "Часть 1-2: заснеженные перевалы — BOOK_DOCUMENT.json:53,391"
    },
    "scene_03": {
        "description": "UNKNOWN",
        "location": "AUTHOR_CANON",
        "notes": "Встреча со Славным — канон (BOOK:71), но 'белобородый сияющий старец' не подтверждён дословно — требует решения автора"
    },
    "scene_04": {
        "description": "AUTHOR_CANON",
        "location": "AUTHOR_CANON",
        "notes": "Гиперборея как северная цивилизация — AUTHOR_CANON (CHARACTERS.json, PHILOSOPHY.json)"
    },
    "scene_05": {
        "description": "AUTHOR_CANON",
        "location": "AUTHOR_CANON",
        "notes": "Звукознание — буквальная цитата BOOK_DOCUMENT.json:3240"
    },
    "scene_06": {
        "description": "AUTHOR_CANON",
        "location": "AUTHOR_CANON",
        "notes": "12 Наставников — BOOK_DOCUMENT.json:107 'Их было двенадцать. Двенадцать достойных'"
    },
    "scene_07": {
        "description": "AUTHOR_CANON",
        "location": "AUTHOR_CANON",
        "notes": "Катаклизмы — BOOK_DOCUMENT.json:98; город обезлюдел — BOOK:107"
    },
    "scene_08": {
        "description": "AUTHOR_CANON",
        "location": "AUTHOR_CANON",
        "notes": "Миграция — BOOK_DOCUMENT.json:116,125"
    },
    "scene_09": {
        "description": "EXTERNAL_SOURCE",
        "location": "EXTERNAL_SOURCE",
        "notes": "Круглый город с двойными стенами — археологический факт (ARCHAEOLOGY.json), не описание из книги"
    },
    "scene_10": {
        "description": "AUTHOR_CANON",
        "location": "AUTHOR_CANON",
        "notes": "Световит как Посредник — BOOK:107,116; передача учения — канон"
    },
    "scene_11": {
        "description": "AUTHOR_CANON",
        "location": "EXTERNAL_SOURCE",
        "notes": "Обнаружение Аркаима археологами — BOOK_DOCUMENT.json:179 (эпилог книги)"
    },
    "scene_12": {
        "description": "AUTHOR_CANON",
        "location": "AUTHOR_CANON",
        "notes": "Самозаконсервация Велика — BOOK_DOCUMENT.json:58,258; пещера Учителя — BOOK:4052"
    },
}


def add_provenance_breakdown(data: dict) -> dict:
    """Add provenance_breakdown to each scene and update file-level metadata."""
    for scene in data.get("scenes", []):
        sid = scene.get("id", "")
        mapping = SCENE_PROVENANCE.get(sid, {})

        description_prov = mapping.get("description", "UNKNOWN")
        location_prov = mapping.get("location", "UNKNOWN")
        notes = mapping.get("notes", "")

        # Determine overall scene category (lowest common denominator)
        if description_prov == "EXTERNAL_SOURCE" or location_prov == "EXTERNAL_SOURCE":
            overall = "EXTERNAL_SOURCE"
        elif description_prov == "UNKNOWN":
            overall = "UNKNOWN"
        else:
            overall = "AUTHOR_CANON"

        scene["provenance_breakdown"] = {
            "description": description_prov,
            "title": "AUTHOR_CANON",
            "chapter": "AUTHOR_CANON",
            "characters": "AUTHOR_CANON",
            "location": location_prov,
            "emotion": "ARTISTIC_MODEL",
            "palette": "ARTISTIC_MODEL",
            "prompt": "ARTISTIC_MODEL",
            "style": "SYSTEM_INTERPRETATION",
            "_overall": overall,
            "_notes": notes,
        }

    # Update file-level metadata to reflect mixed provenance
    data["_provenance_metadata"] = {
        "category": "DERIVED",
        "source_level": "SYSTEM_INTERPRETATION",
        "notes": "Scene descriptions derived from КНИГА.md (AUTHOR_CANON); prompts, palettes, emotions are ARTISTIC_MODEL system interpretations. Per-scene breakdown in each scene.provenance_breakdown.",
        "enriched_at": "Milestone B (forensic follow-up)",
    }
    return data


def main():
    text = FILE.read_text(encoding="utf-8-sig")
    data = json.loads(text)

    before = len(data.get("scenes", []))
    with_breakdown = sum(1 for s in data.get("scenes", []) if "provenance_breakdown" in s)

    data = add_provenance_breakdown(data)

    after_with_breakdown = sum(1 for s in data.get("scenes", []) if "provenance_breakdown" in s)

    FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Scenes: {before} total, {with_breakdown} had breakdown before, {after_with_breakdown} now have breakdown")
    print(f"File-level category: {data['_provenance_metadata']['category']}")

    # Summary
    categories = {}
    for s in data["scenes"]:
        cat = s["provenance_breakdown"]["_overall"]
        categories[cat] = categories.get(cat, 0) + 1
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count} scenes")


if __name__ == "__main__":
    main()
