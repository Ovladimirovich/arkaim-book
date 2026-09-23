"""Заполнение World Model из Genome + KNOWLEDGE/*.json."""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone

log = logging.getLogger("hermes.narrative.seed")


def seed_world_model() -> dict:
    """Заполнить World Model из существующих данных проекта."""
    genome = _load_genome()
    knowledge_dir = Path("core/KNOWLEDGE")

    epochs = _extract_epochs(genome, knowledge_dir)
    locations = _extract_locations(genome, knowledge_dir)
    civilizations = _extract_civilizations(genome, knowledge_dir)
    technologies = _extract_technologies(genome, knowledge_dir)
    religions = _extract_religions(genome, knowledge_dir)
    characters_living = _extract_characters_living(genome, epochs)
    canonical_events = _extract_events(genome)
    causal_rules = _extract_causal_rules()

    return {
        "version": "1.0.0",
        "updated_at": datetime.now(tz=timezone.utc).isoformat(),
        "epochs": epochs,
        "locations": locations,
        "civilizations": civilizations,
        "technologies": technologies,
        "religions": religions,
        "characters_living": characters_living,
        "canonical_events": canonical_events,
        "causal_rules": causal_rules,
    }


def _load_genome() -> dict:
    """Загрузить актуальный genome."""
    genome_dir = Path("core/CORE/genome/history")
    candidates = sorted(genome_dir.glob("genome_v*.json"), reverse=True)
    if not candidates:
        log.warning("no_genome_found")
        return {}
    return json.loads(candidates[0].read_text(encoding="utf-8"))


def _extract_epochs(genome: dict, knowledge_dir: Path) -> list[dict]:
    """Извлечь эпохи из genome + COSMOLOGY.json."""
    epochs = []
    seen_ids = set()

    # Из genome: темы, связанные с эпохами
    for theme in genome.get("modules", {}).get("themes", []):
        name = theme.get("name", "")
        name_lower = name.lower()
        # Определяем эпоху по ключевым словам
        if any(kw in name_lower for kw in ["юга", "эпоха", "век", "эра", "время"]):
            epoch_id = name_lower.replace(" ", "_").replace("-", "_")
            if epoch_id not in seen_ids:
                seen_ids.add(epoch_id)
                epochs.append({
                    "id": epoch_id,
                    "name": name,
                    "name_ru": name,
                    "description": theme.get("description", ""),
                    "order": len(epochs) + 1,
                    "source_level": "CANON",
                    "provenance": [],
                })

    # Добавляем стандартные эпохи, если их нет
    standard_epochs = [
        {"id": "satya_yuga", "name": "Satya Yuga", "name_ru": "Сатья Юга (Золотой век)", "order": 1,
         "description": "Золотой век — время высшего духовного развития и гармонии."},
        {"id": "treta_yuga", "name": "Treta Yuga", "name_ru": "Трета Юга (Серебряный век)", "order": 2,
         "description": "Серебряный век — начало деградации, появление первых конфликтов."},
        {"id": "dvapara_yuga", "name": "Dvapara Yuga", "name_ru": "Двапара Юга (Бронзовый век)", "order": 3,
         "description": "Бронзовый век — усиление разделения, утрата единства."},
        {"id": "kali_yuga", "name": "Kali Yuga", "name_ru": "Кали Юга (Тёмный век)", "order": 4,
         "description": "Тёмный век — время испытаний и поиска пути домой."},
        {"id": "pre_arkaim", "name": "Pre-Arkaim", "name_ru": "До Аркаима", "order": 0,
         "description": "Эпоха до основания Аркаима — время скитаний и поиска."},
        {"id": "arkaim_era", "name": "Arkaim Era", "name_ru": "Эпоха Аркаима", "order": 5,
         "description": "Эпоха расцвета Аркаима — центра духовного знания."},
    ]
    for se in standard_epochs:
        if se["id"] not in seen_ids:
            seen_ids.add(se["id"])
            se["source_level"] = "SYSTEM_INTERPRETATION"
            se["provenance"] = []
            epochs.append(se)

    return sorted(epochs, key=lambda e: e["order"])


