# -*- coding: utf-8 -*-
"""Guard: идентичность сущностей в narrative World Model.

Решение владельца G14 = 2 (2026-10-22): дубли идентификаторов помечены,
ничего не удалено. Соглашение проекта (crosswalk rejection_reason): EN и RU
названия — это labels/aliases, канонической является стабильная
идентичность. Поэтому:

  - запись, у которой есть каноническая пара в другой категории, помечается
    ``also_in_categories``;
  - запись с неканоническим (EN) идентификатором помечается ``pseudonym``
    и ``canonical_id`` (null — если канонической записи в модели нет).

Тесты ниже следят, чтобы пометки не потерялись и не указывали в пустоту.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WORLD_MODEL = REPO_ROOT / "core" / "CORE" / "narrative_engine" / "data" / "WORLD_MODEL.json"


@pytest.fixture(scope="module")
def world_model() -> dict:
    return json.loads(WORLD_MODEL.read_text(encoding="utf-8"))


def _all_ids(wm: dict) -> set[str]:
    ids: set[str] = set()
    for category in ("locations", "civilizations"):
        for record in wm.get(category) or []:
            if isinstance(record, dict) and record.get("id"):
                ids.add(str(record["id"]))
    return ids


def test_pseudonym_records_declare_canonical_id(world_model: dict) -> None:
    """Запись-псевдоним всегда объявляет canonical_id (пустым или id)."""
    known = _all_ids(world_model)
    for category in ("locations", "civilizations"):
        for record in world_model.get(category) or []:
            if not isinstance(record, dict):
                continue
            if record.get("pseudonym") is not True:
                continue
            assert "canonical_id" in record, f"{record.get('id')}: псевдоним без canonical_id"
            canonical = record["canonical_id"]
            if canonical is None:
                continue  # канонической записи в модели нет — это честно помечено
            assert canonical in known, f"{record.get('id')}: canonical_id {canonical!r} не существует в модели"


def test_pseudonym_is_not_marked_without_flag(world_model: dict) -> None:
    """canonical_id без pseudonym не встречается (иначе двусмысленно)."""
    for category in ("locations", "civilizations"):
        for record in world_model.get(category) or []:
            if not isinstance(record, dict):
                continue
            if "canonical_id" in record:
                assert record.get("pseudonym") is True, f"{record.get('id')}: canonical_id без pseudonym"


def test_also_in_categories_is_symmetric(world_model: dict) -> None:
    """Категория, заявленная через also_in_categories, отвечает взаимностью."""
    locations = {r["id"]: r for r in world_model.get("locations") or [] if isinstance(r, dict)}
    civilizations = {r["id"]: r for r in world_model.get("civilizations") or [] if isinstance(r, dict)}
    tables = {"location": locations, "civilization": civilizations}

    for home_category, table in tables.items():
        for record in table.values():
            for other_category in record.get("also_in_categories") or []:
                assert other_category in tables, f"{record['id']}: неизвестная категория {other_category}"
                other = tables[other_category]
                assert record["id"] in other, f"{record['id']}: категория {other_category} не содержит парной записи"
                assert home_category in (other[record["id"]].get("also_in_categories") or []), f"{record['id']}: пометка категории {other_category} не взаимна"


def test_hyperborea_duplicate_is_marked_not_duplicated(world_model: dict) -> None:
    """Гиперборея присутствует в двух категориях и помечена как одна сущность."""
    locations = {r["id"]: r for r in world_model.get("locations") or [] if isinstance(r, dict)}
    civilizations = {r["id"]: r for r in world_model.get("civilizations") or [] if isinstance(r, dict)}

    assert "гиперборея" in locations and "гиперборея" in civilizations
    assert "civilization" in (locations["гиперборея"].get("also_in_categories") or [])
    assert "location" in (civilizations["гиперборея"].get("also_in_categories") or [])


def test_english_civilization_ids_are_pseudonyms(world_model: dict) -> None:
    """EN-идентификаторы цивилизаций помечены псевдонимами."""
    civilizations = {r["id"]: r for r in world_model.get("civilizations") or [] if isinstance(r, dict)}
    assert civilizations["hyperborean"]["pseudonym"] is True
    assert civilizations["hyperborean"]["canonical_id"] == "гиперборея"
    assert civilizations["vedic"]["pseudonym"] is True
    # у «Ведической» канонической записи в модели нет — это зафиксировано явно
    assert civilizations["vedic"]["canonical_id"] is None
