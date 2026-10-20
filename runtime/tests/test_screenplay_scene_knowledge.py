"""Обогащение 119 сцен существующими знаниями без вымысла и записи в источники."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

_CORE = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from knowledge.screenplay_scene_catalog import EXPECTED_SCENE_COUNT, get_scene, list_scenes  # noqa: E402
from knowledge.screenplay_scene_knowledge import extract_characters  # noqa: E402

_SOURCE_FILES = (
    _CORE.parent / "SOURCE_OF_TRUTH" / "SYNOPSIS" / "Наследие_Аркаима_Сценарий_Full.md",
    _CORE.parent / "KNOWLEDGE" / "SYNOPSIS_DOCUMENT.json",
    _CORE.parent / "KNOWLEDGE" / "character_profiles.json",
    _CORE.parent / "KNOWLEDGE" / "deep_characters.json",
    _CORE.parent / "KNOWLEDGE" / "CHARACTERS.json",
    _CORE.parent / "KNOWLEDGE" / "screenplay_links.json",
    _CORE.parent / "KNOWLEDGE" / "enriched_chunks.json",
    _CORE.parent / "KNOWLEDGE" / "MAP_DATA.json",
    _CORE / "visual" / "VISUAL_KNOWLEDGE" / "LOCATION_VISUALS.json",
)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_catalog_has_only_canonical_119_ids():
    scenes = list_scenes()

    assert len(scenes) == EXPECTED_SCENE_COUNT
    assert [scene["scene_id"] for scene in scenes] == [f"scene_{index:03d}" for index in range(EXPECTED_SCENE_COUNT)]
    assert get_scene("scene_999") is None


def test_approved_aliases_are_canonicalized():
    assert extract_characters("Велиусмус, Великосвет, Велом и Вел") == ["Велик"]
    assert extract_characters("Владислав и Вероника") == ["Влад", "Вера"]
    assert extract_characters("Мирослав и Славик") == ["Славный"]
    assert extract_characters("гиперборейцы") == ["Гипербореи"]


def test_characters_are_not_merged_or_synthesized():
    characters = extract_characters("Архат и Учитель. Учитель Человечества. Посредник. Свет и Световит.")
    assert characters == ["Архат", "Учитель", "Учитель Человечества", "Посредник", "Световит"]

    assert extract_characters("Слава героям, вера в людей, учитель вошёл") == []
    assert extract_characters("Городок Славное") == []


def test_scene_characters_are_honest():
    assert get_scene("scene_034")["characters"] == ["Велик"]
    assert get_scene("scene_013")["characters"] == []
    assert get_scene("scene_118")["characters"] == []
    assert get_scene("scene_000")["characters"] == []


def test_time_of_day_comes_from_scene_title():
    assert get_scene("scene_007")["time_of_day"] == "day"
    assert get_scene("scene_000")["time_of_day"] == ""
    assert "time_of_day" in get_scene("scene_000")["knowledge_missing"]


def test_location_name_and_id_are_exact():
    scene = get_scene("scene_019")
    assert scene["location_name"] == "ОСТРОВА АТЛАНТИДЫ"
    assert scene["location_id"] == "Атлантида"

    location_visuals = json.loads((_CORE / "visual" / "VISUAL_KNOWLEDGE" / "LOCATION_VISUALS.json").read_text(encoding="utf-8"))
    for item in list_scenes():
        if item["location_id"]:
            assert item["location_id"] in location_visuals


def test_book_links_and_context_are_only_approved_pairs():
    scene = get_scene("scene_003")
    assert len(scene["book_links"]) == 1
    assert scene["book_links"][0]["chunk_id"] == "chunk_p_0006_104f39f72f26"
    assert scene["book_context"][0]["text"].startswith("Среди мириад звездных систем")

    scene_020 = get_scene("scene_020")
    assert [link["chunk_id"] for link in scene_020["book_links"]] == [
        "chunk_p_0045_bc4a72fed70b",
        "chunk_p_0046_407df13f675f",
    ]
    assert len(scene_020["book_context"]) == 2

    assert get_scene("scene_000")["book_links"] == []
    assert "book_links" in get_scene("scene_000")["knowledge_missing"]


def test_events_emotion_and_meaning_tags_are_not_invented():
    for scene in list_scenes():
        assert scene["events"] == []
        assert scene["emotion"] == ""
        assert scene["meaning_tags"] == []
        assert "timeline/PLOT" in scene["knowledge_missing"]["events"]
        assert scene["knowledge_missing"]["emotion"]
        assert scene["knowledge_missing"]["meaning_tags"]


def test_enrichment_does_not_change_sources():
    before = {path: _hash(path) for path in _SOURCE_FILES}
    list_scenes()
    get_scene("scene_034")
    after = {path: _hash(path) for path in _SOURCE_FILES}
    assert before == after
