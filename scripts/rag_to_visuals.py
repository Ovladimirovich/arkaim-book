"""
Скрипт: RAG-чанки ChromaDB → Visual Genome.
Сканирует 1037 чанков книги, ищет визуальные описания через regex,
группирует по персонажам/локациям, сохраняет в Visual Genome.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent / "ARKAIM_DIGITAL_CONSCIOUSNESS" / "CORE"
sys.path.insert(0, str(CORE_DIR))

from core.config import config

KNOWLEDGE_DIR = config.KNOWLEDGE_DIR
GENOME_DIR = config.GENOME_DIR
CURRENT_DIR = GENOME_DIR / "CURRENT"

# Стоп-слова — если значение состоит только из них, пропускаем
STOP_WORDS = {
    "и", "в", "на", "с", "по", "из", "у", "к", "о", "а", "но", "то",
    "что", "это", "для", "или", "не", "да", "от", "до", "за", "над",
    "под", "перед", "между", "когда", "где", "кто", "что", "такой",
    "так", "как", "же", "бы", "ли", "уж", "вот", "вон", "ну", "все",
    "его", "её", "их", "он", "она", "оно", "они", "мы", "вы", "ты",
    "я", "меня", "тебя", "себя", "нас", "вас", "них", "нему", "ней",
    "ним", "них", "него", "нее", "его", "её",
    "был", "была", "было", "были", "будет", "будут", "есть",
    "сказал", "сказала", "сказали", "говорит", "говорил",
    "стал", "стала", "стали", "стало",
    "мощь", "сила", "время", "раз", "человек",
    "этот", "эта", "это", "эти", "того", "тому", "том",
    "весь", "вся", "всё", "все", "сам", "сама", "сами",
    "чтобы", "потому", "поэтому", "затем", "тогда",
}

# Паттерны: каждый захватывает максимум 60 символов, до знака препинания
PATTERNS = [
    (r"на нём был[аи]?\s+(.{1,60}?)[\.\?!;]", "clothing"),
    (r"одет[а]?\s+(?:в\s+)?(.{1,60}?)[\.\?!;]", "clothing"),
    (r"одежд[ауи]\s+(.{1,60}?)[\.\?!;]", "clothing"),
    (r"плащ[а-я]*\s+(.{1,60}?)[\.\?!;]", "clothing"),
    (r"доспех[а-я]*\s+(.{1,60}?)[\.\?!;]", "clothing"),
    (r"сапог[а-я]*\s+(.{1,60}?)[\.\?!;]", "clothing"),
    (r"накидк[а-я]*\s+(.{1,60}?)[\.\?!;]", "clothing"),
    (r"кафтан[а-я]*\s+(.{1,60}?)[\.\?!;]", "clothing"),
    (r"стены\s+(?:были\s+)?(.{1,60}?)[\.\?!;]", "architecture"),
    (r"кам[её]нн[ыеых]{2}\s+(.{1,60}?)[\.\?!;]", "architecture"),
    (r"цвет\s+(.{1,60}?)[\.\?!;]", "color"),
    (r"свет\s+(.{1,60}?)[\.\?!;]", "lighting"),
    (r"атмосфер[а-я]*\s+(.{1,60}?)[\.\?!;]", "atmosphere"),
    (r"архитектур[а-я]*\s+(.{1,60}?)[\.\?!;]", "architecture"),
    (r"волос[ыа]\s+(.{1,60}?)[\.\?!;]", "hair"),
    (r"глаз[а-я]*\s+(.{1,60}?)[\.\?!;]", "eyes"),
]

# Ключевые слова персонажей — строгое совпадение через \b
CHARACTER_KEYWORDS = [
    "велик", "славный", "световит", "вера", "влад",
    "учитель", "радомир", "яснобор", "коловед", "любомир",
    "герой", "мудрец",
]

LOCATION_KEYWORDS = [
    "аркаим", "гиперборея", "атлантида", "пещера",
    "храм", "город", "гора", "лес", "река", "долина",
    "святилище", "алтарь",
]


def log(msg):
    print(f"[RAG->Visuals] {msg}")


def _is_noise(value: str) -> bool:
    """Проверить, что значение — не мусор.

    Критерии мусора:
    - Длина > 60 символов
    - Меньше 3 буквенных слов
    - Только стоп-слова
    - Содержит глаголы речи (сказал, ответил и т.д.)
    - Начинается с предлога/союза
    """
    cleaned = value.strip(" ,.!?;:-")
    if not cleaned or len(cleaned) < 3:
        return True
    if len(cleaned) > 60:
        return True

    words = re.findall(r"[а-яёa-z]+", cleaned.lower())
    if not words:
        return True

    # Словарь слов, указывающих на НЕ визуальное описание
    speech_verbs = {"сказал", "сказала", "ответил", "спросил", "промолвил",
                    "проговорил", "воскликнул", "произнёс", "заметил", "добавил",
                    "продолжил", "начал", "подумал", "решил", "понял",
                    "почувствовал", "увидел", "услышал", "вспомнил"}
    for w in words:
        if w in speech_verbs:
            return True

    # Если все слова — стоп-слова
    meaningful = [w for w in words if w not in STOP_WORDS and len(w) > 2]
    if not meaningful:
        return True

    # Меньше 2 осмысленных слов — слишком коротко для визуального описания
    if len(meaningful) < 2 and len(words) < 4:
        return True

    return False


def _mentions_entity(text_lower: str, keywords: list[str]) -> set[str]:
    """Проверить, упоминается ли сущность в тексте (только целые слова)."""
    mentioned = set()
    for kw in keywords:
        if re.search(rf"\b{re.escape(kw)}\b", text_lower):
            mentioned.add(kw.capitalize())
    return mentioned


def load_knowledge_files() -> list[dict]:
    """Загрузить enriched_catalog — чанки книги с метаданными."""
    catalog_path = KNOWLEDGE_DIR / "enriched_catalog.json"
    if not catalog_path.exists():
        log(f"enriched_catalog.json not found at {catalog_path}")
        return []

    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("chunks", data.get("catalog", []))
    return []


def extract_descriptions(chunks: list[dict]) -> dict:
    """Прогнать regex-паттерны по чанкам, сгруппировать по сущностям."""
    char_descriptions: dict[str, dict] = defaultdict(lambda: defaultdict(list))
    loc_descriptions: dict[str, dict] = defaultdict(lambda: defaultdict(list))

    for chunk in chunks:
        text = chunk.get("text", chunk.get("content", ""))
        if len(text) < 40:
            continue
        text_lower = text.lower()
        chunk_chars = chunk.get("metadata", {}).get("characters", [])
        chunk_chapter = chunk.get("metadata", {}).get("chapter_title", "")

        # Определить, какие персонажи/локации упоминаются (строго, целое слово)
        mentioned_chars = _mentions_entity(text_lower, CHARACTER_KEYWORDS)
        mentioned_locs = _mentions_entity(text_lower, LOCATION_KEYWORDS)

        if not mentioned_chars and not mentioned_locs:
            continue

        # Применить паттерны
        for pattern, field in PATTERNS:
            for match in re.finditer(pattern, text_lower):
                value = match.group(1).strip()
                if _is_noise(value):
                    continue

                for char_name in mentioned_chars:
                    existing = char_descriptions[char_name][field]
                    if value not in existing:
                        existing.append(value)

                for loc_name in mentioned_locs:
                    existing = loc_descriptions[loc_name][field]
                    if value not in existing:
                        existing.append(value)

    return {
        "characters": {k: dict(v) for k, v in char_descriptions.items()},
        "locations": {k: dict(v) for k, v in loc_descriptions.items()},
    }


def build_character_visuals(descriptions: dict) -> list[dict]:
    """Из собранных описаний собрать character_visuals."""
    visuals = []
    for char_name, fields in descriptions["characters"].items():
        visual = {
            "character_id": char_name,
            "age_range": "не указан",
            "build": "среднее",
            "hair": ", ".join(fields.get("hair", [])) or "не указаны",
            "eyes": ", ".join(fields.get("eyes", [])) or "не указаны",
            "clothing": ", ".join(fields.get("clothing", [])) or "не указана",
            "accessories": [],
            "color_palette": [f"#{hash(c) % 0xFFFFFF:06X}" for c in fields.get("color", [])] if fields.get("color") else ["earth tones"],
            "style_constants": [],
            "source": "rag_extracted",
        }
        if fields.get("clothing") or fields.get("hair") or fields.get("eyes"):
            visuals.append(visual)
    return visuals


def build_location_visuals(descriptions: dict) -> list[dict]:
    """Из собранных описаний собрать location_visuals."""
    visuals = []
    for loc_name, fields in descriptions["locations"].items():
        visual = {
            "location_id": loc_name.lower(),
            "type": "unknown",
            "architecture": ", ".join(fields.get("architecture", [])) or "не описана",
            "atmosphere": ", ".join(fields.get("atmosphere", [])) or "нейтральная",
            "lighting": ", ".join(fields.get("lighting", [])) or "естественный",
            "palette": [f"#{hash(c) % 0xFFFFFF:06X}" for c in fields.get("color", "палитра")] if fields.get("color") else ["#808080"],
            "source": "rag_extracted",
        }
        if fields.get("architecture") or fields.get("atmosphere"):
            visuals.append(visual)
    return visuals


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
    log("RAG-чанки -> Visual Genome")
    log("=" * 50)

    chunks = load_knowledge_files()
    log(f"Загружено чанков: {len(chunks)}")
    if not chunks:
        log("Нет данных для обработки.")
        return

    log("\nСканирование визуальных описаний...")
    descriptions = extract_descriptions(chunks)

    char_count = len(descriptions["characters"])
    loc_count = len(descriptions["locations"])
    log(f"Найдено описаний: {char_count} персонажей, {loc_count} локаций")

    for char_name, fields in descriptions["characters"].items():
        log(f"  [{char_name}]: {', '.join(f'{k}={len(v)}' for k,v in fields.items() if v)}")

    log("\nПостроение character_visuals...")
    char_visuals = build_character_visuals(descriptions)
    log(f"  Создано: {len(char_visuals)} визуалов персонажей")
    if char_visuals:
        save_output(char_visuals, "character_visuals_from_rag.json")

    log("\nПостроение location_visuals...")
    loc_visuals = build_location_visuals(descriptions)
    log(f"  Создано: {len(loc_visuals)} визуалов локаций")
    if loc_visuals:
        save_output(loc_visuals, "location_visuals_from_rag.json")

    total_char_visuals = len(char_visuals)
    total_loc_visuals = len(loc_visuals)

    log("\n" + "=" * 50)
    log(f"Итого: {total_char_visuals} character_visuals, {total_loc_visuals} location_visuals")
    log("=" * 50)


if __name__ == "__main__":
    main()
