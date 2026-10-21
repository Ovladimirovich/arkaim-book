#!/usr/bin/env python
"""validate_knowledge_provenance — ПРОВЕРКА (без записи) слоя provenance.

Заменяет прежний ``scripts/enrich_knowledge_provenance.py``, который был
дублем реестра классификации и при запуске ПЕРЕЗАПИСЫВАЛ файлы знаний:
top-level массивы (screenplay_links.json, claim_temporal_links.json,
enriched_catalog.json, enriched_chunks.json) превращались в объекты
``{"_provenance_metadata": ..., "items": [...], "item_count": N}``, и
потребители переставали видеть данные. Причина — проверка
``"_provenance_metadata" in data`` на списке (это проверка членства, а не
наличия ключа).

Этот скрипт НИЧЕГО НЕ ПИШЕТ. Он только сверяет:
  1. реестр ``core/CORE/narrative_engine/provenance/knowledge_classification.py``
     с фактическими файлами в ``core/KNOWLEDGE/`` и
     ``core/CORE/visual/VISUAL_KNOWLEDGE/``;
  2. категорию в реестре с категорией ``_provenance_metadata`` на диске.

Запуск:
    python scripts/validate_knowledge_provenance.py            # отчёт
    python scripts/validate_knowledge_provenance.py --strict   # ненулевой код возврата при расхождениях

Код возврата: 0 — структурных расхождений нет; 1 — есть (при --strict).
Категорийные расхождения реестр->диск всегда только РЕПОРТУЮТСЯ: что
является каноном — решение владельца, а не технический вывод скрипта.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = PROJECT_ROOT / "core" / "CORE"
if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))

from narrative_engine.provenance.knowledge_classification import (  # noqa: E402
    KNOWLEDGE_CLASSIFICATION,
)

KNOWLEDGE_DIR = PROJECT_ROOT / "core" / "KNOWLEDGE"
VISUAL_DIR = PROJECT_ROOT / "core" / "CORE" / "visual" / "VISUAL_KNOWLEDGE"


def _registry_by_name() -> dict:
    return {fc.filename: fc for fc in KNOWLEDGE_CLASSIFICATION}


def _disk_files() -> dict[str, Path]:
    files: dict[str, Path] = {}
    for path in sorted(KNOWLEDGE_DIR.glob("*.json")):
        files[path.name] = path
    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        files[path.name] = path
    for path in sorted(VISUAL_DIR.glob("*.json")):
        files[path.name] = path
    return files


def _disk_category(path: Path) -> str | None:
    """Категория из _provenance_metadata на диске (None — её нет)."""
    if path.suffix != ".json":
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    meta = data.get("_provenance_metadata")
    if not isinstance(meta, dict):
        return None
    category = meta.get("category")
    return str(category) if category else None


def main() -> int:
    # Консоль Windows по умолчанию cp1251 и не умеет часть символов —
    # печать падала бы UnicodeEncodeError. Принудительно UTF-8 с заменой.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover - нестандартный stdout
        pass

    parser = argparse.ArgumentParser(
        description="Проверка слоя provenance (без записи)."
    )
    parser.add_argument(
        "--strict", action="store_true", help="ненулевой код возврата при расхождениях"
    )
    args = parser.parse_args()

    registry = _registry_by_name()
    disk = _disk_files()

    duplicates = sorted(
        {
            fc.filename
            for fc in KNOWLEDGE_CLASSIFICATION
            if sum(1 for f in KNOWLEDGE_CLASSIFICATION if f.filename == fc.filename) > 1
        }
    )
    unclassified = sorted(name for name in disk if name not in registry)
    missing_on_disk = sorted(name for name in registry if name not in disk)

    drift: list[tuple[str, str, str]] = []
    for name, path in disk.items():
        fc = registry.get(name)
        if fc is None:
            continue
        disk_category = _disk_category(path)
        if disk_category is not None and disk_category != fc.category.value:
            drift.append((name, disk_category, fc.category.value))

    print("Проверка слоя provenance (режим только-чтение)")
    print(f"  реестр: {len(registry)} записей")
    print(f"  файлов на диске: {len(disk)}")
    print()

    ok = True
    if duplicates:
        ok = False
        print(f"ДУБЛИ В РЕЕСТРЕ ({len(duplicates)}): {', '.join(duplicates)}")
    if unclassified:
        ok = False
        print(
            f"НЕ КЛАССИФИЦИРОВАНЫ НА ДИСКЕ ({len(unclassified)}): {', '.join(unclassified)}"
        )
    if missing_on_disk:
        ok = False
        print(
            f"В РЕЕСТРЕ, НО НЕТ НА ДИСКЕ ({len(missing_on_disk)}): {', '.join(missing_on_disk)}"
        )
    if not (duplicates or unclassified or missing_on_disk):
        print(
            "Структурных расхождений нет: каждый файл классифицирован, лишних записей нет."
        )

    if drift:
        print()
        print(
            f"РАСХОЖДЕНИЕ КАТЕГОРИЙ реестр->диск ({len(drift)}) — решение по канону принимает владелец:"
        )
        for name, disk_category, registry_category in drift:
            print(f"  {name}: диск={disk_category} реестр={registry_category}")

    if not ok:
        return 1 if args.strict else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
