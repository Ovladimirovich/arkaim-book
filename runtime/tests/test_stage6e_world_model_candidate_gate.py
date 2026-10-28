"""Этап 6e: непроверенный LLM-кандидат не попадает в WORLD MODEL.

Проверяется фактический контур:
  KNOWLEDGE/*.json → world_extraction (pipeline/modules) → WORLD_MODEL/*.json

Два входа:
  1. офлайн-сборка ``create_world_pipeline().extract_all()``
     (scripts/build_world_model.py) — фильтр после экстрактора;
  2. проектор ``traditions.project_world_model`` — читает ``items`` напрямую
     и заполняет пустые оболочки WORLD_MODEL.

Гейт переиспользует предикаты Этапа 6d, второго механизма нет.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_CORE = _PROJECT_ROOT / "core" / "CORE"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from world_extraction.models import ExtractionResult, WorldKnowledge  # noqa: E402
from world_extraction.modules.traditions import (  # noqa: E402
    _items_by_topic,
    _resolve_blank_item_content,
    project_world_model,
)
from world_extraction.provenance import (  # noqa: E402
    build_candidate_index,
    filter_extraction_result,
)

_CANDIDATE_META = {
    "category": "DERIVED",
    "provenance_category": "SYSTEM_INTERPRETATION",
    "source_level": "SYSTEM_INTERPRETATION",
    "source": "LLM",
    "requires_author_review": True,
    "status": "PENDING_REVIEW",
}

_MODULES = (
    "architecture",
    "astronomy",
    "chronology",
    "civilizations",
    "climate",
    "crafts",
    "daily_life",
    "economy",
    "education",
    "fauna",
    "flora",
    "geography",
    "language",
    "mythology",
    "philosophy",
    "religion",
    "rituals",
    "social_structure",
    "technologies",
    "transport",
    "warfare",
)


def _write(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _candidate(topic: str = "Кандидат-проверка") -> dict:
    return {
        "topic": topic,
        "content": "Кандидат: ремесло гончар металлург торговля обмен род семья.",
        "layers": {"literal": "Кандидат: ремесло гончар металлург торговля обмен род семья."},
        "metadata": {"_provenance_metadata": dict(_CANDIDATE_META)},
        "_provenance_metadata": dict(_CANDIDATE_META),
    }


def _verified(topic: str = "Проверенная-тема") -> dict:
    return {
        "topic": topic,
        "content": "Проверенный текст книги о ремесле и роде.",
        "layers": {"literal": "Проверенный текст книги о ремесле и роде."},
    }


def _patch_knowledge_dir(monkeypatch, tmp_path: Path) -> None:
    for name in _MODULES:
        module = importlib.import_module(f"world_extraction.modules.{name}")
        if hasattr(module, "KNOWLEDGE_DIR"):
            monkeypatch.setattr(module, "KNOWLEDGE_DIR", tmp_path)


class TestPipelineGate:
    def test_bare_list_candidate_is_dropped_verified_passes(self, monkeypatch, tmp_path: Path):
        _write(tmp_path / "PHILOSOPHY_DEEP.json", [_candidate(), _verified()])
        _patch_knowledge_dir(monkeypatch, tmp_path)
        from world_extraction.pipeline import create_world_pipeline

        manifest = create_world_pipeline().extract_all()

        names = {item.name for item in manifest.categories["philosophy"].items}
        assert names == {"Проверенная-тема"}, names

    def test_wrapped_candidate_is_dropped_verified_passes(self, tmp_path: Path):
        """Тот же фильтр, но для сегодняшнего wrapped-формата пайплайна."""
        _write(
            tmp_path / "THEMES_EXPANDED.json",
            {
                "_provenance_metadata": {"category": "DERIVED"},
                "items": [_candidate(), _verified()],
            },
        )
        result = ExtractionResult(
            category="crafts",
            source_files=[tmp_path / "THEMES_EXPANDED.json"],
            items=[
                WorldKnowledge(id="c", name="Кандидат-проверка", source="THEMES_EXPANDED.json"),
                WorldKnowledge(id="v", name="Проверенная-тема", source="THEMES_EXPANDED.json"),
            ],
        )

        dropped = filter_extraction_result(result)

        assert dropped == 1
        assert [item.name for item in result.items] == ["Проверенная-тема"]
        assert result.items_count == 1

    def test_file_level_candidate_blocks_whole_source(self, tmp_path: Path):
        _write(
            tmp_path / "COSMOLOGY.json",
            {
                "_provenance_metadata": dict(_CANDIDATE_META),
                "items": [_verified("Обычная-тема")],
            },
        )
        result = ExtractionResult(
            category="astronomy",
            source_files=[tmp_path / "COSMOLOGY.json"],
            items=[
                WorldKnowledge(id="a", name="Обычная-тема", source="COSMOLOGY.json"),
                WorldKnowledge(id="b", name="Другая-тема", source="COSMOLOGY.json"),
            ],
        )

        assert filter_extraction_result(result) == 2
        assert result.items == []

    def test_approved_record_still_passes(self, tmp_path: Path):
        approved = _verified("Одобренная-тема")
        approved["_provenance_metadata"] = {
            "requires_author_review": True,
            "status": "APPROVED",
        }
        _write(
            tmp_path / "SYMBOLS_DEEP.json",
            {"_provenance_metadata": {"category": "DERIVED"}, "items": [approved]},
        )
        result = ExtractionResult(
            category="mythology",
            source_files=[tmp_path / "SYMBOLS_DEEP.json"],
            items=[WorldKnowledge(id="m", name="Одобренная-тема", source="SYMBOLS_DEEP.json")],
        )

        assert filter_extraction_result(result) == 0
        assert len(result.items) == 1

    def test_same_topic_from_other_file_is_not_dropped(self, tmp_path: Path):
        _write(tmp_path / "THEMES_EXPANDED.json", [_candidate("Аркаим")])
        result = ExtractionResult(
            category="geography",
            source_files=[tmp_path / "THEMES_EXPANDED.json"],
            items=[WorldKnowledge(id="g", name="Аркаим", source="MAP_DATA.json")],
        )

        assert filter_extraction_result(result) == 0
        assert len(result.items) == 1

    def test_candidate_index_reads_containers(self, tmp_path: Path):
        _write(
            tmp_path / "SYMBOLS_DEEP.json",
            {
                "_provenance_metadata": {"category": "DERIVED"},
                "items": [_candidate("Символ-кандидат")],
            },
        )

        index = build_candidate_index([tmp_path / "SYMBOLS_DEEP.json"])

        assert "символ-кандидат" in index.topics_by_file["SYMBOLS_DEEP.json"]
        assert index.blocked_files == set()


class TestTraditionsProjectionGate:
    @staticmethod
    def _workspace(tmp_path: Path, symbols_payload: dict, blank_name: str):
        wm = tmp_path / "WORLD_MODEL"
        kw = tmp_path / "KNOWLEDGE"
        wm.mkdir()
        kw.mkdir()
        _write(
            wm / "MYTHOLOGY.json",
            [
                {
                    "id": f"myth_{blank_name.lower()}",
                    "name": blank_name,
                    "description": "",
                    "provenance_category": "UNKNOWN",
                }
            ],
        )
        _write(kw / "SYMBOLS_DEEP.json", symbols_payload)
        _write(kw / "COSMOLOGY.json", {"_provenance_metadata": {"category": "DERIVED"}, "items": []})
        _write(kw / "ESOTERIC_CONNECTIONS.json", {"traditions": []})
        _write(kw / "RITUALS.json", {"items": []})
        return wm, kw

    def test_candidate_does_not_fill_world_model_shell(self, tmp_path: Path):
        wm, kw = self._workspace(
            tmp_path,
            {
                "_provenance_metadata": {"category": "DERIVED"},
                "items": [_candidate("Пустая-оболочка")],
            },
            "Пустая-оболочка",
        )

        project_world_model(wm, kw)

        record = json.loads((wm / "MYTHOLOGY.json").read_text(encoding="utf-8"))[0]
        assert record["description"] == ""
        assert "derived_from" not in record

    def test_verified_item_fills_shell_as_before(self, tmp_path: Path):
        wm, kw = self._workspace(
            tmp_path,
            {
                "_provenance_metadata": {"category": "DERIVED"},
                "items": [_verified("Пустая-оболочка")],
            },
            "Пустая-оболочка",
        )

        project_world_model(wm, kw)

        record = json.loads((wm / "MYTHOLOGY.json").read_text(encoding="utf-8"))[0]
        assert "Проверенный текст" in record["description"]
        assert record["derived_from"] == "SYMBOLS_DEEP.json#items[0]"

    def test_file_level_candidate_does_not_fill_shell(self, tmp_path: Path):
        wm, kw = self._workspace(
            tmp_path,
            {"_provenance_metadata": dict(_CANDIDATE_META), "items": [_verified("Пустая-оболочка")]},
            "Пустая-оболочка",
        )

        project_world_model(wm, kw)

        assert json.loads((wm / "MYTHOLOGY.json").read_text(encoding="utf-8"))[0]["description"] == ""

    def test_mirror_resolution_ignores_candidate(self, tmp_path: Path):
        _write(
            tmp_path / "SOURCE.json",
            {
                "_provenance_metadata": {"category": "DERIVED"},
                "items": [_candidate("Зеркало")],
            },
        )
        item = {"mirrors_from": "SOURCE.json#items[0]"}

        assert _resolve_blank_item_content(item, tmp_path, set()) == ""

    def test_items_by_topic_skips_candidate(self):
        source = {
            "_provenance_metadata": {"category": "DERIVED"},
            "items": [_candidate("Кандидат"), _verified("Проверено")],
        }

        index = _items_by_topic(source)

        assert "Кандидат" not in index
        assert "Проверено" in index

    def test_candidate_tradition_does_not_fill_religion(self, tmp_path: Path):
        wm = tmp_path / "WORLD_MODEL"
        kw = tmp_path / "KNOWLEDGE"
        wm.mkdir()
        kw.mkdir()
        _write(
            wm / "RELIGION.json",
            [
                {
                    "id": "ritual_кандидат",
                    "name": "Кандидат",
                    "description": "",
                    "provenance_category": "UNKNOWN",
                }
            ],
        )
        _write(wm / "RITUALS.json", [])
        _write(wm / "MYTHOLOGY.json", [])
        _write(
            kw / "ESOTERIC_CONNECTIONS.json",
            {
                "traditions": [
                    {
                        "name": "Кандидат",
                        "core_teaching": "Текст непроверенной традиции",
                        "_provenance_metadata": dict(_CANDIDATE_META),
                    }
                ]
            },
        )
        _write(kw / "SYMBOLS_DEEP.json", {"items": []})
        _write(kw / "COSMOLOGY.json", {"items": []})
        _write(kw / "RITUALS.json", {"items": []})

        project_world_model(wm, kw)

        record = json.loads((wm / "RELIGION.json").read_text(encoding="utf-8"))[0]
        assert record["description"] == ""
