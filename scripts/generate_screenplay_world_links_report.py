"""Генератор отчёта по связям 119 сцен сценария с World Model и Knowledge Core.

Только чтение: скрипт не меняет ни источники, ни реестры. Отчёт
воспроизводим — одинаковый вход даёт одинаковый файл.

Запуск:
  python scripts/generate_screenplay_world_links_report.py            # записать отчёт
  python scripts/generate_screenplay_world_links_report.py --check    # проверить актуальность
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = PROJECT_ROOT / "core" / "CORE"
if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))

from knowledge.screenplay_scene_catalog import list_scenes  # noqa: E402

DEFAULT_OUTPUT = PROJECT_ROOT / "docs" / "SCREENPLAY_SCENE_WORLD_LINKS_REPORT.md"

_STATUSES = ("CONFIRMED", "DERIVED", "UNRESOLVED", "AMBIGUOUS")


def _short(value: str, limit: int = 46) -> str:
    value = " ".join(str(value).split())
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "…"


def _confirmed_targets(scene: dict) -> str:
    targets = []
    for link in scene.get("world_links") or []:
        if link["status"] != "CONFIRMED":
            continue
        if link["link_type"] in {"event", "epoch", "location"}:
            targets.append(f"{link['link_type']}:{link['target_id']}")
    return ", ".join(targets) if targets else "—"


def _derived_targets(scene: dict) -> str:
    targets = []
    for link in scene.get("world_links") or []:
        if link["status"] != "DERIVED":
            continue
        if link["link_type"] in {"location", "location_mention", "character_relation"}:
            targets.append(f"{link['link_type']}:{_short(link['target_id'], 28)}")
    return ", ".join(targets) if targets else "—"


def _missing_types(scene: dict) -> str:
    missing = sorted(scene.get("world_link_missing") or {})
    return ", ".join(missing) if missing else "—"


def build_report() -> str:
    scenes = list_scenes()

    status_counts: Counter[str] = Counter()
    type_counts: Counter[tuple[str, str]] = Counter()
    scenes_with_confirmed = 0
    scenes_with_derived = 0
    scenes_with_ambiguous = 0
    missing_counter: Counter[str] = Counter()
    ambiguous_rows: list[str] = []
    location_unresolved = 0
    location_resolved = 0
    location_mentions = 0
    scenes_with_confirmed_event = 0
    scenes_with_book_link = 0
    scenes_with_unresolved_event = 0

    for scene in scenes:
        summary = scene["world_link_summary"]
        if summary["confirmed"]:
            scenes_with_confirmed += 1
        if summary["derived"]:
            scenes_with_derived += 1
        if summary["ambiguous"]:
            scenes_with_ambiguous += 1
        for link in scene["world_links"]:
            status_counts[link["status"]] += 1
            type_counts[(link["link_type"], link["status"])] += 1
            if link["status"] == "AMBIGUOUS":
                ambiguous_rows.append(
                    f"| {scene['scene_id']} | {link['link_type']} | {_short(link['basis'], 90)} |"
                )
        for link_type in scene.get("world_link_missing") or {}:
            missing_counter[link_type] += 1
        for link in scene["world_links"]:
            if link["link_type"] == "location":
                if link["status"] == "UNRESOLVED":
                    location_unresolved += 1
                else:
                    location_resolved += 1
            if link["link_type"] == "location_mention":
                location_mentions += 1
            if link["link_type"] == "event" and link["status"] == "CONFIRMED":
                scenes_with_confirmed_event += 1
            if link["link_type"] == "event" and link["status"] == "UNRESOLVED":
                scenes_with_unresolved_event += 1
        if scene.get("book_links"):
            scenes_with_book_link += 1

    lines: list[str] = []
    lines.append("# Связи 119 сцен сценария с World Model и Knowledge Core")
    lines.append("")
    lines.append(
        "Отчёт формируется скриптом `scripts/generate_screenplay_world_links_report.py` "
        "из read-only каталога сцен `core/CORE/knowledge/screenplay_scene_catalog.py`."
    )
    lines.append("Источники не изменяются; отчёт воспроизводим.")
    lines.append("")
    lines.append("## 1. Что означают статусы связей")
    lines.append("")
    lines.append("| Статус | Значение |")
    lines.append("| --- | --- |")
    lines.append(
        "| `CONFIRMED` | Цель и её идентичность подтверждены владельцем: одобренная связь "
        "сценарий↔книга + одобренная claim-связь с валидной цепочкой до канонического события, "
        "либо точное совпадение имени персонажа с записью `characters_living` в World Model. |"
    )
    lines.append(
        "| `DERIVED` | Связь вычислена по точному задокументированному правилу над существующими "
        "данными: идентификатор локации из `LOCATION_VISUALS` дословно совпал с `name_ru` локации "
        "World Model; дословное упоминание одобренной метки crosswalk; оба участника подтверждённой "
        "связи персонажей присутствуют в сцене; обогащение одобренного книжного чанка. |"
    )
    lines.append(
        "| `UNRESOLVED` | Точного основания нет. Причина фиксируется явно, значение не подставляется. |"
    )
    lines.append(
        "| `AMBIGUOUS` | На одну цель претендуют несколько сущностей. Выбор не выполняется, "
        "кандидаты перечисляются. |"
    )
    lines.append("")
    lines.append("## 2. Сводка")
    lines.append("")
    lines.append(f"- Всего сцен: **{len(scenes)}**")
    lines.append(f"- Сцен с подтверждёнными связями: **{scenes_with_confirmed}**")
    lines.append(f"- Сцен с производными связями: **{scenes_with_derived}**")
    lines.append(f"- Сцен с неоднозначностями: **{scenes_with_ambiguous}**")
    lines.append("")
    lines.append("| Тип связи | CONFIRMED | DERIVED | UNRESOLVED | AMBIGUOUS |")
    lines.append("| --- | --- | --- | --- | --- |")
    link_types = sorted({link_type for link_type, _ in type_counts})
    for link_type in link_types:
        lines.append(
            f"| `{link_type}` | {type_counts[(link_type, 'CONFIRMED')]} "
            f"| {type_counts[(link_type, 'DERIVED')]} | {type_counts[(link_type, 'UNRESOLVED')]} "
            f"| {type_counts[(link_type, 'AMBIGUOUS')]} |"
        )
    lines.append(
        f"| **Итого связей** | {status_counts['CONFIRMED']} | {status_counts['DERIVED']} "
        f"| {status_counts['UNRESOLVED']} | {status_counts['AMBIGUOUS']} |"
    )
    lines.append("")
    lines.append("## 3. Пробелы (по типам отсутствующих связей)")
    lines.append("")
    lines.append("| Тип | Сцен без связи |")
    lines.append("| --- | --- |")
    for link_type, count in sorted(missing_counter.items()):
        lines.append(f"| `{link_type}` | {count} |")
    lines.append("")
    lines.append("## 4. Неоднозначности")
    lines.append("")
    if ambiguous_rows:
        lines.append("| Сцена | Тип | Причина |")
        lines.append("| --- | --- | --- |")
        lines.extend(ambiguous_rows)
    else:
        lines.append(
            "Неоднозначных связей не зафиксировано: ни одна локация/персонаж сцены "
            "не претендует сразу на несколько сущностей World Model."
        )
    lines.append("")
    lines.append("## 5. Карта по всем 119 сценам")
    lines.append("")
    lines.append(
        "| Сцена | Заголовок | Confirmed | Derived | Unresolved | Ambiguous | Подтверждённые цели | Производные связи | Нет данных |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for scene in scenes:
        summary = scene["world_link_summary"]
        lines.append(
            f"| {scene['scene_id']} | {_short(scene['title'], 40)} | {summary['confirmed']} "
            f"| {summary['derived']} | {summary['unresolved']} | {summary['ambiguous']} "
            f"| {_confirmed_targets(scene)} | {_derived_targets(scene)} | {_missing_types(scene)} |"
        )
    lines.append("")
    lines.append("## 6. Наблюдения по качеству данных (требуют решения владельца)")
    lines.append("")
    lines.append(
        f"- **Локации сцен почти не сопоставимы с миром.** {location_unresolved} из {len(scenes)} "
        "сцен не имеют точного соответствия: заголовки сценария — это общие места действия "
        "(`ПЕЩЕРА`, `ЗАЛ`, `КОМНАТА`), а не имена локаций мира. Сопоставление по падежным формам "
        "небезопасно: в тексте преобладает `Гипербореи` (люди) при `Гиперборея` (место) — "
        "основа отличается одной буквой."
    )
    lines.append(
        f"- **Точное упоминание одобренной метки crosswalk** даёт {location_mentions} связь: "
        "упоминание помечается отдельно от места действия сцены."
    )
    lines.append(
        f"- **`Океания` одобрена владельцем**: каноническая локация `океания` и соответствие "
        f"`region_oceania` есть в World Model и crosswalk. Сцен со связью по локации: "
        f"{location_resolved} (связь по заголовку/идентификатору локации, статус DERIVED), "
        f"{location_mentions} — только упоминание. «Атлантида» и «Океания» — два названия "
        "одной южной цивилизации (решение владельца 2026-10-20): каноническая локация — "
        "`океания`, «Атлантида» утверждена как её метка "
        "(`core/KNOWLEDGE/location_aliases.json`)."
    )
    lines.append(
        "- **Формы упоминаний мест утверждены владельцем ограниченным списком** "
        "(`core/KNOWLEDGE/place_mention_forms.json`): только те формы, которые в сценарии означают "
        "именно место. Формы людей (`Гипербореи`, `Наставники`, `Учитель`) и эпох "
        "(`Кали Юга`, `Сати Юга`) исключены явно и местом не считаются. Упоминание остаётся "
        "отдельным типом связи и не означает место действия сцены."
    )
    lines.append(
        "- **Дубли идентичности локаций в модели мира устранены (решение владельца 2026-10-20)**: "
        "англоязычные записи `arkaim` и `hyperborea` удалены — они были метками, а не "
        "идентичностями (crosswalk v2); записи `наставники` и `учителя_человечества` (люди и "
        "группы) и `кали_юга`, `сати_юга` (эпохи) убраны из списка мест — все они остаются "
        "персонажами или эпохами. Дубли в именах персонажей (`Славный` / `Мирослав`) намеренно "
        "не склеиваются: связи строятся только по точному совпадению имени."
    )
    lines.append(
        "- **Канонический персонаж `Ученики`** в мире записан как `Ученики (плеяда)`. Точного "
        "совпадения нет, поэтому персонаж в сценах с упоминанием «ученики» не связывается с миром "
        "и остаётся в статусе `UNRESOLVED`."
    )
    lines.append(
        "- **События и эпохи** доступны только через одобренную цепочку "
        "`screenplay_links.json` → `claim_temporal_links.json` → `WORLD_MODEL.json`: "
        f"{scenes_with_confirmed_event} сцен имеют подтверждённое событие и эпоху; "
        f"{scenes_with_unresolved_event} сцен с одобренной книжной связью "
        f"(всего сцен с книжной связью — {scenes_with_book_link}) не имеют подтверждённой "
        "claim-связи и остаются `UNRESOLVED`."
    )
    lines.append("")
    lines.append("## 7. Источники")
    lines.append("")
    lines.append(
        "- `core/KNOWLEDGE/screenplay_links.json` — одобренные связи сценарий↔книга (15)."
    )
    lines.append(
        "- `core/KNOWLEDGE/claim_temporal_links.json` — одобренные связи claim→событие/эпоха (9)."
    )
    lines.append(
        "- `core/KNOWLEDGE/enriched_chunks.json` — тексты книжных чанков и их обогащение."
    )
    lines.append(
        "- `core/CORE/narrative_engine/data/WORLD_MODEL.json` — эпохи, локации, персонажи, события."
    )
    lines.append(
        "- `core/CORE/WORLD_CROSSWALK/WORLD_ENGINE_WORLD_MODEL.json` — одобренные соответствия (2)."
    )
    lines.append(
        "- `core/CORE/visual/VISUAL_KNOWLEDGE/LOCATION_VISUALS.json` — ключи визуальных локаций."
    )
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_OUTPUT, help="путь к файлу отчёта"
    )
    parser.add_argument(
        "--check", action="store_true", help="проверить актуальность, не записывая файл"
    )
    args = parser.parse_args()

    report = build_report()
    if args.check:
        current = args.out.read_text(encoding="utf-8") if args.out.exists() else ""
        if current != report:
            print(f"Отчёт устарел: {args.out}")
            return 1
        print(f"Отчёт актуален: {args.out}")
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(f"Отчёт записан: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
