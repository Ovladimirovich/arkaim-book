"""Инструмент для наполнения Visual Genome в GENOME_v1.0.0.json."""
import json
import sys
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent / "ARKAIM_DIGITAL_CONSCIOUSNESS" / "CORE"
sys.path.insert(0, str(CORE_DIR))


def _get_config():
    import config as _cfg
    return _cfg.config


def load_genome() -> dict:
    config = _get_config()
    path = config.GENOME_DIR / f"GENOME_v{config.GENOME_VERSION}.json"
    if not path.exists():
        print(f"Геном не найден: {path}")
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def save_genome(genome: dict):
    config = _get_config()
    path = config.GENOME_DIR / f"GENOME_v{config.GENOME_VERSION}.json"
    path.write_text(json.dumps(genome, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Сохранено: {path}")


def add_scenes(genome: dict, scenes: list[dict]):
    modules = genome.setdefault("modules", {})
    existing = modules.setdefault("scenes", [])
    existing.extend(scenes)
    print(f"Добавлено сцен: {len(scenes)}")


def add_character_visuals(genome: dict, visuals: list[dict]):
    modules = genome.setdefault("modules", {})
    existing = modules.setdefault("character_visuals", [])
    existing.extend(visuals)
    print(f"Добавлено визуалов персонажей: {len(visuals)}")
    # Хук: если у персонажа есть archetype, но нет visual — создать из шаблона
    try:
        from visualization.archetype_visuals import fill_missing_archetype_visuals
        filled = fill_missing_archetype_visuals(genome)
        if filled:
            print(f"  Авто-заполнено из архетипов: {filled}")
    except ImportError:
        pass  # модуль может отсутствовать на ранних этапах


def add_location_visuals(genome: dict, visuals: list[dict]):
    modules = genome.setdefault("modules", {})
    existing = modules.setdefault("location_visuals", [])
    existing.extend(visuals)
    print(f"Добавлено визуалов локаций: {len(visuals)}")


def add_style_presets(genome: dict, presets: list[dict]):
    modules = genome.setdefault("modules", {})
    existing = modules.setdefault("style_presets", {})
    for preset in presets:
        preset_id = preset.get("preset_id")
        if preset_id:
            existing[preset_id] = preset
    print(f"Добавлено стилей: {len(presets)}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Наполнение Visual Genome")
    parser.add_argument("--scenes", type=str, help="JSON файл со сценами")
    parser.add_argument("--character-visuals", type=str, help="JSON файл с визуалами персонажей")
    parser.add_argument("--location-visuals", type=str, help="JSON файл с визуалами локаций")
    parser.add_argument("--style-presets", type=str, help="JSON файл со стилевыми пресетами")
    args = parser.parse_args()

    genome = load_genome()

    if args.scenes:
        scenes = json.loads(Path(args.scenes).read_text(encoding="utf-8"))
        add_scenes(genome, scenes)

    if args.character_visuals:
        visuals = json.loads(Path(args.character_visuals).read_text(encoding="utf-8"))
        add_character_visuals(genome, visuals)

    if args.location_visuals:
        visuals = json.loads(Path(args.location_visuals).read_text(encoding="utf-8"))
        add_location_visuals(genome, visuals)

    if args.style_presets:
        presets = json.loads(Path(args.style_presets).read_text(encoding="utf-8"))
        add_style_presets(genome, presets)

    save_genome(genome)


if __name__ == "__main__":
    main()