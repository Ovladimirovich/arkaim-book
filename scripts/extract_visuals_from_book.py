"""
Скрипт: LLM-пайплайн для извлечения Visual Genome из текста книги.
Читает BOOK_DOCUMENT.json, разбивает на сцены, отправляет в GigaChat,
парсит ответ, сохраняет в Visual Genome.
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
GENOME_PATH = GENOME_DIR / f"GENOME_v{config.GENOME_VERSION}.json"

SCENE_BREAK_KEYWORDS = [
    "глава", "часть", "***", "— — —",
    "прошло", "тем временем", "на следующий день",
    "через несколько", "вернёмся", "тем временем",
]


def log(msg):
    print(f"[LLM->Visuals] {msg}")


def load_book() -> dict:
    """Загрузить книгу из BOOK_DOCUMENT.json."""
    path = KNOWLEDGE_DIR / "BOOK_DOCUMENT.json"
    if not path.exists():
        log(f"BOOK_DOCUMENT.json не найден: {path}")
        log("Пробую SOURCE_OF_TRUTH/...")
        alt_path = KNOWLEDGE_DIR.parent / "SOURCE_OF_TRUTH" / "book.json"
        if alt_path.exists():
            return json.loads(alt_path.read_text(encoding="utf-8"))
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def split_into_scenes(chapter_text: str) -> list[str]:
    """Разбить текст главы на сцены по ключевым маркерам."""
    import re
    pattern = "|".join(re.escape(kw) for kw in SCENE_BREAK_KEYWORDS)
    scenes = re.split(pattern, chapter_text, flags=re.IGNORECASE)
    return [s.strip() for s in scenes if len(s.strip()) > 100]


async def extract_visuals_with_llm(scene_text: str, chapter: int, scene_index: int) -> dict | None:
    """Отправить сцену в LLM, получить структурированный Visual Genome."""
    try:
        from llm_client import LLMClient
        llm = LLMClient()

        prompt = (
            f"Ты — визуальный редактор книги «Наследие Аркаима».\n"
            f"Из текста сцены (глава {chapter}) извлеки визуальные образы.\n\n"
            f"Текст сцены:\n{scene_text[:3000]}\n\n"
            f"Ответь строго в JSON:\n"
            f"{{\n"
            f'  "scene": {{\n'
            f'    "title": "короткое название сцены",\n'
            f'    "characters": ["имена персонажей"],\n'
            f'    "location": "название локации",\n'
            f'    "emotion": "эмоциональная окраска",\n'
            f'    "meaning_tags": ["теги"]\n'
            f'  }},\n'
            f'  "character_visuals": [{{\n'
            f'    "character_id": "имя",\n'
            f'    "age_range": "возраст",\n'
            f'    "clothing": "одежда",\n'
            f'    "color_palette": ["#HEX"]\n'
            f'  }}],\n'
            f'  "location_visuals": [{{\n'
            f'    "location_id": "локация",\n'
            f'    "architecture": "архитектура",\n'
            f'    "atmosphere": "атмосфера",\n'
            f'    "lighting": "освещение",\n'
            f'    "palette": ["#HEX"]\n'
            f'  }}]\n'
            f"}}\n\n"
            f"Если данных нет — оставь пустой массив. "
            f"Только JSON, без объяснений."
        )

        response = await llm.chat([
            {"role": "system", "content": "Ты — визуальный редактор. Отвечай только JSON."},
            {"role": "user", "content": prompt},
        ])

        cleaned = response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned.replace("```json", "").replace("```", "")

        result = json.loads(cleaned)
        return result

    except ImportError:
        log("LLMClient не найден. Установите зависимости.")
        return None
    except json.JSONDecodeError as e:
        log(f"  Ошибка парсинга JSON: {e}")
        return None
    except Exception as e:
        log(f"  Ошибка LLM: {e}")
        return None


def merge_results(all_results: list[dict]) -> dict:
    """Слить результаты всех сцен в один Visual Genome."""
    merged = {
        "scenes": [],
        "character_visuals": [],
        "location_visuals": [],
    }
    seen_chars = set()
    seen_locs = set()

    for result in all_results:
        if not result:
            continue
        if "scene" in result:
            merged["scenes"].append(result["scene"])
        for cv in result.get("character_visuals", []):
            char_id = cv.get("character_id", "")
            if char_id and char_id not in seen_chars:
                seen_chars.add(char_id)
                merged["character_visuals"].append(cv)
        for lv in result.get("location_visuals", []):
            loc_id = lv.get("location_id", "")
            if loc_id and loc_id not in seen_locs:
                seen_locs.add(loc_id)
                merged["location_visuals"].append(lv)

    return merged


def save_output(data: dict, name: str):
    CURRENT_DIR.mkdir(parents=True, exist_ok=True)
    path = CURRENT_DIR / name
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    log(f"  Saved: GENOME/CURRENT/{name}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="LLM-пайплайн Visual Genome")
    parser.add_argument("--chapters", type=str, default="", help="Диапазон глав (например 1-10)")
    parser.add_argument("--force", action="store_true", help="Перезаписать существующие")
    parser.add_argument("--dry-run", action="store_true", help="Только показать, что будет сделано")
    args = parser.parse_args()

    log("=" * 50)
    log("LLM-пайплайн: Извлечение Visual Genome из книги")
    log("=" * 50)

    book = load_book()
    if not book:
        log("Книга не загружена.")
        return

    chapters = book.get("content", {}).get("chapters", book.get("chapters", []))
    log(f"Загружено глав: {len(chapters)}")

    # Фильтр по диапазону
    chapter_range = None
    if args.chapters:
        parts = args.chapters.split("-")
        try:
            start = int(parts[0])
            end = int(parts[1]) if len(parts) > 1 else start
            chapter_range = range(start, end + 1)
        except (ValueError, IndexError):
            log(f"Неверный диапазон: {args.chapters}")

    all_results = []
    total_chars = 0
    total_locs = 0

    import asyncio

    async def process_chapter(chapter_data, chapter_num):
        chapter_text = chapter_data.get("text", chapter_data.get("content", json.dumps(chapter_data, ensure_ascii=False)))
        if len(chapter_text) < 100:
            log(f"  Глава {chapter_num}: слишком короткая, пропуск")
            return []

        scenes = split_into_scenes(chapter_text)
        log(f"  Глава {chapter_num}: {len(scenes)} сцен")

        if args.dry_run:
            return []

        results = []
        for si, scene_text in enumerate(scenes):
            log(f"    Сцена {si + 1}/{len(scenes)}...")
            result = await extract_visuals_with_llm(scene_text, chapter_num, si)
            if result:
                results.append(result)
                log(f"      [OK] scene={result.get('scene', {}).get('title', '?')}")
        return results

    async def run_all():
        all_results = []
        total_chars = 0
        total_locs = 0

        for i, chapter in enumerate(chapters):
            chapter_num = i + 1
            if chapter_range and chapter_num not in chapter_range:
                continue
            chapter_results = await process_chapter(chapter, chapter_num)
            for r in chapter_results:
                all_results.append(r)
                total_chars += len(r.get("character_visuals", []))
                total_locs += len(r.get("location_visuals", []))

        return all_results, total_chars, total_locs

    all_results, total_chars, total_locs = asyncio.run(run_all())

    if args.dry_run:
        log("\nDry-run завершён. Для реального запуска уберите --dry-run.")
        return

    if not all_results:
        log("\nНет результатов. Проверьте подключение к LLM.")
        return

    merged = merge_results(all_results)

    log(f"\n{'=' * 50}")
    log(f"РЕЗУЛЬТАТЫ:")
    log(f"  Сцен:               {len(merged['scenes'])}")
    log(f"  Character visuals:  {len(merged['character_visuals'])}")
    log(f"  Location visuals:   {len(merged['location_visuals'])}")

    save_output(merged, "extracted_visuals.json")

    # Сохранить по отдельности для populate_visual_genome
    if merged["scenes"]:
        save_output(merged["scenes"], "scenes_from_llm.json")
    if merged["character_visuals"]:
        save_output(merged["character_visuals"], "character_visuals_from_llm.json")
    if merged["location_visuals"]:
        save_output(merged["location_visuals"], "location_visuals_from_llm.json")

    log(f"\nЗапустите populate_visual_genome.py для слияния:")
    if merged["scenes"]:
        log(f"  python scripts/populate_visual_genome.py --scenes GENOME/CURRENT/scenes_from_llm.json")
    if merged["character_visuals"]:
        log(f"  python scripts/populate_visual_genome.py --character-visuals GENOME/CURRENT/character_visuals_from_llm.json")
    if merged["location_visuals"]:
        log(f"  python scripts/populate_visual_genome.py --location-visuals GENOME/CURRENT/location_visuals_from_llm.json")

    log("=" * 50)


if __name__ == "__main__":
    main()
