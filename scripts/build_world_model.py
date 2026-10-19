"""Воспроизводимая офлайн-сборка World Model (core/CORE/WORLD_MODEL/*.json).

World Model строится детерминированно из уже существующих файлов
``core/KNOWLEDGE`` через ``world_extraction.create_world_pipeline``.
Скрипт НЕ подключён к рантайму и ничего не делает автоматически.

Режимы:
  --check   только сравнить вычисленное с текущими файлами, ничего не писать
            (по умолчанию);
  --write   записать файлы (с timestamped .bak-бэкапами).

Ограничения (зафиксировано решением владельца):
  * TECHNOLOGIES.json остаётся пустым ([]);
  * рантайм не читает WORLD_MODEL через этот скрипт.

Запуск из корня репозитория:
    python scripts/build_world_model.py --check
    python scripts/build_world_model.py --write
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
WORLD_MODEL_DIR = CORE_DIR / "WORLD_MODEL"

if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from world_extraction.pipeline import create_world_pipeline  # noqa: E402


def _strip_trailing_ws(data) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def _read_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _computed_by_category() -> dict[str, list[dict]]:
    pipeline = create_world_pipeline()
    manifest = pipeline.extract_all()
    computed: dict[str, list[dict]] = {}
    for category, result in manifest.categories.items():
        if result.success and result.items_count > 0:
            computed[category] = [item.to_dict() for item in result.items]
    return computed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Сборка World Model (офлайн).")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--check",
        action="store_true",
        help="только сравнить, ничего не писать (по умолчанию)",
    )
    group.add_argument(
        "--write", action="store_true", help="записать категории (с бэкапом)"
    )
    args = parser.parse_args(argv)

    computed = _computed_by_category()
    computed_files = {cat: f"{cat.upper()}.json" for cat in computed}

    existing_files = (
        {p.name for p in WORLD_MODEL_DIR.glob("*.json")}
        if WORLD_MODEL_DIR.exists()
        else set()
    )
    expected_names = set(computed_files.values())

    total_items = sum(len(v) for v in computed.values())
    print(
        f"[build_world_model] категорий с данными: {len(computed)}, сущностей: {total_items}"
    )

    same, differ, new, missing = [], [], [], []
    for cat, filename in sorted(computed_files.items()):
        current = _read_json(WORLD_MODEL_DIR / filename)
        if current is None:
            new.append(filename)
            print(f"  [new]      {filename}: вычислено {len(computed[cat])}")
        elif _strip_trailing_ws(current) == _strip_trailing_ws(computed[cat]):
            same.append(filename)
            print(f"  [same]     {filename}: {len(computed[cat])}")
        else:
            differ.append(filename)
            cur_n = len(current) if isinstance(current, list) else "?"
            print(
                f"  [differs]  {filename}: файл {cur_n} vs вычислено {len(computed[cat])}"
            )

    orphan = sorted(existing_files - expected_names)
    for filename in orphan:
        missing.append(filename)
        print(f"  [orphan]   {filename}: есть в WORLD_MODEL, нет в вычисленном")

    print(
        f"[build_world_model] итог: same={len(same)} differ={len(differ)} "
        f"new={len(new)} orphan={len(missing)}"
    )

    if not args.write:
        if differ or new or missing:
            print("[build_world_model] CHECK: есть расхождения — требуется --write")
            return 1
        print(
            "[build_world_model] CHECK: WORLD_MODEL совпадает с вычисленным — перезапись не нужна"
        )
        return 0

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    WORLD_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    for filename in sorted(existing_files):
        backup = WORLD_MODEL_DIR / f"{filename}.{stamp}.bak"
        shutil.copy2(WORLD_MODEL_DIR / filename, backup)

    pipeline = create_world_pipeline()
    manifest = pipeline.extract_all()
    saved = pipeline.save_all(manifest)
    print(
        f"[build_world_model] записано категорий: {len(saved)}; бэкап-суффикс: .{stamp}.bak"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
