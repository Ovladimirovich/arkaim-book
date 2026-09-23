"""Tests for Narrative Engine — Story Store (SQLite persistence)."""

import sys
import tempfile
from pathlib import Path
from datetime import datetime, timezone

import pytest

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

# Override DB path before import
import narrative_engine.story.store as store_module


@pytest.fixture(autouse=True)
def temp_db(tmp_path):
    """Use temporary database for each test."""
    original_path = store_module.DB_PATH
    store_module.DB_PATH = tmp_path / "test_stories.db"
    store_module.init_db()
    yield
    store_module.DB_PATH = original_path


class TestStoryStore:
    def test_save_and_get_story(self):
        story = {
            "id": "test001",
            "text": "Тестовая история о Гиперборее.",
            "word_count": 5,
            "prompt": "Расскажи о Гиперборее",
            "constraints": {"epoch": "satya_yuga"},
            "validation": {"passed": True, "score": 0.95},
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        store_module.save_story(story)

        retrieved = store_module.get_story("test001")
        assert retrieved is not None
        assert retrieved["id"] == "test001"
        assert retrieved["text"] == "Тестовая история о Гиперборее."
        assert retrieved["word_count"] == 5
        assert retrieved["constraints"]["epoch"] == "satya_yuga"

    def test_get_nonexistent_story(self):
        result = store_module.get_story("nonexistent")
        assert result is None

    def test_get_stories_list(self):
        for i in range(5):
            store_module.save_story({
                "id": f"story_{i:03d}",
                "text": f"История номер {i}",
                "word_count": 3,
                "prompt": f"Промпт {i}",
                "constraints": {},
                "validation": {},
                "created_at": datetime.now(tz=timezone.utc).isoformat(),
            })

        stories = store_module.get_stories(limit=3)
        assert len(stories) == 3
        # Most recent first
        assert stories[0]["id"] == "story_004"
        assert stories[2]["id"] == "story_002"

    def test_delete_story(self):
        store_module.save_story({
            "id": "to_delete",
            "text": "Удаляемая история",
            "word_count": 2,
            "prompt": "test",
            "constraints": {},
            "validation": {},
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
        })
        assert store_module.get_story("to_delete") is not None

        deleted = store_module.delete_story("to_delete")
        assert deleted is True
        assert store_module.get_story("to_delete") is None

    def test_count_stories(self):
        assert store_module.count_stories() == 0
        store_module.save_story({
            "id": "count_test",
            "text": "test",
            "word_count": 1,
            "prompt": "",
            "constraints": {},
            "validation": {},
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
        })
        assert store_module.count_stories() == 1

    def test_json_fields_parse_correctly(self):
        story = {
            "id": "json_test",
            "text": "test",
            "word_count": 1,
            "prompt": "test",
            "constraints": {"nested": {"key": "value"}},
            "validation": {"violations": [{"rule_id": "test"}]},
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        store_module.save_story(story)
        retrieved = store_module.get_story("json_test")
        assert retrieved["constraints"]["nested"]["key"] == "value"
        assert retrieved["validation"]["violations"][0]["rule_id"] == "test"
