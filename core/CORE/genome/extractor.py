"""
Extractor — извлечение Генома Книги из исходных текстов.
Читает SOURCE_OF_TRUTH/ и KNOWLEDGE/, пишет валидированный GENOME/.
"""
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

from genome.validator import validate_genome

BASE = Path(__file__).resolve().parents[2]
KNOWLEDGE = BASE / "KNOWLEDGE"
SOURCE_OF_TRUTH = BASE / "SOURCE_OF_TRUTH"
GENOME_DIR = BASE / "GENOME"
CURRENT_DIR = GENOME_DIR / "CURRENT"
GENOME_VERSION = "1.0.0"

GENOME_VERSION = "1.0.0"


def log(msg):
    print(f"[Genome] {msg}", flush=True)


def load_json(path: Path) -> dict:
    if not path.exists():
        log(f"  WARNING: {path.name} not found")
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_genome(data: Any, name: str):
    CURRENT_DIR.mkdir(parents=True, exist_ok=True)
    p = CURRENT_DIR / name
    p.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )
    log(f"  Saved: GENOME/CURRENT/{name}")


def extract_themes(philosophy: dict, chatpdf: dict) -> list:
    """Извлечение тем из философии + chatpdf."""
    themes = []
    seen = set()

    for c in philosophy.get("concepts", []):
        name = c.get("name", "").strip()
        if name and name not in seen:
            seen.add(name)
            themes.append({
                "id": f"theme_{len(themes)+1:03d}",
                "name": name,
                "description": c.get("description", ""),
                "strength": 0.7,
            })

    # Core themes from book
    core = [
        ("Духовная эволюция", "Путь персонажей от материального к духовному"),
        ("Память предков", "Сохранение знаний через поколения"),
        ("Кали Юга и Сати Юга", "Цикличность эпох"),
        ("Закон причинности", "Свобода воли и невмешательство высших сил"),
        ("Гиперборея", "Северная цивилизация — хранительница древних знаний"),
        ("Наследие Учения", "Передача Великого Учения от учителей к ученикам"),
    ]
    for name, desc in core:
        if name not in seen:
            themes.insert(0, {
                "id": f"theme_{len(themes)+1:03d}",
                "name": name,
                "description": desc,
                "strength": 0.95,
            })

    return themes


def extract_values(values_data: dict) -> list:
    """Извлечение ценностей."""
    vals = []
    seen = set()

    for v in values_data.get("values", []):
        name = v.get("name", "").strip()
        if name and name not in seen:
            seen.add(name)
            vals.append({
                "id": f"val_{len(vals)+1:03d}",
                "name": name,
                "description": v.get("description", ""),
                "strength": v.get("strength", 0.6),
            })

    core = [
        ("Истина", "Поиск истины — главная движущая сила"),
        ("Преемственность", "Передача знаний и традиций"),
        ("Служение", "Служение общему благу и эволюции"),
        ("Память", "Сохранение памяти предков"),
        ("Ответственность", "Ответственность за свой народ и планету"),
        ("Гармония", "Баланс человека с природой и космосом"),
    ]
    for name, desc in core:
        if name not in seen:
            vals.insert(0, {
                "id": f"val_{len(vals)+1:03d}",
                "name": name,
                "description": desc,
                "strength": 0.9,
            })

    return vals


