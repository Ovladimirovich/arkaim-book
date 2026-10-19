"""Воспроизводимая офлайн-сборка модуля modules.narrative_arcs в GENOME.

Сюжетные дуги НЕ пишутся от руки и не генерируются LLM: они вычисляются
детерминированно из уже существующих модулей генома
(characters / conflicts / themes / timeline) через
``genome.extractor.extract_narrative_arcs``.

Каждая дуга получает:
  * ``provenance`` — из какого модуля генома и какой сущности построена;
  * ``incomplete`` / ``incomplete_reason`` — пометка неполной связи
    (нет entity_id, границ глав или известного архетипа).

Режимы:
  --check   только сравнить с текущим геномом, ничего не писать (по умолчанию);
  --write   сделать резервную копию генома и записать модуль narrative_arcs.

Запуск из корня репозитория:
    python scripts/build_narrative_arcs.py --check
    python scripts/build_narrative_arcs.py --write
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_DIR = REPO_ROOT / "core" / "CORE"
GENOME_PATH = REPO_ROOT / "core" / "GENOME" / "GENOME_v1.0.0.json"

if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from genome.extractor import extract_narrative_arcs  # noqa: E402


def _load_genome(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_arcs(genome: dict) -> list[dict]:
    modules = genome.get("modules", {})
    chars = modules.get("characters", [])
    confs = modules.get("conflicts", [])
    themes = modules.get("themes", [])
    timeline = modules.get("timeline", [])
    return extract_narrative_arcs(chars, confs, themes, timeline)


def _arc_stats(arcs: list[dict]) -> dict:
    by_type: dict[str, int] = {}
    incomplete = 0
    for a in arcs:
        by_type[a.get("type", "?")] = by_type.get(a.get("type", "?"), 0) + 1
        if a.get("incomplete"):
            incomplete += 1
    return {"total": len(arcs), "by_type": by_type, "incomplete": incomplete}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Сборка modules.narrative_arcs в GENOME (офлайн)."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--check",
        action="store_true",
        help="только сравнить, ничего не писать (по умолчанию)",
    )
    group.add_argument(
        "--write",
        action="store_true",
        help="записать модуль narrative_arcs (с бэкапом)",
    )
    args = parser.parse_args(argv)

    genome = _load_genome(GENOME_PATH)
    arcs = _build_arcs(genome)
    stats = _arc_stats(arcs)
    current = genome.get("modules", {}).get("narrative_arcs")

    print(f"[build_narrative_arcs] вычислено дуг: {stats['total']} {stats['by_type']}")
    print(f"[build_narrative_arcs] неполных связей: {stats['incomplete']}")
    print(
        f"[build_narrative_arcs] в геноме сейчас: {'нет модуля' if current is None else len(current)}"
    )

    if not args.write:
        if current is None:
            print(
                "[build_narrative_arcs] CHECK: модуль narrative_arcs отсутствует — требуется --write"
            )
            return 1
        if current == arcs:
            print(
                "[build_narrative_arcs] CHECK: модуль совпадает — перезапись не нужна"
            )
            return 0
        print(
            "[build_narrative_arcs] CHECK: модуль отличается от вычисленного — требуется --write"
        )
        return 1

    backup = GENOME_PATH.with_name(
        f"{GENOME_PATH.name}.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.bak"
    )
    shutil.copy2(GENOME_PATH, backup)
    print(f"[build_narrative_arcs] бэкап: {backup.name}")

    genome.setdefault("modules", {})["narrative_arcs"] = arcs
    GENOME_PATH.write_text(
        json.dumps(genome, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[build_narrative_arcs] записано {stats['total']} дуг в {GENOME_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
