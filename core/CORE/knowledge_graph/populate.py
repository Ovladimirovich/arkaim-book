"""
Populate — заполнение Knowledge Graph из генома и BOOK OS хранилищ.
"""
import json
import uuid
from pathlib import Path
from typing import Optional

from book_os.entity_store import EntityStore
from book_os.relationship_store import RelationshipStore
from book_os.fact_store import FactStore
from schemas.entity import Entity
from schemas.relationship import Relationship
from schemas.fact import Fact

BASE = Path(__file__).resolve().parents[2]
GENOME_PATH = BASE / "GENOME" / "GENOME_v1.0.0.json"
OS_DATA_DIR = BASE / "OS_DATA"


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def populate_from_genome(
    entity_store: EntityStore,
    rel_store: RelationshipStore,
    fact_store: FactStore,
    genome_path: Optional[Path] = None,
):
    """Заполнить хранилища из генома.
    Сущности: персонажи, локации, концепции, символы.
    Связи: персонаж ↔ ценности, конфликты, символы.
    Факты: описания и атрибуты.
    """
    path = genome_path or GENOME_PATH
    if not path.exists():
        return 0, 0, 0

    genome = json.loads(path.read_text(encoding="utf-8"))
    modules = genome.get("modules", {})
    world = genome.get("world_entities", [])
    entities_added = 0
    rels_added = 0
    facts_added = 0

    entity_map = {}

    # 1. Characters → entities
    for ch in modules.get("characters", []):
        eid = _new_id("char")
        entity = Entity(id=eid, name=ch["name"], type="character", aliases=ch.get("aliases", []),
                        archetype=ch.get("archetype", ""), description=ch.get("description", ""), values=ch.get("values", []))
        entity_store.add(entity)
        entity_map[ch["name"]] = eid
        entities_added += 1

    # 2. Themes → entities
    for th in modules.get("themes", []):
        eid = _new_id("theme")
        entity = Entity(id=eid, name=th["name"], type="theme", description=th.get("description", ""))
        entity_store.add(entity)
        entity_map[th["name"]] = eid
        entities_added += 1

    # 3. Symbols → entities
    for sym in modules.get("symbols", []):
        eid = _new_id("sym")
        entity = Entity(id=eid, name=sym["name"], type="symbol", description=sym.get("meaning", ""))
        entity_store.add(entity)
        entity_map[sym["name"]] = eid
        entities_added += 1

    # 4. Conflicts → entities
    for conf in modules.get("conflicts", []):
        eid = _new_id("conf")
        entity = Entity(id=eid, name=conf["name"], type="conflict", description=conf.get("type", ""))
        entity_store.add(entity)
        entity_map[conf["name"]] = eid
        entities_added += 1

    # 5. Values → entities
    for val in modules.get("values", []):
        eid = _new_id("val")
        entity = Entity(id=eid, name=val["name"], type="value", description=val.get("description", ""))
        entity_store.add(entity)
        entity_map[val["name"]] = eid
        entities_added += 1

    # 6. World entities
    for we in world:
        eid = _new_id("we")
        entity = Entity(id=eid, name=we["name"], type=we.get("type", "concept"), description=we.get("description", ""),
                        values=we.get("values", []), related_to=we.get("related_to", []), conflict_with=we.get("conflict_with", []))
        entity_store.add(entity)
        entity_map[we["name"]] = eid
        entities_added += 1

    # 7. Relationships from genome
    for ch in modules.get("characters", []):
        src = entity_map.get(ch["name"])
        if not src:
            continue
        for vname in ch.get("values", []):
            tgt = entity_map.get(vname)
            if tgt:
                rid = _new_id("rel")
                rel = Relationship(id=rid, source_id=src, target_id=tgt, type="embodies")
                rel_store.add(rel)
                rels_added += 1

    for we in world:
        src = entity_map.get(we["name"])
        if not src:
            continue
        for rel_name in we.get("related_to", []):
            tgt = entity_map.get(rel_name)
            if tgt:
                rid = _new_id("rel")
                rel = Relationship(id=rid, source_id=src, target_id=tgt, type="related_to")
                rel_store.add(rel)
                rels_added += 1
        for conf_name in we.get("conflict_with", []):
            tgt = entity_map.get(conf_name)
            if tgt:
                rid = _new_id("rel")
                rel = Relationship(id=rid, source_id=src, target_id=tgt, type="conflicts_with")
                rel_store.add(rel)
                rels_added += 1

    # 8. Facts from genome
    for ch in modules.get("characters", []):
        eid = entity_map.get(ch["name"])
        if eid and ch.get("description"):
            fid = _new_id("fact")
            fact = Fact(id=fid, statement=f"Персонаж {ch['name']}: {ch['description']}", entity_id=eid, doc_id="genome", provenance="genome", confidence=0.9)
            fact_store.add(fact)
            facts_added += 1
    for we in world:
        eid = entity_map.get(we["name"])
        if eid and we.get("description"):
            fid = _new_id("fact")
            fact = Fact(id=fid, statement=f"{we['name']}: {we['description']}", entity_id=eid, doc_id="genome", provenance="genome", confidence=0.9)
            fact_store.add(fact)
            facts_added += 1

    return entities_added, rels_added, facts_added


def populate_from_book_os(entity_store: EntityStore, rel_store: RelationshipStore):
    """Построить граф из уже существующих BOOK OS хранилищ.
    Просто триггерит build() — данные уже есть в entity/relationship store.
    Счётчики показывают, сколько уже есть."""
    return entity_store.get_stats()["total"], rel_store.get_stats()["total"]
