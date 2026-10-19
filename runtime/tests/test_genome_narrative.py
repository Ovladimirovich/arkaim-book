"""Tests for Narrative Arc Layer — schema + extractor + pulse layer."""

import sys
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
sys.path.insert(0, str(CORE_DIR))

from genome.schema import NarrativeArc, Beat
from genome.extractor import extract_narrative_arcs, CHARACTER_ARC_TYPES


def test_schema_beat():
    b = Beat(chapter=1, state="introduction", intensity=0.3, description="Test")
    assert b.chapter == 1
    assert b.state == "introduction"
    assert b.intensity == 0.3
    assert b.description == "Test"


def test_schema_narrative_arc():
    beats = [
        Beat(chapter=1, state="introduction", intensity=0.3, description="Start"),
        Beat(chapter=2, state="rise", intensity=0.6, description="Rise"),
    ]
    arc = NarrativeArc(
        type="character_arc",
        entity_id="velik",
        name="Путь Велика",
        arc_type="hero_journey",
        beats=beats,
        resolution="Обрёл знание",
    )
    assert arc.type == "character_arc"
    assert arc.entity_id == "velik"
    assert len(arc.beats) == 2
    assert arc.beats[0].state == "introduction"
    assert arc.beats[1].state == "rise"


def test_extract_character_arcs():
    chars = [
        {"id": "velik", "name": "Велик", "archetype": "Искатель", "first_chapter": 1, "last_chapter": 5},
        {"id": "old_sage", "name": "Старец", "archetype": "Мудрец", "first_chapter": 1, "last_chapter": 3},
    ]
    confs = [{"id": "c1", "name": "Конфликт 1"}]
    themes = [{"id": "t1", "name": "Тема 1", "strength": 0.8}]
    timeline = [{"chapter": i} for i in range(1, 8)]

    arcs = extract_narrative_arcs(chars, confs, themes, timeline)
    assert len(arcs) >= 2  # минимум 2 персонажа

    char_arcs = [a for a in arcs if a["type"] == "character_arc"]
    plot_arcs = [a for a in arcs if a["type"] == "plot_arc"]
    thematic_arcs = [a for a in arcs if a["type"] == "thematic_arc"]

    assert len(char_arcs) == 2
    assert len(plot_arcs) == 1
    assert len(thematic_arcs) >= 1

    # Проверим структуру дуги Велика
    velik_arc = [a for a in char_arcs if a["entity_id"] == "velik"][0]
    assert velik_arc["arc_type"] == "hero_journey"
    assert len(velik_arc["beats"]) == 5
    assert velik_arc["beats"][0]["state"] == "introduction"
    assert velik_arc["beats"][-1]["state"] == "resolution"
    assert velik_arc["resolution"] == "Обрёл знание и предназначение"

    # Проверим дугу Старца
    sage_arc = [a for a in char_arcs if a["entity_id"] == "old_sage"][0]
    assert sage_arc["arc_type"] == "transformation"
    assert len(sage_arc["beats"]) == 3
    assert sage_arc["resolution"] == "Передал знание следующему поколению"


def test_extract_arcs_empty():
    arcs = extract_narrative_arcs([], [], [], [])
    assert len(arcs) == 0  # пустые входы = пустой результат


def test_character_arc_all_archetypes():
    for archetype in CHARACTER_ARC_TYPES:
        assert CHARACTER_ARC_TYPES[archetype] in ("hero_journey", "transformation", "rise_fall", "tragedy", "comedy")


def test_arc_intensity_monotonic():
    chars = [{"id": "hero", "name": "Hero", "archetype": "Искатель", "first_chapter": 1, "last_chapter": 10}]
    timeline = [{"chapter": i} for i in range(1, 12)]
    arcs = extract_narrative_arcs(chars, [], [], timeline)
    hero_arc = [a for a in arcs if a["entity_id"] == "hero"][0]
    intensities = [b["intensity"] for b in hero_arc["beats"]]
    # intensity растёт до пика, потом падает
    peak_idx = intensities.index(max(intensities))
    for i in range(peak_idx):
        assert intensities[i] <= intensities[i + 1] + 0.01
    for i in range(peak_idx, len(intensities) - 1):
        assert intensities[i] >= intensities[i + 1] - 0.01