def extract_characters(characters_data: dict, book_doc: dict, deep_chars_data: dict) -> list:
    """Извлечение персонажей с главами из BOOK_DOCUMENT и описаниями из глубоких профилей."""
    chars = []
    seen = set()

    # Построить индекс глав по именам персонажей (из BOOK_DOCUMENT)
    chapter_index: dict[str, list[int]] = {}
    chapters = book_doc.get("content", {}).get("chapters", [])
    for i, ch in enumerate(chapters):
        ch_text = json.dumps(ch, ensure_ascii=False).lower()
        for entry in characters_data.get("characters", []):
            name = entry.get("name", "").strip()
            if name and name.lower() in ch_text:
                chapter_index.setdefault(name, []).append(i + 1)

    # Прочитать глубокие профили
    deep_profiles: dict[str, dict] = {}
    if isinstance(deep_chars_data, dict):
        for key, profile in deep_chars_data.items():
            if isinstance(profile, dict) and "name" in profile:
                deep_profiles[profile["name"]] = profile

    for ch in characters_data.get("characters", []):
        name = ch.get("name", "").strip()
        if name and name not in seen:
            seen.add(name)
            deep = deep_profiles.get(name, {})
            chapters_list = chapter_index.get(name, [])
            chars.append({
                "id": f"char_{len(chars)+1:03d}",
                "name": name,
                "aliases": ch.get("aliases", []) + deep.get("aliases", []),
                "type": ch.get("type", deep.get("type", "secondary")),
                "archetype": deep.get("archetype", ch.get("archetype", "")),
                "description": deep.get("description", ch.get("description", "")),
                "values": deep.get("values", ch.get("values", [])),
                "first_chapter": min(chapters_list) if chapters_list else None,
                "last_chapter": max(chapters_list) if chapters_list else None,
            })

    # Known characters from book
    known = [
        ("Велик", ["Велиусмус", "Великосвет", "Вел"], "main", "Искатель", "Главный герой, пилот из Океании"),
        ("Славный", ["Мирослав", "Слав"], "main", "Наставник", "Первый встретивший Велика, учитель"),
        ("Световит", [], "main", "Мудрец", "Старший Брат, объясняющий законы мироздания"),
        ("Вера", ["Вероника"], "secondary", "Проводник", "Жрица Гипербореи"),
        ("Влад", ["Владислав"], "secondary", "Хранитель", "Муж Веры"),
        ("Учитель", ["Архат"], "main", "Архат", "Высшее Существо Космоса"),
        ("Радомир", [], "secondary", "Лидер", "Глава общины переселенцев"),
        ("Яснобор", [], "secondary", "Наставник", "Посвящённый"),
        ("Коловед", [], "secondary", "Наставник", "Посвящённый"),
        ("Любомир", [], "secondary", "Учёный", "Преподаватель звуковедения"),
    ]
    for name, aliases, ctype, arch, desc in known:
        if name not in seen:
            chars.insert(0, {
                "id": f"char_{len(chars)+1:03d}",
                "name": name,
                "aliases": aliases,
                "type": ctype,
                "archetype": arch,
                "description": desc,
                "values": [],
                "first_chapter": None,
                "last_chapter": None,
            })

    return chars


def extract_symbols(symbols_data: dict, book_doc: dict) -> list:
    """Извлечение символов с главами из BOOK_DOCUMENT."""
    syms = []
    seen = set()

    chapters = book_doc.get("content", {}).get("chapters", [])
    chapter_index: dict[str, list[int]] = {}
    for i, ch in enumerate(chapters):
        ch_text = json.dumps(ch, ensure_ascii=False).lower()
        for entry in symbols_data.get("symbols", []):
            name = entry.get("name", "").strip()
            if name and name.lower() in ch_text:
                chapter_index.setdefault(name, []).append(i + 1)

    for s in symbols_data.get("symbols", []):
        name = s.get("name", "").strip()
        if name and name not in seen:
            seen.add(name)
            syms.append({
                "id": f"sym_{len(syms)+1:03d}",
                "name": name,
                "meaning": s.get("meaning", ""),
                "chapters": chapter_index.get(name, s.get("chapters", [])),
            })

    core = [
        ("Аркаим", "Святилище древней мудрости"),
        ("Пещера", "Место пробуждения, контакта с Высшим Миром"),
        ("Аэролет", "Технология, соединяющая миры"),
        ("Импульс", "Космический сигнал к началу преобразований"),
        ("Иерархия Света", "Цепь творческих сил Космоса"),
    ]
    for name, meaning in core:
        if name not in seen:
            syms.insert(0, {
                "id": f"sym_{len(syms)+1:03d}",
                "name": name,
                "meaning": meaning,
                "chapters": [],
            })

    return syms