def _extract_locations(genome: dict, knowledge_dir: Path) -> list[dict]:
    """Извлечь локации из genome + MAP_DATA.json + GEOGRAPHY.json."""
    locations = []
    seen_ids = set()

    # Из genome: world_entities с типом location
    for entity in genome.get("world_entities", []):
        if entity.get("type") in ("location", "civilization", "concept"):
            loc_id = entity.get("name", "").lower().replace(" ", "_").replace("-", "_")
            if loc_id and loc_id not in seen_ids:
                seen_ids.add(loc_id)
                locations.append({
                    "id": loc_id,
                    "name": entity["name"],
                    "name_ru": entity["name"],
                    "type": "region" if entity.get("type") == "location" else "other",
                    "description": entity.get("description", ""),
                    "epochs_present": [],
                    "related_entities": entity.get("related_to", []),
                    "source_level": "CANON",
                    "provenance": [],
                })

    # Из MAP_DATA.json
    map_path = knowledge_dir / "MAP_DATA.json"
    if map_path.exists():
        try:
            map_data = json.loads(map_path.read_text(encoding="utf-8"))
            for region in map_data.get("regions", []):
                loc_id = region.get("id", "").lower().replace(" ", "_")
                if loc_id and loc_id not in seen_ids:
                    seen_ids.add(loc_id)
                    locations.append({
                        "id": loc_id,
                        "name": region.get("name", ""),
                        "name_ru": region.get("name", ""),
                        "type": region.get("type", "region"),
                        "description": region.get("description", ""),
                        "coordinates": region.get("coordinates"),
                        "epochs_present": [],
                        "source_level": "SYSTEM_INTERPRETATION",
                        "provenance": [],
                    })
        except Exception:
            pass

    # Добавляем ключевые локации, если их нет
    key_locations = [
        {"id": "hyperborea", "name": "Hyperborea", "name_ru": "Гиперборея", "type": "region",
         "description": "Земля предков — прародина человечества."},
        {"id": "arkaim", "name": "Arkaim", "name_ru": "Аркаим", "type": "sacred_site",
         "description": "Древний город-крепость, центр духовного знания."},
        {"id": "tmutarakan", "name": "Tmutarakan", "name_ru": "Тмутаракань", "type": "city",
         "description": "Древний город на берегу моря."},
        {"id": "sumer", "name": "Sumer", "name_ru": "Шумер", "type": "region",
         "description": "Колыбель цивилизации."},
        {"id": "india", "name": "India", "name_ru": "Индия", "type": "region",
         "description": "Земля древних риши и ведической традиции."},
    ]
    for kl in key_locations:
        if kl["id"] not in seen_ids:
            seen_ids.add(kl["id"])
            kl["source_level"] = "CANON"
            kl["provenance"] = []
            locations.append(kl)

    return locations


def _extract_civilizations(genome: dict, knowledge_dir: Path) -> list[dict]:
    """Извлечь цивилизации из genome."""
    civs = []
    seen_ids = set()

    for entity in genome.get("world_entities", []):
        if entity.get("type") == "civilization":
            civ_id = entity.get("name", "").lower().replace(" ", "_").replace("-", "_")
            if civ_id and civ_id not in seen_ids:
                seen_ids.add(civ_id)
                civs.append({
                    "id": civ_id,
                    "name": entity["name"],
                    "name_ru": entity["name"],
                    "description": entity.get("description", ""),
                    "epochs": [],
                    "values": entity.get("values", []),
                    "technologies": [],
                    "religion_ids": [],
                    "related_locations": entity.get("related_to", []),
                    "source_level": "CANON",
                    "provenance": [],
                })

    # Добавляем стандартные цивилизации
    key_civs = [
        {"id": "hyperborean", "name": "Hyperborean", "name_ru": "Гиперборейцы",
         "description": "Древнейшая цивилизация — хранители изначального знания."},
        {"id": "vedic", "name": "Vedic", "name_ru": "Ведическая",
         "description": "Цивилизация, основанная на ведическом знании."},
    ]
    for kc in key_civs:
        if kc["id"] not in seen_ids:
            seen_ids.add(kc["id"])
            kc["source_level"] = "SYSTEM_INTERPRETATION"
            kc["provenance"] = []
            civs.append(kc)

    return civs


def _extract_technologies(genome: dict, knowledge_dir: Path) -> list[dict]:
    """Извлечь технологии из KNOWLEDGE/TECHNOLOGY.json."""
    techs = []
    seen_ids = set()

    tech_path = knowledge_dir / "TECHNOLOGY.json"
    if tech_path.exists():
        try:
            data = json.loads(tech_path.read_text(encoding="utf-8"))
            items = data if isinstance(data, list) else data.get("technologies", data.get("items", []))
            for item in items[:20]:  # Ограничиваем
                tech_id = item.get("name", "").lower().replace(" ", "_").replace("-", "_")
                if tech_id and tech_id not in seen_ids:
                    seen_ids.add(tech_id)
                    techs.append({
                        "id": tech_id,
                        "name": item.get("name", ""),
                        "name_ru": item.get("name", ""),
                        "description": item.get("description", item.get("summary", "")),
                        "epoch_first": None,
                        "civilization_origin": None,
                        "source_level": "SYSTEM_INTERPRETATION",
                        "provenance": [],
                    })
        except Exception:
            pass

    # Ключевые технологии
    key_techs = [
        {"id": "energy_harmony", "name": "Energy Harmony", "name_ru": "Гармония энергий",
         "description": "Способность чувствовать и направлять энергии природы."},
        {"id": "crystal_tech", "name": "Crystal Technology", "name_ru": "Кристальная технология",
         "description": "Использование кристаллов для хранения и передачи информации."},
        {"id": "stone_architecture", "name": "Stone Architecture", "name_ru": "Каменное зодчество",
         "description": "Строительство каменных сооружений и городов."},
    ]
    for kt in key_techs:
        if kt["id"] not in seen_ids:
            seen_ids.add(kt["id"])
            kt["source_level"] = "SYSTEM_INTERPRETATION"
            kt["provenance"] = []
            techs.append(kt)

    return techs