def test_arc_provenance_present():
    chars = [{"id": "velik", "name": "Велик", "archetype": "Искатель", "first_chapter": 1, "last_chapter": 5}]
    confs = [{"id": "conf_1", "name": "Конфликт 1"}]
    themes = [{"id": "theme_1", "name": "Тема 1", "strength": 0.8}]
    timeline = [{"chapter": i} for i in range(1, 7)]
    arcs = extract_narrative_arcs(chars, confs, themes, timeline)
    for arc in arcs:
        assert arc["provenance"], f"нет provenance у {arc['type']}"
        assert arc["provenance"][0].startswith("genome.modules.")
    char_arc = [a for a in arcs if a["type"] == "character_arc"][0]
    assert char_arc["provenance"] == ["genome.modules.characters:velik"]
    plot_arc = [a for a in arcs if a["type"] == "plot_arc"][0]
    assert plot_arc["provenance"] == ["genome.modules.conflicts:conf_1"]
    theme_arc = [a for a in arcs if a["type"] == "thematic_arc"][0]
    assert theme_arc["provenance"] == ["genome.modules.themes:theme_1"]


def test_arc_incomplete_marks_missing_bounds():
    chars = [{"id": "no_bounds", "name": "Без границ", "archetype": "Искатель", "first_chapter": None, "last_chapter": None}]
    timeline = [{"chapter": i} for i in range(1, 6)]
    arcs = extract_narrative_arcs(chars, [], [], timeline)
    arc = arcs[0]
    assert arc["incomplete"] is True
    assert "missing chapter bounds" in arc["incomplete_reason"]


def test_arc_incomplete_marks_unknown_archetype():
    chars = [{"id": "x", "name": "X", "archetype": "Неизвестный", "first_chapter": 1, "last_chapter": 3}]
    timeline = [{"chapter": i} for i in range(1, 4)]
    arcs = extract_narrative_arcs(chars, [], [], timeline)
    arc = arcs[0]
    assert arc["incomplete"] is True
    assert "unknown archetype" in arc["incomplete_reason"]


def test_arc_complete_when_fully_linked():
    chars = [{"id": "full", "name": "Полный", "archetype": "Искатель", "first_chapter": 1, "last_chapter": 4}]
    timeline = [{"chapter": i} for i in range(1, 5)]
    arcs = extract_narrative_arcs(chars, [], [], timeline)
    arc = arcs[0]
    assert arc["incomplete"] is False
    assert arc["incomplete_reason"] == ""


def test_beat_emotions_mapped():
    chars = [{"id": "h", "name": "H", "archetype": "Хранитель", "first_chapter": 1, "last_chapter": 4}]
    timeline = [{"chapter": i} for i in range(1, 6)]
    arcs = extract_narrative_arcs(chars, [], [], timeline)
    beats = arcs[0]["beats"]
    emotions = {b["emotion"] for b in beats}
    assert emotions.issubset({"warm_intimate", "hopeful_golden", "dramatic_contrast", "melancholic_dark", "calm_acceptance", "neutral"})


if __name__ == "__main__":
    test_schema_beat()
    test_schema_narrative_arc()
    test_extract_character_arcs()
    test_extract_arcs_empty()
    test_character_arc_all_archetypes()
    test_arc_intensity_monotonic()
    test_beat_emotions_mapped()
    test_arc_provenance_present()
    test_arc_incomplete_marks_missing_bounds()
    test_arc_incomplete_marks_unknown_archetype()
    test_arc_complete_when_fully_linked()
    print("All tests passed")