def extract_conflicts(plot: dict) -> list:
    """Извлечение конфликтов."""
    confs = []
    seen = set()

    for c in plot.get("conflicts", []):
        if isinstance(c, str) and c not in seen:
            seen.add(c)
            confs.append({
                "id": f"conf_{len(confs)+1:03d}",
                "name": c,
                "type": "external" if any(w in c.lower() for w in ["между", "противо", "борьб"]) else "internal",
            })

    core = [
        ("Материя vs Дух", "moral"),
        ("Цивилизация в упадке vs Возрождение", "external"),
        ("Вмешательство высших сил vs Свободная воля", "moral"),
        ("Забвение знаний vs Память предков", "internal"),
        ("Хаос vs Гармония", "external"),
    ]
    for name, ctype in core:
        if name not in seen:
            confs.insert(0, {
                "id": f"conf_{len(confs)+1:03d}",
                "name": name,
                "type": ctype,
            })

    return confs


def extract_world_entities() -> list:
    """Извлечение сущностей мира."""
    entities = [
        {"name": "Гиперборея", "type": "civilization", "description": "Северная прародина, хранящая духовные истины",
         "values": ["знание", "гармония", "служение"], "related_to": ["Наставники", "Аркаим"],
         "conflict_with": ["Материальный путь Атлантиды"]},
        {"name": "Атлантида", "type": "civilization", "description": "Цивилизация на пороге материального тупика",
         "values": ["технологии", "власть"], "related_to": ["Велик"],
         "conflict_with": ["Гиперборея"]},
        {"name": "Аркаим", "type": "location", "description": "Священное место, хранящее память о Гиперборее",
         "values": ["память", "духовность"], "related_to": ["Страна Городов", "Гиперборея"],
         "conflict_with": []},
        {"name": "Наставники", "type": "concept", "description": "Мудрецы, проводники, обладающие скрытыми знаниями",
         "values": ["мудрость", "служение", "истина"], "related_to": ["Учителя Человечества", "Гиперборея"],
         "conflict_with": ["Невежество"]},
        {"name": "Учителя Человечества", "type": "concept", "description": "Высшие сущности, источник Учения",
         "values": ["любовь", "истина", "эволюция"], "related_to": ["Наставники", "Иерархия Света"],
         "conflict_with": []},
        {"name": "Кали Юга", "type": "concept", "description": "Тёмная эпоха упадка и деградации",
         "values": [], "related_to": ["Сати Юга", "Циклы"],
         "conflict_with": ["Сати Юга"]},
        {"name": "Сати Юга", "type": "concept", "description": "Эпоха возрождения и духовного подъёма",
         "values": ["духовность", "гармония"], "related_to": ["Кали Юга", "Циклы"],
         "conflict_with": ["Кали Юга"]},
    ]
    return entities


def extract_catalog_texts(enriched_catalog: dict, max_items: int = 200) -> list:
    """Извлечь ключевые тексты из enriched_catalog для RAG-индекса в геноме."""
    texts = []
    seen = set()
    catalog_items = enriched_catalog if isinstance(enriched_catalog, list) else enriched_catalog.get("chunks", [])
    for item in catalog_items[:max_items]:
        text = item.get("text", "") or item.get("content", "")
        if len(text) < 40:
            continue
        # Дедупликация по первым 100 символам
        key = text.strip()[:100].lower()
        if key in seen:
            continue
        seen.add(key)
        source = item.get("metadata", {}).get("source", "book")
        texts.append({
            "text": text[:1000],
            "source": source,
            "chapter": item.get("metadata", {}).get("chapter_title", ""),
            "characters": item.get("metadata", {}).get("characters", [])[:5],
        })
    return texts


# ── Narrative Arc Extraction ────────────────────────

CHARACTER_ARC_TYPES = {
    "Искатель": "hero_journey",
    "Мудрец": "transformation",
    "Хранитель": "rise_fall",
    "Проводник": "hero_journey",
    "Архат": "transformation",
    "Наставник": "rise_fall",
    "Лидер": "rise_fall",
    "Учёный": "transformation",
}

