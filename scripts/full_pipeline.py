"""
Полный пайплайн: GigaChat → сценарий → шоты → ComfyUI → видео.
"""
import asyncio
import json
import sys
import time

sys.path.insert(0, r"C:\ПРОЕКТ Наследие Аркаима\core")
sys.path.insert(0, r"C:\ПРОЕКТ Наследие Аркаима\core\CORE")
sys.path.insert(0, r"C:\ПРОЕКТ Наследие Аркаима\runtime")

SCREENPLAY_PROMPT = """Ты — сценарист фильма «Наследие Аркаима» — эпического фэнтези о древнем городе-обсерватории на Урале.

Напиши короткий сценарий из 4-5 шотов для одной сцены. Формат JSON:
{
  "title": "Название сцены",
  "description": "Краткое описание",
  "shots": [
    {
      "prompt": "Детальное описание кадра для AI-генерации изображения (на английском, 15-25 слов, включая: объект, освещение, атмосферу, стиль)",
      "duration": 3,
      "camera": "slow_dolly_in"
    }
  ]
}

Доступные движения камеры: static, slow_dolly_in, slow_dolly_out, slow_pan, slow_zoom_in, tracking, crane_up, orbit.

Стиль: cinematic fantasy, epic, dramatic lighting.
Тема сцены: Рассвет над Аркаимом — древний город пробуждается, лучи солнца падают на каменные стены и круговую планировку.

Верни ТОЛЬКО JSON без комментариев."""


async def generate_screenplay():
    """Шаг 1: Генерация сценария через GigaChat."""
    print("=" * 60)
    print("ШАГ 1: Генерация сценария через GigaChat")
    print("=" * 60)

    from llm_client import llm

    messages = [{"role": "user", "content": SCREENPLAY_PROMPT}]
    response = await llm.chat(messages, temperature=0.8, max_tokens=2000)

    # Parse JSON from response
    # Try to extract JSON from markdown code block
    if "```json" in response:
        response = response.split("```json")[1].split("```")[0].strip()
    elif "```" in response:
        response = response.split("```")[1].split("```")[0].strip()

    screenplay = json.loads(response)
    print(f"\nСценарий: {screenplay['title']}")
    print(f"Описание: {screenplay['description']}")
    print(f"Шотов: {len(screenplay['shots'])}")
    for i, shot in enumerate(screenplay['shots'], 1):
        print(f"  {i}. [{shot['camera']}] {shot['duration']}с — {shot['prompt'][:60]}...")

    return screenplay


async def create_project(screenplay):
    """Шаг 2: Создание проекта и шотов."""
    print("\n" + "=" * 60)
    print("ШАГ 2: Создание проекта и шотов")
    print("=" * 60)

    import httpx

    async with httpx.AsyncClient(timeout=30) as c:
        # Create project
        r = await c.post(
            "http://localhost:8642/book/film/create",
            params={
                "title": screenplay["title"],
                "description": screenplay["description"],
                "style": "cinematic_fantasy",
                "mood": "hopeful_golden",
            },
        )
        project = r.json()["data"]
        project_id = project["id"]
        print(f"Проект создан: {project_id}")

        # Add scene
        r = await c.post(
            f"http://localhost:8642/book/film/{project_id}/scenes",
            params={"scene_id": "scene_001", "order": 0},
        )
        scene = r.json()["data"]
        scene_id = scene["id"]
        print(f"Сцена добавлена: {scene_id}")

        # Add shots
        shot_ids = []
        for i, shot_data in enumerate(screenplay["shots"]):
            r = await c.post(
                f"http://localhost:8642/book/film/{project_id}/scenes/{scene_id}/shots",
                params={
                    "prompt": shot_data["prompt"],
                    "duration_sec": shot_data["duration"],
                    "camera_motion": shot_data["camera"],
                },
            )
            shot = r.json()["data"]
            shot_ids.append(shot["id"])
            print(f"  Шот {i+1}: {shot['id']} ({shot_data['duration']}с, {shot_data['camera']})")

        return project_id, scene_id, shot_ids


async def generate_shots(project_id, scene_id, shot_ids):
    """Шаг 3: Генерация изображений через ComfyUI."""
    print("\n" + "=" * 60)
    print("ШАГ 3: Генерация изображений (ComfyUI)")
    print("=" * 60)

    import httpx

    results = []
    async with httpx.AsyncClient(timeout=600) as c:
        for i, shot_id in enumerate(shot_ids, 1):
            print(f"\n  Генерация шота {i}/{len(shot_ids)} ({shot_id})...")
            t0 = time.time()

            r = await c.post(
                f"http://localhost:8642/book/film/{project_id}/scenes/{scene_id}/shots/{shot_id}/generate",
            )
            resp = r.json()["data"]

            elapsed = time.time() - t0
            print(f"  Готово за {elapsed:.0f}с: {resp['asset_id']}")

            results.append(resp)

    return results


async def assemble_video(project_id):
    """Шаг 4: Сборка видео."""
    print("\n" + "=" * 60)
    print("ШАГ 4: Сборка видео (ffmpeg)")
    print("=" * 60)

    import httpx

    async with httpx.AsyncClient(timeout=30) as c:
        # Start assembly
        r = await c.post(f"http://localhost:8642/book/film/{project_id}/assemble")
        print("Сборка запущена...")

        # Poll status
        for _ in range(60):
            await asyncio.sleep(2)
            r = await c.get(f"http://localhost:8642/book/film/{project_id}/assemble/status")
            status = r.json()["data"]

            if status["status"] == "complete":
                print(f"\nВидео собрано!")
                print(f"  Файл: {status['output_path']}")
                print(f"  Длительность: {status['duration_sec']}с")
                print(f"  Шотов: {status['shot_count']}")
                return status
            elif status["status"] == "failed":
                print(f"\nОшибка сборки: {status.get('error', 'unknown')}")
                return status

        print("Таймаут сборки")
        return None


async def main():
    """Полный пайплайн."""
    start = time.time()

    # Step 1: Generate screenplay
    screenplay = await generate_screenplay()

    # Step 2: Create project and shots
    project_id, scene_id, shot_ids = await create_project(screenplay)

    # Step 3: Generate images
    results = await generate_shots(project_id, scene_id, shot_ids)

    # Step 4: Assemble video
    video = await assemble_video(project_id)

    # Summary
    total_time = time.time() - start
    print("\n" + "=" * 60)
    print("ИТОГ")
    print("=" * 60)
    print(f"Проект: {project_id}")
    print(f"Шотов: {len(results)}")
    print(f"Сгенерировано: {sum(1 for r in results if r['status'] == 'completed')}/{len(results)}")
    if video and video.get("output_path"):
        print(f"Видео: {video['output_path']}")
    print(f"Общее время: {total_time:.0f}с")


if __name__ == "__main__":
    asyncio.run(main())
