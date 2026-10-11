"""
Скрипт: SCHEMAS → Visual Genome.
Читает JSON-схемы из SCHEMAS/ и генерирует черновик Visual Genome.
"""
import json
import sys
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent / "ARKAIM_DIGITAL_CONSCIOUSNESS" / "CORE"
sys.path.insert(0, str(CORE_DIR))

from visualization.archetype_visuals import ARCHETYPE_VISUAL_TEMPLATES

SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "SCHEMAS"
GENOME_DIR = CORE_DIR.parent / "GENOME"
CURRENT_DIR = GENOME_DIR / "CURRENT"

ARCHETYPE_MAP = {
    "Искатель": ARCHETYPE_VISUAL_TEMPLATES["Искатель"],
    "Мудрец": ARCHETYPE_VISUAL_TEMPLATES["Мудрец"],
    "Хранитель": ARCHETYPE_VISUAL_TEMPLATES["Хранитель"],
    "Проводник": ARCHETYPE_VISUAL_TEMPLATES["Проводник"],
    "Архат": ARCHETYPE_VISUAL_TEMPLATES["Архат"],
    "Наставник": ARCHETYPE_VISUAL_TEMPLATES["Наставник"],
    "Лидер": ARCHETYPE_VISUAL_TEMPLATES["Лидер"],
    "Учёный": ARCHETYPE_VISUAL_TEMPLATES["Учёный"],
}


def log(msg: str):
    print(f"[SCHEMAS->Visuals] {msg}")


def load_schema(name: str) -> dict:
    path = SCHEMAS_DIR / name
    if not path.exists():
        log(f"  Schema not found: {name}")
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def extract_from_character_schema(schema: dict) -> list[dict]:
    """Из CHARACTER.schema — archetype → character_visuals."""
    if not schema:
        return []
    visuals = []
    archetypes = schema.get("archetypes", []) or []
    props = schema.get("properties", {})
    archetype_enum = props.get("archetype", {}).get("enum", archetypes)

    for archetype in archetype_enum:
        if archetype in ARCHETYPE_MAP:
            template = ARCHETYPE_MAP[archetype]
            visuals.append({
                "character_id": archetype.lower(),
                "archetype": archetype,
                "clothing": template["clothing"],
                "color_palette": template["color_palette"],
                "accessories": template["accessories"],
                "style_constants": template["style_constants"],
                "note": f"авто-создано из архетипа '{archetype}'",
            })
            log(f"  Character visual: {archetype}")
    return visuals


def extract_from_entity_schema(schema: dict) -> list[dict]:
    """Из ENTITY.schema — location → location_visuals."""
    if not schema:
        return []
    visuals = []
    props = schema.get("properties", {})
    types = props.get("type", {}).get("enum", [])
    for etype in types:
        if etype in ("location", "location"):
            visual = {
                "location_id": f"{etype}_template",
                "type": etype,
                "architecture": "описание не заполнено",
                "atmosphere": "нейтральная",
                "lighting": "естественный свет",
                "palette": ["#808080", "#A9A9A9", "#D3D3D3"],
                "note": "авто-создано из ENTITY.schema",
            }
            visuals.append(visual)
            log(f"  Location visual: {etype}")
    return visuals


def extract_from_theme_schema(schema: dict) -> list[dict]:
    """Из THEME.schema — theme → meaning_tags."""
    if not schema:
        return []
    tags = []
    props = schema.get("properties", {})
    theme_enum = props.get("name", {}).get("enum", [])
    for theme in theme_enum:
        tag = f"theme:{theme}"
        tags.append(tag)
        log(f"  Meaning tag: {tag}")
    return tags


def save_output(data: list | dict, name: str):
    CURRENT_DIR.mkdir(parents=True, exist_ok=True)
    path = CURRENT_DIR / name
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    log(f"  Saved: GENOME/CURRENT/{name}")


def main():
    log("=" * 50)
    log("SCHEMAS -> Visual Genome")
    log("=" * 50)

    char_schema = load_schema("CHARACTER.schema.json")
    entity_schema = load_schema("ENTITY.schema.json")
    theme_schema = load_schema("THEME.schema.json")

    log("\n1. Извлечение character_visuals из CHARACTER.schema...")
    char_visuals = extract_from_character_schema(char_schema)
    if char_visuals:
        save_output(char_visuals, "character_visuals_from_schemas.json")

    log("\n2. Извлечение location_visuals из ENTITY.schema...")
    loc_visuals = extract_from_entity_schema(entity_schema)
    if loc_visuals:
        save_output(loc_visuals, "location_visuals_from_schemas.json")

    log("\n3. Извлечение meaning_tags из THEME.schema...")
    meaning_tags = extract_from_theme_schema(theme_schema)
    if meaning_tags:
        save_output(meaning_tags, "meaning_tags_from_schemas.json")

    log("\n" + "=" * 50)
    log(f"Итого: {len(char_visuals)} character_visuals, "
         f"{len(loc_visuals)} location_visuals, "
         f"{len(meaning_tags)} meaning_tags")
    log("=" * 50)


if __name__ == "__main__":
    main()
