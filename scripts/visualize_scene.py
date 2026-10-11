"""CLI: ручная/пакетная генерация визуализаций для сцен."""
import argparse
import asyncio
from pathlib import Path

# CORE_DIR уже настроен в sys.path стартовыми скриптами,
# но оставляем запасной вариант.
CORE_DIR = Path(__file__).resolve().parent.parent / "ARKAIM_DIGITAL_CONSCIOUSNESS" / "CORE"


def _ensure_core_path():
    import sys
    core_str = str(CORE_DIR)
    if core_str not in sys.path:
        sys.path.insert(0, core_str)


async def generate_scene(chapter: int, scene_id: str, output_path: Path):
    _ensure_core_path()
    from providers.image import ImageProviderChain
    from providers.image.mock import MockImageProvider
    from providers.image.svg_template import SVGTemplateProvider
    from visualization.scene_engine import SceneEngine
    from visualization.prompt_builder import PromptBuilder
    from pulse.pulse import BookPulse

    pulse = BookPulse()
    if not pulse.load():
        print("Ошибка загрузки Genome")
        return

    scene_engine = SceneEngine(genome=pulse.genome)
    prompt_builder = PromptBuilder(pulse=pulse)
    provider = ImageProviderChain([MockImageProvider(), SVGTemplateProvider()])

    scene = scene_engine.get_scene(chapter, scene_id)
    if not scene:
        print(f"Сцена не найдена: глава {chapter}, сцена {scene_id}")
        return

    char_visuals = {}
    for char_id in scene.get("characters", []):
        cv = scene_engine.get_character_visual(char_id)
        if cv:
            char_visuals[char_id] = cv

    location = scene_engine.get_location_visual(scene.get("location", ""))
    if not location:
        location = {"type": "unknown", "atmosphere": "", "architecture": "", "lighting": ""}

    prompt = prompt_builder.build_scene_prompt(scene, char_visuals, location)
    print(f"Промпт: {prompt}")

    image_bytes = await provider.generate(prompt)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image_bytes)
    print(f"Сохранено: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Генерация визуализации сцены")
    parser.add_argument("--chapter", type=int, required=True, help="Номер главы")
    parser.add_argument("--scene", type=str, required=True, help="ID сцены")
    parser.add_argument("--output", type=str, default="output/scene.png", help="Путь для сохранения")
    args = parser.parse_args()

    asyncio.run(generate_scene(args.chapter, args.scene, Path(args.output)))


if __name__ == "__main__":
    main()