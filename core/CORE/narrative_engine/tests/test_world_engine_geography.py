"""Guard слоя географии World Engine: без устаревших зеркал и дублей идентичности.

Решение владельца 2026-10-20: дубли `region_*`/`geo_*` убраны, у энергетических
линий появились стабильные идентификаторы, knowledge-зеркало больше не
порождает географические записи.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CORE = ROOT / "core" / "CORE"
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))

from narrative_engine.relation_extractor import extract_relations  # noqa: E402

GEOGRAPHY_PATH = CORE / "WORLD_MODEL" / "GEOGRAPHY.json"


def _geography() -> list[dict]:
    return json.loads(GEOGRAPHY_PATH.read_text(encoding="utf-8"))


def test_no_stale_knowledge_mirrors():
    """Записи `geo_*` — устаревшие зеркала knowledge-слоя; их больше нет."""
    stale = [item["id"] for item in _geography() if item["id"].startswith("geo_")]

    assert stale == [], f"в слое географии остались зеркала: {stale}"


def test_ids_and_names_are_unique():
    """Одно место — один идентификатор и одно имя.

    Исключение — записи ``char_location_*``: это не второе место, а запись
    «локация, упомянутая в описании персонажа» (свой тип character_location),
    которая ссылается на уже известную географическую сущность.
    """
    items = _geography()
    ids = [str(item.get("id", "")) for item in items]
    primary = [
        item
        for item in items
        if not str(item.get("id", "")).startswith("char_location_")
    ]
    primary_names = [
        str(item.get("name_ru") or item.get("name") or "").casefold() for item in primary
    ]

    assert len(ids) == len(set(ids)), "в географии повторяются идентификаторы"
    assert len(primary_names) == len(set(primary_names)), "в географии повторяются названия"


def test_character_mentions_point_to_known_places():
    """Записи char_location_* не плодят новые места — они ссылаются на известные."""
    items = _geography()
    primary_names = {
        str(item.get("name_ru") or item.get("name") or "").casefold()
        for item in items
        if not str(item.get("id", "")).startswith("char_location_")
    }

    for item in items:
        if not str(item.get("id", "")).startswith("char_location_"):
            continue
        name = str(item.get("name_ru") or item.get("name") or "").casefold()
        assert name in primary_names, f"{item.get('id')} ссылается на неизвестное место"


def test_energy_lines_have_stable_distinct_ids():
    """Энергетические линии больше не делят один id `energy_line_unknown`."""
    lines = [
        item
        for item in _geography()
        if str(item.get("id", "")).startswith("energy_line_")
    ]

    assert len(lines) == 2
    ids = {str(item["id"]) for item in lines}
    assert len(ids) == 2, "энергетические линии делят идентификатор"
    assert "energy_line_unknown" not in ids


def test_approved_regions_are_kept():
    """Одобренные crosswalk-локации остались в слое."""
    ids = {str(item.get("id", "")) for item in _geography()}

    for entity_id in ("region_arkaim", "region_hyperborea", "region_oceania"):
        assert entity_id in ids, f"пропала одобренная локация {entity_id}"


def test_geographic_relations_have_no_unknown_type():
    """Связи «Регионы одного типа: unknown» больше не создаются."""
    graph = extract_relations()
    relations = list(getattr(graph, "_relations", []) or [])

    unknown = [
        relation
        for relation in relations
        if "Регионы одного типа: unknown" in str(getattr(relation, "description", ""))
    ]

    assert unknown == [], "в графе связей снова появились зеркальные связи"
