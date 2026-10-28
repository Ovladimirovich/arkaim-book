#!/usr/bin/env python
"""check_provenance_integrity — CI-гейт автодетекции пустых/самоссылочных
provenance-меток в WORLD_MODEL (закрытие B17).

Этап 4 последовательного плана: защита от рецидива B3/B4. Без этого гейта
любое будущее ручное наполнение WORLD_MODEL/*.json может снова вернуть
пустые «оболочки» (description="") или записи с provenance_category, но без
доказательной цепочки (source) — и регрессия пройдёт незамеченной в CI.

Скрипт только читает (READ-ONLY). Падает (код 1) на любой записи, где:
  1. ``provenance_category`` задан, но ``source`` отсутствует / null / пустой;
  2. ``source`` самоссылочный (равен id или name самой записи);
  3. ``description`` пуст и нет ни ``derived_from``, ни ``mirrors_from``
     (запись не является осознанной производной проекцией).

Запуск:
    python scripts/check_provenance_integrity.py             # отчёт, код 0 при чистоте
    python scripts/check_provenance_integrity.py --strict    # код 1 при нарушениях (для CI)

Подключён в ``.github/workflows/ci.yml``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORLD_MODEL_DIR = PROJECT_ROOT / "core" / "CORE" / "WORLD_MODEL"


def _records() -> list[tuple[str, dict]]:
    """(filename, record) для каждой записи WORLD_MODEL/*.json."""
    out: list[tuple[str, dict]] = []
    for path in sorted(WORLD_MODEL_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, list):
            continue
        for item in data:
            if isinstance(item, dict):
                out.append((path.name, item))
    return out


def _check_record(filename: str, item: dict) -> list[str]:
    """Вернуть список нарушений записи (пусто — запись корректна)."""
    problems: list[str] = []
    eid = str(item.get("id") or item.get("name") or "?")
    category = item.get("provenance_category")
    source = item.get("source")
    description = str(item.get("description") or "")
    derived_from = item.get("derived_from") or item.get("DERIVED_FROM")
    mirrors_from = item.get("mirrors_from") or item.get("MIRRORS_FROM")

    if category:
        if source is None or str(source).strip() == "":
            problems.append(f"provenance_category у {eid!r}: source отсутствует/пуст")
        elif str(source).strip().casefold() in {
            str(eid).casefold(),
            str(item.get("name", "")).casefold(),
        }:
            problems.append(
                f"provenance_category у {eid!r}: source самоссылочный ({source!r})"
            )

    if description.strip() == "" and not derived_from and not mirrors_from:
        problems.append(f"у {eid!r}: description пуст и нет derived_from/mirrors_from")

    return [f"[{filename}] {p}" for p in problems]


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover
        pass

    parser = argparse.ArgumentParser(
        description="CI-гейт целостности provenance WORLD_MODEL (B17)."
    )
    parser.add_argument(
        "--strict", action="store_true", help="код 1 при нарушениях (для CI)"
    )
    args = parser.parse_args()

    records = _records()
    violations: list[str] = []
    for filename, item in records:
        violations.extend(_check_record(filename, item))

    print("Проверка целостности provenance WORLD_MODEL (B17, только-чтение)")
    print(f"  записей проверено: {len(records)}")
    print()

    if not violations:
        print(
            "Нарушений нет: каждая запись с provenance_category имеет source, "
            "пустых оболочек без derived_from/mirrors_from не найдено."
        )
        return 0

    print(f"НАРУШЕНИЙ: {len(violations)}")
    for v in violations:
        print("  " + v)
    print()
    print(
        "Внимание: данная запись регрессирует целостность provenance. "
        "Заполните source (доказательнлую цепочку) и/или description, "
        "или укажите derived_from/mirrors_from, иначе данные не пройдут гейт."
    )
    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
