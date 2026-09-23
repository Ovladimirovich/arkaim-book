"""Tests for Narrative Engine — World Model."""

import sys
from pathlib import Path

import pytest

# Add core/CORE to path
CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from narrative_engine.source_levels import SourceLevel, ProvenanceTag, SOURCE_LEVEL_LABELS
from narrative_engine.world_model import (
    WorldModel, Epoch, Location, Civilization, Technology,
    CharacterPresence, CanonicalEvent, CausalRule,
)


class TestSourceLevels:
    def test_all_levels_exist(self):
        assert len(SourceLevel) == 7

    def test_canon_value(self):
        assert SourceLevel.CANON == "CANON"

    def test_labels_have_all_levels(self):
        for level in SourceLevel:
            assert level in SOURCE_LEVEL_LABELS

    def test_provenance_tag_creation(self):
        tag = ProvenanceTag(
            source_level=SourceLevel.CANON,
            confidence=0.95,
            added_by="system",
        )
        assert tag.source_level == SourceLevel.CANON
        assert tag.confidence == 0.95

    def test_provenance_tag_confidence_bounds(self):
        with pytest.raises(Exception):
            ProvenanceTag(source_level=SourceLevel.CANON, confidence=1.5)


class TestWorldModel:
    def test_load_empty(self):
        wm = WorldModel({})
        assert wm.summary() == "Мир: 0 эпох, 0 локаций, 0 событий, 0 правил, 0 технологий, 0 цивилизаций, 0 параллелей, 0 связей персонажей"

    def test_load_with_data(self):
        data = {
            "epochs": [{"id": "test", "name": "Test", "name_ru": "Тест", "order": 1}],
            "locations": [{"id": "loc1", "name": "Loc1", "name_ru": "Лок1", "type": "city"}],
            "canonical_events": [],
            "causal_rules": [],
        }
        wm = WorldModel(data)
        assert len(wm.get_epochs()) == 1
        assert wm.get_epochs()[0].id == "test"

    def test_get_epoch(self):
        data = {
            "epochs": [
                {"id": "epoch1", "name": "E1", "name_ru": "Эпоха 1", "order": 1},
                {"id": "epoch2", "name": "E2", "name_ru": "Эпоха 2", "order": 2},
            ],
            "locations": [],
            "canonical_events": [],
            "causal_rules": [],
        }
        wm = WorldModel(data)
        epoch = wm.get_epoch("epoch1")
        assert epoch is not None
        assert epoch.name == "E1"
        assert wm.get_epoch("nonexistent") is None

    def test_get_epochs_sorted_by_order(self):
        data = {
            "epochs": [
                {"id": "b", "name": "B", "name_ru": "B", "order": 2},
                {"id": "a", "name": "A", "name_ru": "A", "order": 1},
            ],
            "locations": [],
            "canonical_events": [],
            "causal_rules": [],
        }
        wm = WorldModel(data)
        epochs = wm.get_epochs()
        assert epochs[0].id == "a"
        assert epochs[1].id == "b"

    def test_get_locations_filtered_by_epoch(self):
        data = {
            "epochs": [],
            "locations": [
                {"id": "l1", "name": "L1", "name_ru": "Л1", "type": "city", "epochs_present": ["e1"]},
                {"id": "l2", "name": "L2", "name_ru": "Л2", "type": "city", "epochs_present": ["e2"]},
            ],
            "canonical_events": [],
            "causal_rules": [],
        }
        wm = WorldModel(data)
        assert len(wm.get_locations("e1")) == 1
        assert wm.get_locations("e1")[0].id == "l1"

    def test_characters_living(self):
        data = {
            "epochs": [],
            "locations": [],
            "canonical_events": [],
            "causal_rules": [],
            "characters_living": {
                "satya_yuga": [
                    {"character_name": "Велик", "epoch": "satya_yuga", "status": "alive"},
                ]
            },
        }
        wm = WorldModel(data)
        chars = wm.get_characters_alive("satya_yuga")
        assert len(chars) == 1
        assert chars[0].character_name == "Велик"
        assert wm.get_characters_alive("other_epoch") == []

    def test_find_epoch_by_text(self):
        data = {
            "epochs": [
                {"id": "kali_yuga", "name": "Kali Yuga", "name_ru": "Кали Юга", "order": 4},
            ],
            "locations": [],
            "canonical_events": [],
            "causal_rules": [],
        }
        wm = WorldModel(data)
        assert wm.find_epoch_by_text("Что такое Кали Юга?") is not None
        assert wm.find_epoch_by_text("Привет") is None

    def test_find_location_by_text(self):
        data = {
            "epochs": [],
            "locations": [
                {"id": "hyperborea", "name": "Hyperborea", "name_ru": "Гиперборея", "type": "region"},
            ],
            "canonical_events": [],
            "causal_rules": [],
        }
        wm = WorldModel(data)
        assert wm.find_location_by_text("Расскажи о Гиперборее") is not None
        assert wm.find_location_by_text("Привет") is None

    def test_get_constraints_for(self):
        data = {
            "epochs": [{"id": "e1", "name": "E1", "name_ru": "Эпоха 1", "order": 1}],
            "locations": [{"id": "l1", "name": "L1", "name_ru": "Л1", "type": "city"}],
            "canonical_events": [],
            "causal_rules": [{"id": "r1", "description": "Правило", "rule_type": "exclusion"}],
            "characters_living": {"e1": [{"character_name": "Тест", "epoch": "e1", "status": "alive"}]},
        }
        wm = WorldModel(data)
        c = wm.get_constraints_for("e1", "l1")
        assert len(c["epochs"]) == 1
        assert len(c["locations"]) == 1
        assert len(c["characters_alive"]) == 1
        assert len(c["rules"]) == 1

    def test_summary(self):
        data = {
            "epochs": [{"id": "e1", "name": "E1", "name_ru": "E1", "order": 1}],
            "locations": [{"id": "l1", "name": "L1", "name_ru": "L1", "type": "city"}],
            "canonical_events": [{"id": "ev1", "title": "Ev1", "title_ru": "Ev1", "epoch": "e1", "order_in_epoch": 1}],
            "causal_rules": [{"id": "r1", "description": "R1", "rule_type": "exclusion"}],
        }
        wm = WorldModel(data)
        s = wm.summary()
        assert "1 эпох" in s
        assert "1 локаций" in s
        assert "1 событий" in s
        assert "1 правил" in s


