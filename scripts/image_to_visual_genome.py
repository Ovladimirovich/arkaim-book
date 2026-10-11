"""
Скрипт: Изображение → Visual Genome (VLM pipeline).
Загружает изображение, отправляет в Vision-Language Model,
парсит ответ в структуру Visual Genome.

Требует GigaChat Vision или OpenRouter vision-модель.
"""
import base64
import json
import sys
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent / "ARKAIM_DIGITAL_CONSCIOUSNESS" / "CORE"
sys.path.insert(0, str(CORE_DIR))

from core.config import config

GENOME_DIR = config.GENOME_DIR
CURRENT_DIR = GENOME_DIR / "CURRENT"


def log(msg):
    print(f"[Image->Visual] {msg}")


def encode_image(image_path: Path) -> str:
    """Закодировать изображение в base64."""
    data = image_path.read_bytes()
    return base64.b64encode(data).decode("utf-8")


def analyze_with_llm(image_path: Path, entity_type: str = "character") -> dict | None:
    """Отправить изображение в LLM с vision-возможностями.

    Использует LLMClient для запроса к GigaChat/OpenRouter.
    Если vision недоступен — возвращает заглушку.
    """
    try:
        from llm_client import LLMClient
        llm = LLMClient()

        b64_image = encode_image(image_path)

        prompt = (
            f"Опиши эту {entity_type} в формате Visual Genome JSON.\n"
            f"Ответь строго в JSON:\n"
            f"{'{\"character_id\": \"...\", \"age_range\": \"...\", \"clothing\": \"...\", \"color_palette\": [...], \"accessories\": [...]}' if entity_type == 'character' else '{\"location_id\": \"...\", \"type\": \"...\", \"architecture\": \"...\", \"atmosphere\": \"...\", \"lighting\": \"...\", \"palette\": [...]}'}"
        )

        log(f"Отправка изображения в LLM...")
        response = llm.chat([
            {"role": "system", "content": "Ты — визуальный редактор. Отвечай только JSON."},
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}},
            ]},
        ])

        cleaned = response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned.replace("```json", "").replace("```", "")

        result = json.loads(cleaned)
        log("Успешно распознано")
        return result

    except ImportError:
        log("LLMClient не найден. VLM-пайплайн недоступен.")
        return None
    except Exception as e:
        log(f"Ошибка VLM: {e}")
        return None


def extract_colors_from_image(image_path: Path) -> list[str]:
    """Извлечь доминантные цвета из изображения (упрощённо).

    Возвращает заглушку. В реальности использует PIL/ColorThief.
    """
    try:
        from PIL import Image
        import colorsys

        img = Image.open(image_path).convert("RGB")
        img = img.resize((100, 100))
        pixels = list(img.getdata())

        # Простой подсчёт: группировка по hue
        color_buckets = {}
        for r, g, b in pixels:
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            bucket = int(h * 10)
            if bucket not in color_buckets:
                color_buckets[bucket] = {"count": 0, "r": 0, "g": 0, "b": 0}
            color_buckets[bucket]["count"] += 1
            color_buckets[bucket]["r"] += r
            color_buckets[bucket]["g"] += g
            color_buckets[bucket]["b"] += b

        top = sorted(color_buckets.values(), key=lambda x: x["count"], reverse=True)[:5]
        palette = []
        for entry in top:
            r = entry["r"] // entry["count"]
            g = entry["g"] // entry["count"]
            b = entry["b"] // entry["count"]
            palette.append(f"#{r:02X}{g:02X}{b:02X}")

        return palette
    except ImportError:
        log("PIL не найден, цвета не извлечены.")
        return []


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

    parser = argparse.ArgumentParser(description="Изображение → Visual Genome")
    parser.add_argument("image", type=str, help="Путь к изображению")
    parser.add_argument("--entity-type", choices=["character", "location"], default="character", help="Тип сущности")
    parser.add_argument("--entity-id", type=str, default="", help="ID сущности (если известен)")
    parser.add_argument("--no-llm", action="store_true", help="Не использовать LLM (только извлечение цветов)")
    args = parser.parse_args()

    image_path = Path(args.image)
    if not image_path.exists():
        log(f"Файл не найден: {image_path}")
        sys.exit(1)

    log(f"Анализ изображения: {image_path}")
    log(f"Тип сущности: {args.entity_type}")

    result = None
    if not args.no_llm:
        result = analyze_with_llm(image_path, args.entity_type)

    palette = extract_colors_from_image(image_path)
    if palette:
        log(f"Доминантные цвета: {palette}")

    if result:
        result["color_palette"] = palette or result.get("color_palette", [])
        if args.entity_id:
            result["character_id" if args.entity_type == "character" else "location_id"] = args.entity_id
        result["source"] = "vlm_pipeline"
        save_output(result, f"visual_from_image_{image_path.stem}.json")
        log(f"\nРезультат:\n{json.dumps(result, ensure_ascii=False, indent=2)}")
    else:
        log(f"\nVLM недоступен. Сохранены только цвета.")
        fallback = {
            "entity_id": args.entity_id or image_path.stem,
            "entity_type": args.entity_type,
            "color_palette": palette,
            "source": "vlm_fallback_colors_only",
        }
        save_output(fallback, f"colors_from_image_{image_path.stem}.json")


if __name__ == "__main__":
    main()
