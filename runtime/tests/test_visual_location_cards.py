"""Визуальный слой: одна карточка на каноническое место, палитра — из проекта.

Решение владельца 2026-10-21 (вариант A): карточка «Атлантида» переключена
под канонический ключ «Океания», отдельная коралловая карточка «Океания»
удалена. Источник визуальной формы — палитра эпохи «Океания (упадок)»
(`core/KNOWLEDGE/EPOCH_PALETTES.json`) и цвет региона `oceania` из карты
(`core/KNOWLEDGE/MAP_DATA.json`); обоснование — в
`docs/VISUAL_CARDS_ATLANTIDA_OCEANIA_2026-10-21.md`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_CORE = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

LOCATION_VISUALS_PATH = _CORE / "visual" / "VISUAL_KNOWLEDGE" / "LOCATION_VISUALS.json"
EPOCH_PALETTES_PATH = _CORE.parent / "KNOWLEDGE" / "EPOCH_PALETTES.json"
MAP_DATA_PATH = _CORE.parent / "KNOWLEDGE" / "MAP_DATA.json"


def _visuals() -> dict:
    return json.loads(LOCATION_VISUALS_PATH.read_text(encoding="utf-8"))


def test_single_card_for_the_southern_civilization():
    """У одного места — одна визуальная карточка под каноническим ключом."""
    visuals = _visuals()

    assert "Океания" in visuals
    assert "Атлантида" not in visuals


def test_card_palette_matches_the_project_epoch_palette():
    """Визуальная карточка продолжает опираться на палитру эпохи из проекта."""
    visuals = _visuals()
    palettes = json.loads(EPOCH_PALETTES_PATH.read_text(encoding="utf-8"))
    entries = palettes["epochs"] if isinstance(palettes, dict) and "epochs" in palettes else palettes
    if isinstance(entries, dict):
        entries = list(entries.values())
    epoch = next(entry for entry in entries if str(entry.get("name", "")).startswith("Океания"))

    epoch_colors = set(epoch["palette"]["primary"])
    card_colors = set(visuals["Океания"]["palette"])

    assert epoch_colors & card_colors, "визуальная карточка разошлась с палитрой эпохи"


def test_card_color_follows_the_map_region():
    """Первый цвет карточки совпадает с цветом региона на карте."""
    visuals = _visuals()
    map_data = json.loads(MAP_DATA_PATH.read_text(encoding="utf-8"))
    region = next(item for item in map_data["regions"] if item["id"] == "oceania")

    assert region["color"] in visuals["Океания"]["palette"]


def test_scene_locations_resolve_to_existing_visual_cards():
    """Идентификатор локации сцены всегда есть среди визуальных карточек."""
    from knowledge.screenplay_scene_catalog import list_scenes

    visuals = _visuals()
    for scene in list_scenes():
        location_id = scene.get("location_id")
        if location_id:
            assert location_id in visuals, f"{scene['scene_id']}: нет визуальной карточки {location_id}"