# ── TEMPORAL_LEGACY_REFINEMENT: Character Relations + Epoch Parallels ──


class TestCharacterRelations:
    """Character cross-reference: mentor/student/peer relations."""

    def _make_wm(self):
        data = {
            "epochs": [{"id": "e1", "name": "E1", "name_ru": "E1", "order": 1}],
            "characters_living": {
                "e1": [
                    {
                        "character_name": "Учитель",
                        "epoch": "e1",
                        "status": "alive",
                        "relations": [
                            {"type": "mentor_of", "target": "Велик", "provenance": "AUTHOR_CANON"},
                            {"type": "mentor_of", "target": "Наставники", "provenance": "AUTHOR_CANON"},
                        ],
                    },
                    {
                        "character_name": "Велик",
                        "epoch": "e1",
                        "status": "alive",
                        "relations": [
                            {"type": "student_of", "target": "Учитель", "provenance": "AUTHOR_CANON"},
                            {"type": "mentor_of", "target": "Мирослав", "provenance": "AUTHOR_CANON"},
                        ],
                    },
                    {
                        "character_name": "Мирослав",
                        "epoch": "e1",
                        "status": "alive",
                        "relations": [
                            {"type": "student_of", "target": "Велик", "provenance": "AUTHOR_CANON"},
                        ],
                    },
                ],
            },
            "character_relations": [
                {"character": "Учитель", "relation": "mentor_of", "target": "Велик"},
                {"character": "Велик", "relation": "mentor_of", "target": "Мирослав"},
            ],
        }
        return WorldModel(data)

    def test_character_has_relations_field(self):
        wm = self._make_wm()
        chars = wm.get_characters_alive("e1")
        teacher = [c for c in chars if c.character_name == "Учитель"][0]
        assert len(teacher.relations) == 2

    def test_character_relations_roundtrip(self):
        wm = self._make_wm()
        chars = wm.get_characters_alive("e1")
        velik = [c for c in chars if c.character_name == "Велик"][0]
        assert velik.relations[0]["type"] == "student_of"
        assert velik.relations[0]["target"] == "Учитель"

    def test_get_character_relations_all(self):
        wm = self._make_wm()
        all_rels = wm.get_character_relations()
        assert len(all_rels) == 2

    def test_get_character_relations_by_name(self):
        wm = self._make_wm()
        teacher_rels = wm.get_character_relations("Учитель")
        assert len(teacher_rels) == 1
        assert teacher_rels[0].relation == "mentor_of"

    def test_get_character_mentors(self):
        wm = self._make_wm()
        mentors = wm.get_character_mentors("Велик")
        assert "Учитель" in mentors

    def test_get_character_students(self):
        wm = self._make_wm()
        students = wm.get_character_students("Учитель")
        assert "Велик" in students


class TestEpochParallels:
    """Temporal parallels / echoes between epochs."""

    def _make_wm(self):
        data = {
            "epochs": [
                {"id": "e1", "name": "E1", "name_ru": "E1", "order": 1},
                {"id": "e2", "name": "E2", "name_ru": "E2", "order": 2},
            ],
            "epoch_parallels": [
                {
                    "source": "e1",
                    "target": "e2",
                    "description": "structural parallel test",
                    "provenance": [{"source_level": "SYSTEM_INTERPRETATION", "category": "HYPOTHESIS", "confidence": 0.5, "notes": "test"}],
                },
            ],
        }
        return WorldModel(data)

    def test_epoch_parallels_loaded(self):
        wm = self._make_wm()
        parallels = wm.get_epoch_parallels()
        assert len(parallels) == 1

    def test_epoch_parallel_has_source_target(self):
        wm = self._make_wm()
        p = wm.get_epoch_parallels()[0]
        assert p.source == "e1"
        assert p.target == "e2"

    def test_epoch_parallel_has_provenance(self):
        wm = self._make_wm()
        p = wm.get_epoch_parallels()[0]
        assert len(p.provenance) == 1

    def test_summary_includes_parallels(self):
        wm = self._make_wm()
        s = wm.summary()
        assert "1 параллелей" in s

    def test_summary_includes_character_relations(self):
        data = {
            "epochs": [{"id": "e1", "name": "E1", "name_ru": "E1", "order": 1}],
            "character_relations": [
                {"character": "A", "relation": "mentor_of", "target": "B"},
            ],
        }
        wm = WorldModel(data)
        s = wm.summary()
        assert "1 связей персонажей" in s