ARC_STATES = ["introduction", "rise", "peak", "fall", "resolution"]

EMOTION_TO_ARC_STATE = {
    "warm_intimate": "introduction",
    "melancholic_dark": "fall",
    "hopeful_golden": "rise",
    "dark_mystical": "rise",
    "dramatic_contrast": "peak",
    "ethereal_light": "resolution",
    "sepia_flashback": "fall",
    "ceremonial_warm": "peak",
    "sacred_glow": "resolution",
    "conflict": "peak",
    "bright_warm": "rise",
    "calm_acceptance": "resolution",
}


def _arc_provenance(module: str, entity_id: str) -> list[str]:
    """Провенанс дуги: из какого модуля генома и какой сущности построена."""
    return [f"genome.modules.{module}:{entity_id}"]


def _character_incomplete_reason(ch: dict, char_id: str, archetype: str, beats: list) -> str:
    """Причина неполной связи персонажа (для пометки incomplete)."""
    reasons = []
    if not char_id:
        reasons.append("missing entity_id")
    if ch.get("first_chapter") is None or ch.get("last_chapter") is None:
        reasons.append("missing chapter bounds")
    if archetype and archetype not in CHARACTER_ARC_TYPES:
        reasons.append(f"unknown archetype: {archetype}")
    if not beats:
        reasons.append("no beats")
    return "; ".join(reasons)


def extract_character_arcs(chars: list, timeline: list) -> list[dict]:
    """Построить сюжетные дуги персонажей на основе архетипов и таймлайна."""
    arcs = []
    total_chapters = len(timeline) or 1

    for ch in chars:
        char_id = ch.get("id", "")
        name = ch.get("name", "")
        archetype = ch.get("archetype", "")
        first_ch = ch.get("first_chapter") or 1
        last_ch = ch.get("last_chapter") or total_chapters
        arc_type = CHARACTER_ARC_TYPES.get(archetype, "rise_fall")

        beats = []
        for i in range(1, total_chapters + 1):
            if i < first_ch or i > last_ch:
                continue
            # Определяем состояние по позиции персонажа в дуге
            pos = (i - first_ch) / max(last_ch - first_ch, 1)
            if pos < 0.2:
                state = "introduction"
                intensity = round(0.3 + pos * 0.5, 2)
            elif pos < 0.5:
                state = "rise"
                intensity = round(0.5 + pos * 0.3, 2)
            elif pos < 0.7:
                state = "peak"
                intensity = round(0.8 + (pos - 0.5) * 0.2, 2)
            elif pos < 0.9:
                state = "fall"
                intensity = round(0.6 - (pos - 0.7) * 0.3, 2)
            else:
                state = "resolution"
                intensity = round(0.3, 2)

            beats.append({
                "chapter": i,
                "state": state,
                "emotion": _infer_beat_emotion(state, archetype),
                "intensity": min(intensity, 1.0),
                "description": f"{name}: {ARC_STATE_LABELS.get(state, state)}",
            })

        incomplete = not char_id or ch.get("first_chapter") is None or ch.get("last_chapter") is None
        if char_id and archetype and archetype not in CHARACTER_ARC_TYPES:
            incomplete = True
        arcs.append({
            "type": "character_arc",
            "entity_id": char_id,
            "name": f"Путь {name}",
            "arc_type": arc_type,
            "beats": beats,
            "resolution": _infer_resolution(archetype),
            "provenance": _arc_provenance("characters", char_id or name),
            "incomplete": incomplete,
            "incomplete_reason": _character_incomplete_reason(ch, char_id, archetype, beats),
        })

    return arcs


