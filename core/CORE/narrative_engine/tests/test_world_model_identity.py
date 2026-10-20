"""Guard идентичности модели мира: только канонические локации, без дублей и не-мест.

Правила, которые охраняет этот тест:
  - у локаций нет двух записей с одинаковым именем (англоязычные id — это
    метки, а не идентичности; crosswalk v2);
  - id локации не совпадает с id эпохи (эпоха и место — разные сущности);
  - в списке локаций нет записей, которые в сценарии означают людей или эпохи
    (перечень утверждён владельцем в core/KNOWLEDGE/place_mention_forms.json);
  - ссылки событий на локации разрешаются;
  - группы людей, убранные из локаций, остались персонажами модели мира.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CORE = ROOT / "core" / "CORE"
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))

from narrative_engine.world_model import WorldModel  # noqa: E402
from narrative_engine.world_model_data import _extract_locations  # noqa: E402

WORLD_MODEL_PATH = CORE / "narrative_engine" / "data" / "WORLD_MODEL.json"
PLACE_MENTIONS_PATH = ROOT / "core" / "KNOWLEDGE" / "place_mention_forms.json"
PLACE_ALIASES_PATH = ROOT / "core" / "KNOWLEDGE" / "location_aliases.json"


def _world_data() -> dict:
    return json.loads(WORLD_MODEL_PATH.read_text(encoding="utf-8"))


def _never_places() -> list[str]:
    registry = json.loads(PLACE_MENTIONS_PATH.read_text(encoding="utf-8"))
    forms: list[str] = []
    for entry in registry.get("never_places", []):
        forms.extend(str(form) for form in entry.get("forms", []))
    return forms


def test_locations_have_no_duplicate_names():
    """Англоязычные id-дубли (arkaim/arkaim, hyperborea/hyperborea) не возвращаются."""
    data = _world_data()
    names = [
        str(location.get("name_ru") or location.get("name") or "").casefold()
        for location in data["locations"]
    ]

    assert len(names) == len(set(names)), (
        "в locations есть две записи с одинаковым именем"
    )


def test_location_ids_do_not_collide_with_epoch_ids():
    """Эпоха не может быть замаскирована под локацию."""
    data = _world_data()
    epoch_ids = {str(epoch.get("id")) for epoch in data.get("epochs", [])}
    location_ids = {str(location.get("id")) for location in data.get("locations", [])}

    assert not (epoch_ids & location_ids), (
        f"id эпохи повторён в locations: {epoch_ids & location_ids}"
    )


def test_locations_contain_no_people_or_epochs():
    """В локациях нет людей, групп и эпох — перечень утверждён владельцем."""
    never_places = _never_places()
    data = _world_data()

    for location in data.get("locations", []):
        name = str(location.get("name_ru") or location.get("name") or "")
        for forbidden in never_places:
            assert not name.casefold().startswith(forbidden.casefold()), (
                f"{location.get('id')} — не место, а «{forbidden}»"
            )


def test_event_locations_resolve():
    """Каждая ссылка события на локацию разрешается."""
    model = WorldModel.load(use_cache=False)
    for event in model.get_events():
        if event.location_id:
            assert model.get_location(event.location_id) is not None, (
                f"{event.id} ссылается на несуществующую локацию {event.location_id}"
            )


def test_collectives_stay_characters():
    """Группы людей, убранные из локаций, остались персонажами модели мира."""
    model = WorldModel.load(use_cache=False)
    names = {
        presence.character_name
        for epoch in model.get_epochs()
        for presence in model.get_characters_alive(epoch.id)
    }

    assert "Наставники" in names
    assert "Учитель Человечества" in names


def test_mention_targets_exist_as_locations():
    """Цели утверждённых форм-упоминаний — настоящие локации модели мира."""
    registry = json.loads(PLACE_MENTIONS_PATH.read_text(encoding="utf-8"))
    model = WorldModel.load(use_cache=False)
    known = {location.id for location in model.get_locations()}

    for place in registry.get("places", []):
        assert place["location_id"] in known, (
            f"цель упоминания {place['location_id']} не является локацией"
        )


def test_generator_does_not_turn_concepts_into_locations(tmp_path):
    """Мёртвый генератор не вернёт концепты и дубли, если его однажды оживят."""
    genome = {
        "world_entities": [
            {"name": "Аркаим", "type": "location", "description": ""},
            {"name": "Наставники", "type": "concept", "description": ""},
            {"name": "Учителя Человечества", "type": "concept", "description": ""},
            {"name": "Аркаим", "type": "location", "description": "дубль"},
        ]
    }

    locations = _extract_locations(genome, tmp_path)
    ids = {location["id"] for location in locations}

    assert "аркаим" in ids
    assert "наставники" not in ids
    assert "учителя_человечества" not in ids
    assert len(locations) == len(ids)


def test_approved_aliases_point_to_existing_single_locations():
    """Алиас — метка существующего места, а не второе место."""
    registry = json.loads(PLACE_ALIASES_PATH.read_text(encoding="utf-8"))
    data = _world_data()
    location_ids = {str(location.get("id")) for location in data.get("locations", [])}
    location_names = {
        str(location.get("name_ru") or location.get("name") or "").casefold()
        for location in data.get("locations", [])
    }

    for alias in registry.get("aliases", []):
        assert alias["location_id"] in location_ids, (
            f"цель алиаса {alias['location_id']} не является локацией"
        )
        assert str(alias.get("label", "")).casefold() not in location_ids, (
            f"алиас {alias.get('label')} существует как отдельная локация"
        )
        assert str(alias.get("label", "")).casefold() not in location_names, (
            f"алиас {alias.get('label')} существует как отдельное место"
        )
