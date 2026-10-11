"""
generate_scenes_comfyui.py — пакетная генерация изображений через ComfyUI.

Единый скрипт генерации сцен книги «Наследие Аркаима» через ComfyUI.
Поддерживает локальный режим и Colab (Cloudflare Tunnel).

Запуск:
    python scripts/generate_scenes_comfyui.py

Настройка:
    - Локальный ComfyUI: запустить ComfyUI на порту 8188 (по умолчанию)
    - Colab: установить COMFYUI_URL в .env на URL Cloudflare Tunnel

Требования:
    - ComfyUI запущен (локально или через Colab)
    - SDXL checkpoint загружен
"""
import asyncio
import json
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = PROJECT_ROOT / "core" / "KNOWLEDGE"
OUTPUT_DIR = PROJECT_ROOT / "docs" / "images" / "scenes"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Добавляем путь к ядру
sys.path.insert(0, str(PROJECT_ROOT / "core" / "CORE"))

# Загружаем .env (для COMFYUI_URL)
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / "runtime" / ".env")

# URL ComfyUI: из env или локальный по умолчанию
COMFYUI_URL = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")


async def generate_all():
    """Сгенерировать все сцены через ComfyUI."""
    # Загружаем промпты
    prompts_file = KNOWLEDGE_DIR / "SCENE_PROMPTS.json"
    if not prompts_file.exists():
        print(f"ERROR: {prompts_file} not found")
        return

    data = json.loads(prompts_file.read_text(encoding="utf-8"))
    scenes = data["scenes"]
    print(f"Found {len(scenes)} scenes to generate")
    print(f"ComfyUI URL: {COMFYUI_URL}")

    # Импортируем ComfyUI provider
    try:
        from providers.image.comfyui import ComfyUIProvider
        provider = ComfyUIProvider(base_url=COMFYUI_URL)
    except Exception as e:
        print(f"ERROR: Cannot initialize ComfyUI provider: {e}")
        print(f"Make sure ComfyUI is running at {COMFYUI_URL}")
        return

    # Проверяем здоровье ComfyUI
    health = await provider.health()
    if not health:
        print("WARNING: ComfyUI health check failed")
        print("Continuing anyway...")

    # Генерируем каждую сцену
    results = []
    for i, scene in enumerate(scenes, 1):
        scene_id = scene["id"]
        title = scene["title"]
        prompt = scene["prompt"]
        emotion = scene.get("emotion", "")
        style = scene.get("style", "")

        print(f"\n[{i}/{len(scenes)}] {title}")
        print(f"  Emotion: {emotion}")
        print(f"  Prompt: {prompt[:100]}...")

        # Формируем негативный промпт
        negative = "blurry, low quality, deformed, ugly, bad anatomy, watermark, text, signature"

        try:
            start = time.time()
            image_bytes = await provider.generate(
                prompt=(prompt, negative),
                size="1024x1024",
            )
            elapsed = time.time() - start

            # Сохраняем
            output_path = OUTPUT_DIR / f"{scene_id}.png"
            output_path.write_bytes(image_bytes)

            results.append({
                "id": scene_id,
                "title": title,
                "path": str(output_path),
                "size": len(image_bytes),
                "time": round(elapsed, 1),
                "status": "ok",
            })
            print(f"  OK: {output_path.name} ({len(image_bytes)} bytes, {elapsed:.1f}s)")

        except Exception as e:
            results.append({
                "id": scene_id,
                "title": title,
                "error": str(e),
                "status": "error",
            })
            print(f"  ERROR: {e}")

    # Сохраняем отчёт
    report_path = OUTPUT_DIR / "generation_report.json"
    report_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Итоги
    ok = sum(1 for r in results if r["status"] == "ok")
    errors = sum(1 for r in results if r["status"] == "error")
    print(f"\n{'='*50}")
    print(f"Generated: {ok}/{len(scenes)} scenes")
    if errors:
        print(f"Errors: {errors}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    asyncio.run(generate_all())