def extract_conflict_arcs(confs: list, timeline: list) -> list[dict]:
    """Построить дуги конфликтов — эскалация по главам."""
    arcs = []
    total = len(timeline) or 1

    for ci, conf in enumerate(confs):
        conf_name = conf.get("name", f"conflict_{ci}")
        peak_chapter = max(total // 2, 1)
        beats = []

        for i in range(1, total + 1):
            if i < peak_chapter * 0.5:
                state = "introduction"
                intensity = round(0.2 + (i / peak_chapter) * 0.3, 2)
            elif i < peak_chapter:
                state = "rise"
                intensity = round(0.5 + (i / peak_chapter) * 0.3, 2)
            elif i == peak_chapter:
                state = "peak"
                intensity = 1.0
            elif i < peak_chapter * 1.5:
                state = "fall"
                intensity = round(0.7 - (i / peak_chapter) * 0.2, 2)
            else:
                state = "resolution"
                intensity = round(0.3, 2)

            beats.append({
                "chapter": i,
                "state": state,
                "emotion": "conflict" if state == "peak" else "tension" if state in ("rise", "fall") else "calm",
                "intensity": min(intensity, 1.0),
                "description": f"Конфликт «{conf_name}»: {ARC_STATE_LABELS.get(state, state)}",
            })

        conf_id = conf.get("id", "")
        conf_prov_id = conf_id or conf_name
        arcs.append({
            "type": "plot_arc",
            "entity_id": conf_id or conf_name,
            "name": f"Конфликт: {conf_name}",
            "arc_type": "rise_fall",
            "beats": beats,
            "resolution": f"Конфликт «{conf_name}» разрешён",
            "provenance": _arc_provenance("conflicts", conf_prov_id),
            "incomplete": not conf_id,
            "incomplete_reason": "" if conf_id else "missing entity_id",
        })

    return arcs


def extract_thematic_arcs(themes: list, timeline: list) -> list[dict]:
    """Построить дуги тем — их сила по главам."""
    arcs = []
    total = len(timeline) or 1

    for th in themes:
        theme_name = th.get("name", "")
        base_strength = th.get("strength", 0.5)
        beats = []

        for i in range(1, total + 1):
            pos = i / total
            if pos < 0.3:
                intensity = round(base_strength * (0.5 + pos), 2)
            elif pos < 0.7:
                intensity = round(base_strength * (0.8 + (pos - 0.3) * 0.5), 2)
            else:
                intensity = round(base_strength * (1.1 - (pos - 0.7)), 2)

            beats.append({
                "chapter": i,
                "state": "rise" if pos < 0.7 else "fall",
                "emotion": _infer_beat_emotion("rise" if pos < 0.7 else "fall", ""),
                "intensity": min(intensity, 1.0),
                "description": f"Тема «{theme_name}»: {intensity:.0%}",
            })

        theme_id = th.get("id", "")
        theme_prov_id = theme_id or theme_name
        arcs.append({
            "type": "thematic_arc",
            "entity_id": theme_id or theme_name,
            "name": f"Тема: {theme_name}",
            "arc_type": "rise_fall",
            "beats": beats,
            "resolution": f"Тема «{theme_name}» проведена через {total} глав",
            "provenance": _arc_provenance("themes", theme_prov_id),
            "incomplete": not theme_id,
            "incomplete_reason": "" if theme_id else "missing entity_id",
        })

    return arcs


def extract_narrative_arcs(chars: list, confs: list, themes: list, timeline: list) -> list[dict]:
    """Собрать все сюжетные дуги: персонажи, конфликты, темы."""
    arcs = []
    arcs.extend(extract_character_arcs(chars, timeline))
    arcs.extend(extract_conflict_arcs(confs, timeline))
    arcs.extend(extract_thematic_arcs(themes, timeline))
    return arcs


ARC_STATE_LABELS = {
    "introduction": "Введение",
    "rise": "Подъём",
    "peak": "Кульминация",
    "fall": "Спад",
    "resolution": "Развязка",
}


def _infer_beat_emotion(state: str, archetype: str = "") -> str:
    mapping = {
        "introduction": "warm_intimate",
        "rise": "hopeful_golden",
        "peak": "dramatic_contrast",
        "fall": "melancholic_dark",
        "resolution": "calm_acceptance",
    }
    return mapping.get(state, "neutral")


def _infer_resolution(archetype: str) -> str:
    mapping = {
        "Искатель": "Обрёл знание и предназначение",
        "Мудрец": "Передал знание следующему поколению",
        "Хранитель": "Сохранил наследие ценой жертвы",
        "Проводник": "Привёл ищущих к цели",
        "Архат": "Достиг просветления",
        "Наставник": "Воспитал достойного ученика",
        "Лидер": "Привёл народ к гармонии",
    }
    return mapping.get(archetype, "Завершил свой путь")


def extract_screenplay(screenplay_path=None):
    """Extract screenplay genome data from screenplay_extracts.json + SYNOPSIS."""
    import re as _re
    from pathlib import Path as _P
    kb = _P("core/KNOWLEDGE")
    extracts_path = kb / "screenplay_extracts.json"
    if not extracts_path.exists():
        return {"characters": [], "locations": [], "scenes": [], "dialogues": []}
    extracts = json.loads(extracts_path.read_text(encoding="utf-8"))

    characters = []
    for o in extracts.get("oceania_officers", []):
        characters.append({
            "name": o.get("name", ""),
            "role": o.get("rank", ""),
            "description": o.get("description", ""),
            "source": "screenplay",
        })
    # Add Stranger
    stranger_desc = extracts.get("the_stranger", "")
    if stranger_desc:
        characters.append({
            "name": "Незнакомец",
            "role": "гипербореец",
            "description": stranger_desc,
            "source": "screenplay",
        })

    locations = []
    teaching_room = extracts.get("teaching_room", {})
    if teaching_room:
        locations.append({
            "name": "Комната обучения",
            "description": teaching_room.get("description", ""),
            "type": "teaching",
        })

    dialogues = []
    for d in extracts.get("key_dialogues", []):
        dialogues.append({
            "participants": d.get("participants", []),
            "topic": d.get("topic", ""),
            "excerpt": d.get("excerpt", ""),
            "significance": d.get("significance", ""),
            "scene": d.get("scene", ""),
        })

    return {
        "characters": characters,
        "locations": locations,
        "scenes": [],
        "dialogues": dialogues,
        "total_characters": len(characters),
        "total_dialogues": len(dialogues),
    }


def main():
    log("=" * 60)
    log(f"BOOK GENOME EXTRACTOR v{GENOME_VERSION}")
    log("=" * 60)

    # 1. Load sources
    log("\n1. Loading sources...")
    book_doc = load_json(KNOWLEDGE / "BOOK_DOCUMENT.json")
    plot = load_json(KNOWLEDGE / "PLOT.json")
    characters_data = load_json(KNOWLEDGE / "CHARACTERS.json")
    philosophy = load_json(KNOWLEDGE / "PHILOSOPHY.json")
    symbols_data = load_json(KNOWLEDGE / "SYMBOLS.json")
    values_data = load_json(KNOWLEDGE / "VALUES.json")
    chatpdf = load_json(KNOWLEDGE / "chatpdf_answers.json")
    deep_chars_data = load_json(KNOWLEDGE / "deep_characters.json")
    enriched_catalog = load_json(KNOWLEDGE / "enriched_catalog.json")

    # 2. Extract modules
    log("\n2. Extracting themes...")
    themes = extract_themes(philosophy, chatpdf)
    save_genome(themes, "themes.json")

    log("\n3. Extracting values...")
    vals = extract_values(values_data)
    save_genome(vals, "values.json")

    log("\n4. Extracting characters...")
    chars = extract_characters(characters_data, book_doc, deep_chars_data)
    save_genome(chars, "characters.json")

    log("\n5. Extracting symbols...")
    syms = extract_symbols(symbols_data, book_doc)
    save_genome(syms, "symbols.json")

    log("\n6. Extracting conflicts...")
    confs = extract_conflicts(plot)
    save_genome(confs, "conflicts.json")

    log("\n7. Extracting catalog texts for RAG...")
    catalog_texts = extract_catalog_texts(enriched_catalog)
    save_genome(catalog_texts, "catalog_texts.json")
    log(f"  RAG texts: {len(catalog_texts)}")

    log("\n8. Building timeline...")
    chapters = book_doc.get("content", {}).get("chapters", [])
    timeline = []
    for i, ch in enumerate(chapters):
        title = ch.get("title", f"Глава {i}")
        timeline.append({
            "id": f"ev_{i+1:03d}",
            "event": f"Глава о {title}" if title not in ["Пролог", "Эпилог"] else title,
            "chapter": ch.get("number", i),
            "title": title,
        })
    save_genome(timeline, "timeline.json")

    log("\n8a. Extracting narrative arcs...")
    from visualization.meaning_to_visual import EMOTION_MAP as _EM
    narrative_arcs = extract_narrative_arcs(chars, confs, themes, timeline)
    save_genome(narrative_arcs, "narrative_arcs.json")
    log(f"  Arc types: {len(narrative_arcs)} ({', '.join(a['type'] for a in narrative_arcs)})")

    log("\n8b. Extracting world entities...")
    entities = extract_world_entities()
    save_genome(entities, "world_entities.json")

    # 9. Build full genome
    log("\n9. Building full GENOME...")
    ai_data = load_json(KNOWLEDGE / "AUTHOR_INTENT.json")

    # Обогатить author_intent философией
    main_philosophy = philosophy.get("main_philosophy", "")
    if main_philosophy and not ai_data.get("main_message"):
        ai_data["main_message"] = main_philosophy[:500]

    full_genome = {
        "book_id": "nasledie-arkaima",
        "title": "Наследие Аркаима",
        "author": "ОВладимирович",
        "version": GENOME_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "modules": {
            "themes": themes,
            "values": vals,
            "characters": chars,
            "symbols": syms,
            "philosophy": philosophy.get("concepts", []),
            "conflicts": confs,
            "timeline": timeline,
            "narrative_arcs": narrative_arcs,
                "screenplay": extract_screenplay(),
        },
        "author_intent": {
            "main_message": ai_data.get("main_message", ""),
            "secondary_messages": ai_data.get("secondary_messages", []),
            "desired_reader_transformation": ai_data.get("desired_reader_transformation", []),
            "questions_for_reader": ai_data.get("questions_for_reader", []),
            "core_values": ai_data.get("core_values", []),
            "misinterpretation_risks": ai_data.get("misinterpretation_risks", []),
        },
        "world_entities": entities,
        "catalog_texts": catalog_texts[:100],
        "validation": {"score": None, "passed": None},
    }

    genome_path = GENOME_DIR / f"GENOME_v{GENOME_VERSION}.json"
    genome_path.write_text(
        json.dumps(full_genome, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )
    log(f"  Saved: GENOME/{genome_path.name}")

    # 10. Validate
    log("\n10. Validating genome...")
    passed, errors, genome = validate_genome(full_genome)
    if passed:
        log("  VALIDATION PASSED")
    else:
        log(f"  VALIDATION FAILED: {len(errors)} errors")
        for e in errors[:5]:
            log(f"    - {e}")

    # 11. Stats
    log("\n" + "=" * 60)
    log("GENOME STATS:")
    log(f"  Themes:     {len(themes)}")
    log(f"  Values:     {len(vals)}")
    log(f"  Characters: {len(chars)}")
    log(f"  Symbols:    {len(syms)}")
    log(f"  Conflicts:  {len(confs)}")
    log(f"  Timeline:   {len(timeline)}")
    log(f"  Entities:   {len(entities)}")
    log(f"  RAG texts:  {len(catalog_texts)}")
    total_arcs = len(narrative_arcs)
    char_arcs = sum(1 for a in narrative_arcs if a["type"] == "character_arc")
    plot_arcs = sum(1 for a in narrative_arcs if a["type"] == "plot_arc")
    thematic_arcs = sum(1 for a in narrative_arcs if a["type"] == "thematic_arc")
    log(f"  Narrative arcs: {total_arcs} ({char_arcs} char, {plot_arcs} plot, {thematic_arcs} thematic)")
    log(f"  Validation: {'PASSED' if passed else 'FAILED'}")
    log("=" * 60)

    return passed


if __name__ == "__main__":
    main()