def _extract_religions(genome: dict, knowledge_dir: Path) -> list[dict]:
    """Извлечь религии из KNOWLEDGE/PHILOSOPHY.json."""
    religions = []
    # Базовые религиозные концепции из genome
    key_religions = [
        {"id": "vedic_tradition", "name": "Vedic Tradition", "name_ru": "Ведическая традиция",
         "description": "Древнейшая духовная традиция, основанная на ведах.",
         "epochs": ["satya_yuga", "treta_yuga"], "practices": ["meditation", "ritual", "study"]},
        {"id": "hyperborean_cult", "name": "Hyperborean Cult", "name_ru": "Гиперборейский культ",
         "description": "Культ Солнца и огня у гиперборейцев.",
         "epochs": ["satya_yuga"], "practices": ["fire_ritual", "sun_worship"]},
    ]
    for kr in key_religions:
        kr["key_figures"] = []
        kr["source_level"] = "SYSTEM_INTERPRETATION"
        kr["provenance"] = []
        religions.append(kr)

    return religions


def _extract_characters_living(genome: dict, epochs: list[dict]) -> dict:
    """Определить, какие персонажи живы в какие эпохи."""
    characters = genome.get("modules", {}).get("characters", [])
    result = {}

    for ch in characters:
        name = ch.get("name", "")
        first_ch = ch.get("first_chapter") or 1
        last_ch = ch.get("last_chapter") or 999

        # Простое маппирование: глава 1-10 → первые эпохи, 11-20 → средние, 21+ → поздние
        if first_ch <= 5:
            epoch = "satya_yuga"
        elif first_ch <= 15:
            epoch = "treta_yuga"
        elif first_ch <= 25:
            epoch = "dvapara_yuga"
        else:
            epoch = "kali_yuga"

        if epoch not in result:
            result[epoch] = []

        result[epoch].append({
            "character_name": name,
            "epoch": epoch,
            "location_id": None,
            "status": "alive",
            "notes": f"Персонаж из глав {first_ch}-{last_ch}",
            "source_level": "SYSTEM_INTERPRETATION",
        })

    return result


def _extract_events(genome: dict) -> list[dict]:
    """Извлечь события из genome timeline."""
    events = []
    timeline = genome.get("modules", {}).get("timeline", [])

    for i, item in enumerate(timeline):
        event_id = f"event_{i:03d}"
        events.append({
            "id": event_id,
            "title": item.get("event", item.get("title", "")),
            "title_ru": item.get("event", item.get("title", "")),
            "description": item.get("description", ""),
            "epoch": "unknown",
            "location_id": None,
            "characters_involved": [],
            "chapter": item.get("chapter"),
            "order_in_epoch": i,
            "source_level": "CANON",
            "provenance": [],
        })

    return events


def _extract_causal_rules() -> list[dict]:
    """Создать базовые причинно-следственные правила."""
    return [
        {
            "id": "rule_no_tech_before_epoch",
            "description": "Технологии эпохи не могут появиться раньше своего времени",
            "rule_type": "exclusion",
            "condition": "technologies must match epoch",
            "related_events": [],
            "related_characters": [],
            "source_level": "SYSTEM_INTERPRETATION",
        },
        {
            "id": "rule_no_future_knowledge",
            "description": "Персонаж не может знать о событиях, которые ещё не произошли",
            "rule_type": "exclusion",
            "condition": "character knowledge must not exceed current epoch",
            "related_events": [],
            "related_characters": [],
            "source_level": "SYSTEM_INTERPRETATION",
        },
        {
            "id": "rule_geographic_consistency",
            "description": "Персонаж не может быть одновременно в двух удалённых локациях",
            "rule_type": "exclusion",
            "condition": "character location must be single at any time",
            "related_events": [],
            "related_characters": [],
            "source_level": "SYSTEM_INTERPRETATION",
        },
        {
            "id": "rule_causal_chain",
            "description": "Следствия не могут предшествовать причинам",
            "rule_type": "dependency",
            "condition": "effects must follow causes in timeline",
            "related_events": [],
            "related_characters": [],
            "source_level": "SYSTEM_INTERPRETATION",
        },
    ]


def seed_if_needed():
    """Заполнить World Model, если файл не существует."""
    from pathlib import Path
    wm_path = Path("core/CORE/narrative_engine/data/WORLD_MODEL.json")
    if not wm_path.exists():
        log.info("seeding_world_model")
        data = seed_world_model()
        wm_path.parent.mkdir(parents=True, exist_ok=True)
        wm_path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        log.info("world_model_seeded epochs=%d locations=%d events=%d",
                 len(data["epochs"]), len(data["locations"]), len(data["canonical_events"]))
        return True
    return False


