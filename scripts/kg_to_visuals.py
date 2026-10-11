"""
Скрипт: Knowledge Graph → Visual Genome.
Обходит граф сущностей и создаёт черновик Visual Genome.
"""
import json
import sys
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent / "ARKAIM_DIGITAL_CONSCIOUSNESS" / "CORE"
sys.path.insert(0, str(CORE_DIR))

from core.config import config

KNOWLEDGE_DIR = config.KNOWLEDGE_DIR
GENOME_DIR = config.GENOME_DIR
CURRENT_DIR = GENOME_DIR / "CURRENT"

# Импорты с защитой
try:
    from book_os.entity_store import EntityStore
    from book_os.relationship_store import RelationshipStore
    from book_os.fact_store import FactStore
    from knowledge_graph.graph_engine import GraphEngine
    KG_AVAILABLE = True
except ImportError:
    KG_AVAILABLE = False

try:
    from visualization.character_visualizer import CharacterVisualizer
    from visualization.world_visualizer import WorldVisualizer
    VIS_AVAILABLE = True
except ImportError:
    VIS_AVAILABLE = False


def log(msg):
    print(f"[KG->Visuals] {msg}")


def load_knowledge_store(name: str) -> dict:
    """Загрузить JSON-файл хранилища из KNOWLEDGE."""
    path = KNOWLEDGE_DIR / name
    if not path.exists():
        log(f"  NOT FOUND: {name}")
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def extract_from_graph(genome: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """Извлечь visual-черновики из Knowledge Graph.

    Возвращает (character_visuals, location_visuals, scenes).
    """
    char_visuals = []
    loc_visuals = []
    scenes = []

    if KG_AVAILABLE:
        try:
            entity_store = EntityStore()
            rel_store = RelationshipStore()
            fact_store = FactStore()
            engine = GraphEngine(entity_store, rel_store, fact_store)
            engine.build()
            stats = engine.stats()
            log(f"Граф: {stats.get('nodes', 0)} узлов, {stats.get('edges', 0)} рёбер")

            all_nodes = entity_store.list()
            for entity in all_nodes:
                etype = entity.type or "unknown"
                ename = entity.name or entity.id
                if etype == "person" and VIS_AVAILABLE:
                    cv = CharacterVisualizer(genome).visualize(entity.id)
                    if cv is None:
                        cv = CharacterVisualizer(genome).visualize(entity.name)
                    if cv and cv.get("clothing") != "не указана":
                        cv["source"] = "kg_extracted"
                        char_visuals.append(cv)
                    elif cv is None and ename:
                        char_visuals.append({
                            "character_id": ename,
                            "age_range": "не указан",
                            "clothing": entity.description or "не указана",
                            "color_palette": ["earth tones"],
                            "accessories": [],
                            "style_constants": [],
                            "source": "kg_extracted_fallback",
                        })

                elif etype in ("location", "place") and VIS_AVAILABLE:
                    wv = WorldVisualizer(genome).visualize(entity.id)
                    if wv is None:
                        wv = WorldVisualizer(genome).visualize(entity.name)
                    if wv:
                        wv["source"] = "kg_extracted"
                        loc_visuals.append(wv)

            # Сцены из связей
            conflict_rid = "conflict_with"
            all_rels = rel_store.list()
            group_scene_chars = {}
            for rel in all_rels:
                if rel.type == conflict_rid:
                    scenes.append({
                        "chapter": 1,
                        "scene_id": f"kg_conflict_{rel.source_id}_{rel.target_id}",
                        "title": f"Конфликт из графа знаний",
                        "characters": [rel.source_id, rel.target_id],
                        "location": "",
                        "emotion": "conflict",
                        "meaning_tags": [f"конфликт:{rel.type}"],
                        "visual_style_hint": "contrast",
                        "source": "kg_extracted",
                    })
                elif rel.type in ("meets", "dialog", "related_to"):
                    key = tuple(sorted([rel.source_id, rel.target_id]))
                    if key not in group_scene_chars:
                        group_scene_chars[key] = {"chars": set(), "rels": []}
                    group_scene_chars[key]["chars"].add(rel.source_id)
                    group_scene_chars[key]["chars"].add(rel.target_id)
                    group_scene_chars[key]["rels"].append(rel.type)

            for key, data in group_scene_chars.items():
                chars = list(data["chars"])
                rel_types = list(set(data["rels"]))
                if len(chars) >= 2:
                    scenes.append({
                        "chapter": 1,
                        "scene_id": f"kg_group_{chars[0]}_{chars[1]}",
                        "title": f"Сцена: {' и '.join(chars)}",
                        "characters": chars,
                        "location": "",
                        "emotion": "встреча",
                        "meaning_tags": [f"связь:{r}" for r in rel_types],
                        "visual_style_hint": "group_interaction",
                        "source": "kg_extracted",
                    })

        except Exception as e:
            log(f"Ошибка при работе с KG: {e}")

    return char_visuals, loc_visuals, scenes


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
    log("Knowledge Graph -> Visual Genome")
    log("=" * 50)

    if not KG_AVAILABLE:
        log("ПРЕДУПРЕЖДЕНИЕ: KG-модули не найдены. "
            "Работаем через KNOWLEDGE/*.json.")
        genome_path = GENOME_DIR / "GENOME_v1.0.0.json"
        if genome_path.exists():
            genome = json.loads(genome_path.read_text(encoding="utf-8"))
        else:
            log("Геном не найден.")
            return
    else:
        genome_path = GENOME_DIR / "GENOME_v1.0.0.json"
        genome = json.loads(genome_path.read_text(encoding="utf-8")) if genome_path.exists() else {}

    char_visuals, loc_visuals, scenes = extract_from_graph(genome)

    log(f"\nРезультаты:")
    log(f"  Character visuals: {len(char_visuals)}")
    log(f"  Location visuals:  {len(loc_visuals)}")
    log(f"  Scenes:           {len(scenes)}")

    if char_visuals:
        save_output(char_visuals, "character_visuals_from_kg.json")
    if loc_visuals:
        save_output(loc_visuals, "location_visuals_from_kg.json")
    if scenes:
        save_output(scenes, "scenes_from_kg.json")

    log("=" * 50)


if __name__ == "__main__":
    main()
