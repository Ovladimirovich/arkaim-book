# -*- coding: utf-8 -*-
"""Guard: реестр классификации знаний полон и не содержит мёртвых записей.

Раньше существовал второй, дублирующий реестр — в
``scripts/enrich_knowledge_provenance.py``. Он не только расходился с
каноническим реестром, но и ПЕРЕЗАПИСЫВАЛ файлы знаний: top-level массивы
превращались в ``{"_provenance_metadata": ..., "items": [...], "item_count": N}``
(ошибка: ``"_provenance_metadata" in data`` на списке проверяет членство,
а не наличие ключа). После такого прогона потребители переставали видеть
данные: терялись 15 одобренных книжных связей, 15 связей claim→событие и
RAG-индекс на 824 документа.

Тесты ниже фиксируют:
  1. каждый файл знаний классифицирован, лишних записей в реестре нет;
  2. имена в реестре уникальны, категории валидны;
  3. разрушительный скрипт отсутствует, а проверочный — только читает;
  4. top-level массивы в core/KNOWLEDGE остаются массивами.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CORE_ROOT = REPO_ROOT / "core" / "CORE"
if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))

from narrative_engine.provenance.knowledge_classification import (  # noqa: E402
    KNOWLEDGE_CLASSIFICATION,
    KnowledgeCategory,
    get_classification,
)

KNOWLEDGE_DIR = REPO_ROOT / "core" / "KNOWLEDGE"
VISUAL_DIR = REPO_ROOT / "core" / "CORE" / "visual" / "VISUAL_KNOWLEDGE"
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _registry_names() -> list[str]:
    return [fc.filename for fc in KNOWLEDGE_CLASSIFICATION]


def _files_on_disk() -> dict[str, Path]:
    files: dict[str, Path] = {}
    for path in sorted(KNOWLEDGE_DIR.glob("*.json")):
        files[path.name] = path
    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        files[path.name] = path
    for path in sorted(VISUAL_DIR.glob("*.json")):
        files[path.name] = path
    return files


# ── 1. Полнота реестра ──────────────────────────────────────────────────


def test_every_knowledge_file_is_classified() -> None:
    """Каждый файл слоя знаний (включая визуальный) классифицирован."""
    registry = set(_registry_names())
    unclassified = sorted(name for name in _files_on_disk() if name not in registry)
    assert unclassified == [], f"не классифицированы: {unclassified}"


def test_no_dead_registry_entries() -> None:
    """В реестре нет записей о файлах, которых больше нет на диске."""
    disk = set(_files_on_disk())
    missing = sorted(name for name in _registry_names() if name not in disk)
    assert missing == [], f"в реестре есть несуществующие файлы: {missing}"


def test_registry_covers_visual_layer() -> None:
    """Визуальный слой покрыт тем же реестром, что и core/KNOWLEDGE."""
    registry = set(_registry_names())
    visual = {path.name for path in VISUAL_DIR.glob("*.json")}
    assert visual, "визуальный слой не найден — тест бессмыслен"
    assert visual <= registry, f"не классифицированы: {sorted(visual - registry)}"


# ── 2. Целостность реестра ─────────────────────────────────────────────


def test_registry_filenames_are_unique() -> None:
    names = _registry_names()
    duplicates = sorted({name for name in names if names.count(name) > 1})
    assert duplicates == [], f"дубли имён в реестре: {duplicates}"


def test_registry_categories_are_valid() -> None:
    valid = {category.value for category in KnowledgeCategory}
    invalid = sorted({fc.category.value for fc in KNOWLEDGE_CLASSIFICATION} - valid)
    assert invalid == [], f"неизвестные категории: {invalid}"


def test_registry_category_equals_disk_metadata() -> None:
    """Категория в реестре равна _provenance_metadata на диске.

    Решение владельца G13 (2026-10-22): источник истины — данные на диске;
    реестр приведён к ним. Расхождение означает, что либо диск, либо реестр
    изменены в обход друг друга.
    """
    mismatches = []
    for name, path in _files_on_disk().items():
        if path.suffix != ".json":
            continue
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            continue
        meta = data.get("_provenance_metadata")
        if not isinstance(meta, dict) or not meta.get("category"):
            continue
        fc = get_classification(name)
        if fc is None:
            continue
        if fc.category.value != meta["category"]:
            mismatches.append(f"{name}: реестр={fc.category.value} диск={meta['category']}")
    assert mismatches == [], "реестр разошёлся с диском: " + "; ".join(mismatches)


def test_is_canon_follows_category() -> None:
    """is_canon выводится из категории: DERIVED-файл не может быть каноном."""
    wrong = []
    for fc in KNOWLEDGE_CLASSIFICATION:
        should = fc.category == KnowledgeCategory.AUTHOR_CANON
        if fc.is_canon != should:
            wrong.append(f"{fc.filename}: category={fc.category.value} is_canon={fc.is_canon}")
    assert wrong == [], "is_canon не соответствует категории: " + "; ".join(wrong)


def test_visual_layer_is_artistic_model() -> None:
    """Визуальный слой — художественная модель, требует проверки автором."""
    from narrative_engine.provenance.knowledge_classification import get_classification

    for path in sorted(VISUAL_DIR.glob("*.json")):
        fc = get_classification(path.name)
        assert fc is not None, path.name
        assert fc.category == KnowledgeCategory.ARTISTIC_MODEL, path.name
        assert fc.is_canon is False, path.name
        assert fc.requires_author_review is True, path.name
        assert fc.source_path, path.name


# ── 3. Разрушительный скрипт удалён, проверочный — только читает ──────


def test_destructive_enrich_script_is_gone() -> None:
    """Скрипт, перезаписывавший файлы знаний, удалён из репозитория."""
    assert not (SCRIPTS_DIR / "enrich_knowledge_provenance.py").exists()


def test_validator_script_does_not_write() -> None:
    """Проверочный скрипт не содержит вызовов записи."""
    script = SCRIPTS_DIR / "validate_knowledge_provenance.py"
    assert script.exists(), "нет проверочного скрипта"
    text = script.read_text(encoding="utf-8")
    for forbidden in ("write_text", "os.replace", "shutil.copy", "json.dump("):
        assert forbidden not in text, f"проверочный скрипт не должен вызывать {forbidden}"


# ── 4. Форма файлов знаний не разрушена ────────────────────────────────


@pytest.mark.parametrize(
    "name",
    [
        "screenplay_links.json",
        "claim_temporal_links.json",
        "enriched_catalog.json",
        "enriched_chunks.json",
    ],
)
def test_top_level_arrays_stay_arrays(name: str) -> None:
    """Top-level массив остаётся массивом (обёртка {items, item_count} недопустима)."""
    path = KNOWLEDGE_DIR / name
    assert path.exists(), f"{name} отсутствует"
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    assert isinstance(data, list), f"{name} должен оставаться массивом, а не {type(data).__name__}"
    assert "items" not in data, f"{name} не должен быть обёрнут в {{items, item_count}}"
