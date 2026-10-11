"""
Скрипт: Cron-рефреш Visual Genome.
Сравнивает хэш текущего генома с сохранённым,
при изменениях запускает авто-заполнение визуалов.
Отправляет дайджест автору.

Рекомендуемое расписание: раз в неделю (Task Scheduler).
"""
import hashlib
import json
import sys
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent / "ARKAIM_DIGITAL_CONSCIOUSNESS" / "CORE"
sys.path.insert(0, str(CORE_DIR))

from core.config import config
from visualization.archetype_visuals import fill_missing_archetype_visuals
from visualization.conflict_palettes import generate_all_conflict_scenes
from visualization.meaning_to_visual import generate_visuals_from_meaning

GENOME_DIR = config.GENOME_DIR
GENOME_PATH = GENOME_DIR / f"GENOME_v{config.GENOME_VERSION}.json"
HASH_PATH = GENOME_DIR / "CURRENT" / ".visual_hash"
CURRENT_DIR = GENOME_DIR / "CURRENT"


def log(msg):
    print(f"[Cron->Visuals] {msg}")


def compute_hash() -> str:
    """SHA256 генома (первые 16 символов)."""
    if not GENOME_PATH.exists():
        return ""
    return hashlib.sha256(GENOME_PATH.read_bytes()).hexdigest()[:16]


def load_previous_hash() -> str:
    if HASH_PATH.exists():
        return HASH_PATH.read_text(encoding="utf-8").strip()
    return ""


def save_current_hash(h: str):
    CURRENT_DIR.mkdir(parents=True, exist_ok=True)
    HASH_PATH.write_text(h, encoding="utf-8")


def load_genome() -> dict:
    if GENOME_PATH.exists():
        return json.loads(GENOME_PATH.read_text(encoding="utf-8"))
    return {}


def save_genome(genome: dict):
    GENOME_PATH.write_text(
        json.dumps(genome, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_output(data: list | dict, name: str):
    CURRENT_DIR.mkdir(parents=True, exist_ok=True)
    path = CURRENT_DIR / name
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    log(f"  Saved: GENOME/CURRENT/{name}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Cron-рефреш Visual Genome")
    parser.add_argument("--dry-run", action="store_true", help="Не сохранять изменения")
    parser.add_argument("--notify", action="store_true", help="Отправить дайджест в Telegram")
    args = parser.parse_args()

    log("=" * 50)
    log("Cron: Рефреш Visual Genome")
    log("=" * 50)

    current_hash = compute_hash()
    prev_hash = load_previous_hash()

    log(f"Текущий хэш:  {current_hash}")
    log(f"Предыдущий:   {prev_hash}")

    genome = load_genome()
    if not genome:
        log("Геном не загружен.")
        return

    changes = []
    errors = []

    # 1. Archetype visuals
    log("\n1. Archetype visuals...")
    try:
        filled = fill_missing_archetype_visuals(genome)
        if filled:
            changes.append(f"character_visuals из архетипов: {filled}")
    except Exception as e:
        errors.append(f"archetype: {e}")

    # 2. Conflict palettes
    log("2. Conflict palettes...")
    try:
        conflict_scenes = generate_all_conflict_scenes(genome)
        if conflict_scenes:
            modules = genome.setdefault("modules", {})
            existing = modules.setdefault("scenes", [])
            existing_ids = {s.get("scene_id") for s in existing}
            new_scenes = [s for s in conflict_scenes if s.get("scene_id") not in existing_ids]
            if new_scenes:
                existing.extend(new_scenes)
                changes.append(f"конфликтных сцен: {len(new_scenes)}")
                save_output(new_scenes, "conflict_scenes_auto.json")
    except Exception as e:
        errors.append(f"conflict_palettes: {e}")

    # 3. Meaning -> visuals
    log("3. Meaning -> visuals...")
    try:
        meaning_scenes, style_presets = generate_visuals_from_meaning(genome)
        if meaning_scenes:
            modules = genome.setdefault("modules", {})
            existing_scenes = modules.setdefault("scenes", [])
            existing_ids = {s.get("scene_id") for s in existing_scenes}
            new_scenes = [s for s in meaning_scenes if s.get("scene_id") not in existing_ids]
            if new_scenes:
                existing_scenes.extend(new_scenes)
                changes.append(f"сцен из meaning: {len(new_scenes)}")
        if style_presets:
            modules = genome.setdefault("modules", {})
            existing_presets = modules.setdefault("style_presets", {})
            for preset in style_presets:
                pid = preset.get("preset_id")
                if pid and pid not in existing_presets:
                    existing_presets[pid] = preset
                    changes.append(f"стиль: {pid}")
    except Exception as e:
        errors.append(f"meaning_to_visual: {e}")

    # 4. Проверить отсутствующие visual для персонажей без archetype
    log("4. Missing visuals check...")
    try:
        modules = genome.get("modules", {})
        chars = modules.get("characters", [])
        char_visuals = modules.get("character_visuals", [])
        visual_ids = {v.get("character_id", "").lower() for v in char_visuals}
        missing = [c.get("name", c.get("id", "")) for c in chars
                   if c.get("id", c.get("name", "")).lower() not in visual_ids]
        if missing:
            log(f"  Нет visual для: {', '.join(missing[:5])}")
    except Exception as e:
        errors.append(f"missing_check: {e}")

    # Сохранить
    if changes and not args.dry_run:
        save_genome(genome)
        save_current_hash(current_hash)
    elif not changes:
        log("\nИзменений нет.")

    # Итог
    log(f"\n{'=' * 50}")
    log(f"ИТОГ:")
    if changes:
        log(f"  Изменения:")
        for c in changes:
            log(f"    [OK] {c}")
    else:
        log(f"  Нет изменений")
    if errors:
        log(f"  Ошибки:")
        for e in errors:
                log(f"    [ERR] {e}")
    log("=" * 50)

    # Уведомление
    if args.notify and changes:
        try:
            from community.telegram import TelegramBotStub
            bot = TelegramBotStub()
            digest = f"📊 Дайджест визуалов\n"
            for c in changes:
                digest += f"[OK] {c}\n"
            if errors:
                digest += f"⚠️ Ошибки: {len(errors)}\n"
            # Отправка через TelegramBotStub.send_notification
            import asyncio
            asyncio.run(bot.send_notification(digest))
            log("  Уведомление отправлено в Telegram")
        except Exception as e:
            log(f"  Не удалось отправить уведомление: {e}")


if __name__ == "__main__":
    main()
