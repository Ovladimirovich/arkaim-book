"""Связи 119 сцен сценария с World Model: происхождение, честность, неизменность источников."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from knowledge.screenplay_scene_aliases import APPROVED_ALIASES, TERM_SPECS  # noqa: E402
from knowledge.screenplay_scene_catalog import get_scene, list_scenes  # noqa: E402
from knowledge.screenplay_scene_knowledge import extract_characters  # noqa: E402
from knowledge.screenplay_scene_world_links import (  # noqa: E402
    STATUS_AMBIGUOUS,
    STATUS_CONFIRMED,
    STATUS_DERIVED,
    STATUS_UNRESOLVED,
    build_world_links,
)

_PROJECT = _CORE.parent.parent
_ALLOWED_STATUSES = {STATUS_CONFIRMED, STATUS_DERIVED, STATUS_UNRESOLVED, STATUS_AMBIGUOUS}

_SOURCE_FILES = (
    _PROJECT / "core" / "SOURCE_OF_TRUTH" / "SYNOPSIS" / "Наследие_Аркаима_Сценарий_Full.md",
    _PROJECT / "core" / "KNOWLEDGE" / "SYNOPSIS_DOCUMENT.json",
    _PROJECT / "core" / "KNOWLEDGE" / "screenplay_links.json",
    _PROJECT / "core" / "KNOWLEDGE" / "claim_temporal_links.json",
    _PROJECT / "core" / "KNOWLEDGE" / "enriched_chunks.json",
    _PROJECT / "core" / "CORE" / "narrative_engine" / "data" / "WORLD_MODEL.json",
    _PROJECT / "core" / "CORE" / "WORLD_CROSSWALK" / "WORLD_ENGINE_WORLD_MODEL.json",
)


@lru_cache(maxsize=1)
def _scenes() -> tuple[dict, ...]:
    return tuple(list_scenes())


@lru_cache(maxsize=1)
def _world_character_names() -> frozenset[str]:
    from narrative_engine.world_model import WorldModel

    world = WorldModel.load()
    names: set[str] = set()
    for epoch in world.get_epochs():
        for presence in world.get_characters_alive(epoch.id):
            names.add(presence.character_name)
    return frozenset(names)


@lru_cache(maxsize=1)
def _approved_links() -> tuple[tuple[str, str], ...]:
    raw = json.loads((_PROJECT / "core" / "KNOWLEDGE" / "screenplay_links.json").read_text(encoding="utf-8"))
    return tuple((item["screenplay_scene_id"], item["book_chunk_id"]) for item in raw)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _scene(scene_id: str) -> dict:
    return next(scene for scene in _scenes() if scene["scene_id"] == scene_id)


def _links(scene: dict, link_type: str, status: str | None = None) -> list[dict]:
    return [link for link in scene["world_links"] if link["link_type"] == link_type and (status is None or link["status"] == status)]


def test_every_scene_exposes_world_link_contract():
    scenes = _scenes()
    assert len(scenes) == 119

    for scene in scenes:
        assert isinstance(scene["world_links"], list)
        assert isinstance(scene["world_link_missing"], dict)
        summary = scene["world_link_summary"]
        assert summary["total"] == len(scene["world_links"])
        assert summary["confirmed"] + summary["derived"] + summary["unresolved"] + summary["ambiguous"] == summary["total"]
        for link in scene["world_links"]:
            assert link["status"] in _ALLOWED_STATUSES
            assert link["link_type"]
            assert link["basis"]
            assert "provenance" in link
            assert "source_files" in link
            if link["status"] in {STATUS_UNRESOLVED, STATUS_AMBIGUOUS}:
                assert link["target_id"] == ""


def test_confirmed_event_requires_approved_chain():
    scene = _scene("scene_004")
    events = _links(scene, "event", STATUS_CONFIRMED)

    assert len(events) == 1
    event = events[0]
    assert event["target_id"] == "event_cosmic_impulse"
    assert event["epoch_id"] == "pre_arkaim"
    assert event["temporal_node_id"] == "temporal_pre_arkaim"
    assert [step["step"] for step in event["chain"]] == [
        "screenplay_scene",
        "book_chunk",
        "claim",
        "temporal_node",
        "world_event",
    ]
    assert event["provenance"]["category"] == "AUTHOR_CANON"
    assert "core/KNOWLEDGE/claim_temporal_links.json" in event["source_files"]


def test_book_link_without_claim_link_stays_unresolved():
    scene = _scene("scene_003")
    events = _links(scene, "event")

    assert len(events) == 1
    assert events[0]["status"] == STATUS_UNRESOLVED
    assert "claim" in events[0]["basis"]
    assert scene["book_links"], "сцена без одобренной книжной связи не должна иметь связей по книге"


def test_no_confirmed_event_without_approved_book_link():
    approved = set(_approved_links())
    for scene in _scenes():
        for link in _links(scene, "event", STATUS_CONFIRMED):
            assert (scene["scene_id"], link["book_chunk_id"]) in approved


def test_character_links_are_exact_name_matches():
    world_names = _world_character_names()
    for scene in _scenes():
        for link in _links(scene, "character", STATUS_CONFIRMED):
            assert link["target_id"] in world_names

    scene = _scene("scene_034")
    characters = _links(scene, "character", STATUS_CONFIRMED)
    assert [link["target_id"] for link in characters] == ["Велик"]
    assert characters[0]["epochs"] == ["satya_yuga"]


def test_world_duplicate_records_are_not_merged():
    scene = _scene("scene_117")
    targets = [link["target_id"] for link in _links(scene, "character", STATUS_CONFIRMED)]

    assert "Славный" in targets
    assert "Мирослав" not in targets
    assert "Мирослав (Славный)" not in targets
    assert "Велик (Велиусмус)" not in targets


def test_relation_link_requires_both_characters_in_scene():
    scene = _scene("scene_050")
    relations = _links(scene, "character_relation")

    assert len(relations) == 1
    relation = relations[0]
    assert relation["status"] == STATUS_DERIVED
    assert relation["character"] == "Световит"
    assert relation["target"] == "Велик"
    assert set(scene["characters"]) >= {relation["character"], relation["target"]}


def test_location_links_require_exact_match():
    for scene in _scenes():
        for link in _links(scene, "location", STATUS_CONFIRMED):
            pytest.fail(f"подтверждённая локация без точного совпадения: {scene['scene_id']}")

    scene = _scene("scene_019")
    locations = _links(scene, "location")
    assert len(locations) == 1
    assert locations[0]["status"] == STATUS_DERIVED
    assert locations[0]["target_id"] == "океания"
    assert "LOCATION_VISUALS" in locations[0]["basis"]


def test_approved_place_forms_create_mention_links():
    """Утверждённые владельцем формы дают отдельные связи-упоминания."""
    cases = {
        "scene_020": ("океания", "Океании"),
        "scene_030": ("гиперборея", "Гиперборею"),
        "scene_047": ("океания", "Океании"),
        "scene_050": ("океания", "Атлантиды"),
        "scene_077": ("гиперборея", "Гиперборее"),
        "scene_113": ("океания", "Океании"),
        "scene_117": ("аркаим", "Аркаима"),
    }
    for scene_id, (target_id, form) in cases.items():
        scene = get_scene(scene_id)
        mentions = [link for link in scene["world_links"] if link["link_type"] == "location_mention"]
        assert len(mentions) == 1, f"{scene_id}: упоминаний {len(mentions)}"
        mention = mentions[0]
        assert mention["target_id"] == target_id
        assert mention["status"] == "DERIVED"
        assert mention.get("mention_only") is True
        assert mention.get("matched_forms") == [form]
        assert mention["provenance"]["source_level"] == "AUTHOR_INTERPRETATION"
        assert "core/KNOWLEDGE/place_mention_forms.json" in mention["source_files"]


def test_people_and_epoch_forms_never_become_locations():
    """Формы людей и эпох не дают связей-локаций."""
    forbidden = ("Гипербореи", "гипербореев", "гиперборейцев", "Наставник", "Учител", "Кали Юга", "Сати Юга")
    for scene in list_scenes():
        for link in scene["world_links"]:
            if link["link_type"] != "location_mention":
                continue
            for form in link.get("matched_forms") or []:
                assert not any(form.lower().startswith(word.lower()) for word in forbidden), f"{scene['scene_id']}: форма {form!r} ошибочно принята за место"


def test_mention_is_not_the_place_of_action():
    """Упоминание места не превращается в место действия сцены."""
    scene = get_scene("scene_030")

    locations = [link for link in scene["world_links"] if link["link_type"] == "location"]
    mentions = [link for link in scene["world_links"] if link["link_type"] == "location_mention"]

    assert locations and locations[0]["status"] == "UNRESOLVED"
    assert mentions and mentions[0]["status"] == "DERIVED"
    assert locations[0]["target_id"] == ""


def test_place_mention_targets_exist_in_world_model():
    from narrative_engine.world_model import WorldModel

    known = {location.id for location in WorldModel.load().get_locations()}
    for scene in list_scenes():
        for link in scene["world_links"]:
            if link["link_type"] == "location_mention" and link["status"] == "DERIVED":
                assert link["target_id"] in known, f"{scene['scene_id']}: неизвестная локация {link['target_id']}"


def test_place_mention_registry_fails_closed(monkeypatch):
    """Без реестра форм упоминания не создаются — и сцена не падает."""
    from knowledge import screenplay_scene_world_links as world_links

    monkeypatch.setattr(
        world_links,
        "_place_mentions_path",
        lambda: Path("C:/nonexistent/place_mention_forms.json"),
    )
    assert world_links._load_place_mention_records() == ()


def test_place_mention_registry_is_owner_approved():
    import json

    registry = json.loads((_PROJECT / "core" / "KNOWLEDGE" / "place_mention_forms.json").read_text(encoding="utf-8"))
    assert registry["status"] == "APPROVED"
    assert registry["_provenance_metadata"]["notes"]
    assert registry["places"]
    for place in registry["places"]:
        assert place["location_id"]
        assert place["forms"]
        assert "excluded_forms" in place


def test_oceania_is_resolved_and_mention_is_a_separate_link():
    """Океания одобрена владельцем: локация сцены и упоминание — разные связи."""
    scene = get_scene("scene_021")

    locations = [link for link in scene["world_links"] if link["link_type"] == "location"]
    assert len(locations) == 1
    assert locations[0]["status"] == "DERIVED"
    assert locations[0]["target_id"] == "океания"

    mentions = [link for link in scene["world_links"] if link["link_type"] == "location_mention"]
    assert len(mentions) == 1
    assert mentions[0]["status"] == "DERIVED"
    assert mentions[0].get("mention_only") is True
    assert mentions[0]["target_id"] == "океания"

    # Упоминание не выдаётся за локацию сцены.
    assert locations[0]["link_type"] != mentions[0]["link_type"]
    assert "Океания" in mentions[0]["basis"]


def test_unresolved_location_states_reason():
    scene = _scene("scene_013")
    locations = _links(scene, "location")

    assert len(locations) == 1
    assert locations[0]["status"] == STATUS_UNRESOLVED
    assert "World Model" in locations[0]["basis"]
    assert scene["world_link_missing"]["location"]


def test_unknown_character_is_not_linked():
    result = build_world_links(
        {
            "scene_id": "scene_test",
            "characters": ["Неизвестный Персонаж"],
            "location_name": "",
            "location_id": "",
        }
    )
    characters = [link for link in result["world_links"] if link["link_type"] == "character"]

    assert len(characters) == 1
    assert characters[0]["status"] == STATUS_UNRESOLVED
    assert characters[0]["target_id"] == ""


def test_approved_alias_table_is_not_expanded():
    assert APPROVED_ALIASES == {
        "Велик": ("Велиусмус", "Великосвет", "Велом", "Вел", "Велика"),
        "Влад": ("Владислав",),
        "Вера": ("Вероника",),
        "Славный": ("Мирослав", "Славик"),
        "Гипербореи": ("гиперборейцы",),
    }
    for canonical, surfaces in APPROVED_ALIASES.items():
        for surface in surfaces:
            assert extract_characters(surface) == [canonical], f"{surface} → {canonical} не согласован с таблицей правил"
    assert len(TERM_SPECS) == 28


def test_sources_are_not_modified_by_linking():
    before = {path: _hash(path) for path in _SOURCE_FILES}
    list_scenes()
    get_scene("scene_004")
    after = {path: _hash(path) for path in _SOURCE_FILES}
    assert before == after


def test_report_is_up_to_date():
    script = _PROJECT / "scripts" / "generate_screenplay_world_links_report.py"
    result = subprocess.run(
        [sys.executable, str(script), "--check"],
        cwd=str(_PROJECT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_report_source_counts_match_data():
    """Числа в разделе «Источники» отчёта равны фактическим данным.

    Раньше эти числа были захардкожены и разошлись с данными
    (указывалось 9 записей claim_temporal_links вместо 15 и 2 соответствия
    crosswalk вместо 3). Теперь они вычисляются при генерации.
    """
    import json

    script = _PROJECT / "scripts" / "generate_screenplay_world_links_report.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(_PROJECT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = (_PROJECT / "docs" / "SCREENPLAY_SCENE_WORLD_LINKS_REPORT.md").read_text(encoding="utf-8")

    knowledge = _PROJECT / "core" / "KNOWLEDGE"
    screenplay_links = json.loads((knowledge / "screenplay_links.json").read_text(encoding="utf-8-sig"))
    claim_links = json.loads((knowledge / "claim_temporal_links.json").read_text(encoding="utf-8-sig"))
    crosswalk = json.loads((_PROJECT / "core" / "CORE" / "WORLD_CROSSWALK" / "WORLD_ENGINE_WORLD_MODEL.json").read_text(encoding="utf-8-sig"))
    approved = [m for m in crosswalk["mappings"] if m.get("status", "APPROVED") == "APPROVED"]

    assert f"сценарий↔книга ({len(screenplay_links)})" in report
    assert f"claim→событие/эпоха ({len(claim_links)})" in report
    assert f"одобренные соответствия ({len(approved)})" in report
