"""Этап 6d: непроверенные LLM-кандидаты не попадают в RAG/карточки.

Проверяется реальный путь чтения знаний:
  KNOWLEDGE-файл → ExpansionLoader / KnowledgeCardBuilder / Pulse fallback
  → записи с ``requires_author_review`` отсечены, проверенные читаются.

Гейт не должен менять поведение на существующих данных: проверенных записей
без полей провенанса в проекте большинство.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_CORE = _PROJECT_ROOT / "core" / "CORE"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from knowledge_card.builder import KnowledgeCardBuilder  # noqa: E402
from knowledge_expansion.expansion_loader import ExpansionLoader  # noqa: E402
from knowledge_expansion.provenance_gate import (  # noqa: E402
    file_is_unverified,
    item_is_unverified,
    record_is_unverified,
)

_CANDIDATE_META = {
    "category": "DERIVED",
    "provenance_category": "SYSTEM_INTERPRETATION",
    "source_level": "SYSTEM_INTERPRETATION",
    "source": "LLM",
    "requires_author_review": True,
    "status": "PENDING_REVIEW",
}


def _candidate(topic: str = "LLM-кандидат") -> dict:
    return {
        "topic": topic,
        "content": "Сгенерированный текст",
        "metadata": {"_provenance_metadata": dict(_CANDIDATE_META)},
        "_provenance_metadata": dict(_CANDIDATE_META),
    }


def _verified(topic: str = "Проверенная тема") -> dict:
    return {"topic": topic, "content": "Текст книги"}


def _write(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class TestGatePredicate:
    def test_plain_record_is_allowed(self):
        assert not record_is_unverified(_verified())

    def test_record_level_flag_blocks(self):
        assert record_is_unverified(_candidate())

    def test_nested_metadata_flag_blocks(self):
        record = {
            "topic": "Вложенная",
            "content": "текст",
            "metadata": {"_provenance_metadata": dict(_CANDIDATE_META)},
        }
        assert record_is_unverified(record)

    def test_pending_status_without_flag_blocks(self):
        record = {
            "topic": "Статус",
            "content": "текст",
            "_provenance_metadata": {"status": "PENDING_REVIEW"},
        }
        assert record_is_unverified(record)

    def test_approved_status_wins_over_stale_flag(self):
        record = {
            "topic": "Одобрено",
            "content": "текст",
            "_provenance_metadata": {
                "status": "APPROVED",
                "requires_author_review": True,
            },
        }
        assert not record_is_unverified(record)

    def test_string_flag_is_recognized(self):
        record = {
            "topic": "Строковый флаг",
            "content": "текст",
            "_provenance_metadata": {"requires_author_review": "true"},
        }
        assert record_is_unverified(record)

    def test_file_level_flag_blocks_document(self):
        document = {"_provenance_metadata": dict(_CANDIDATE_META), "items": []}
        assert file_is_unverified(document)
        assert item_is_unverified(_verified(), document)


class TestExpansionLoaderGate:
    def test_candidate_is_not_loaded(self, tmp_path: Path):
        _write(
            tmp_path / "THEMES_DEEP.json",
            {
                "_provenance_metadata": {"category": "DERIVED"},
                "items": [_verified(), _candidate(), _verified("Вторая тема")],
            },
        )

        loader = ExpansionLoader(knowledge_dir=tmp_path)
        loader.load()

        assert set(loader._knowledge) == {"проверенная тема", "вторая тема"}
        assert loader.stats["skipped_unverified"] == 1
        assert loader.get("LLM-кандидат") is None
        assert loader.search("LLM-кандидат") == []

    def test_pending_status_is_not_loaded(self, tmp_path: Path):
        item = _verified("Статусная тема")
        item["_provenance_metadata"] = {"status": "PENDING_REVIEW"}
        _write(tmp_path / "THEMES_EXPANDED.json", {"themes": [item]})

        loader = ExpansionLoader(knowledge_dir=tmp_path)
        loader.load()

        assert loader._knowledge == {}
        assert loader.stats["skipped_unverified"] == 1

    def test_file_level_candidate_blocks_whole_file(self, tmp_path: Path):
        _write(
            tmp_path / "SYMBOLS_DEEP.json",
            {
                "_provenance_metadata": dict(_CANDIDATE_META),
                "items": [_verified("Символ"), _verified("Второй символ")],
            },
        )

        loader = ExpansionLoader(knowledge_dir=tmp_path)
        loader.load()

        assert loader._knowledge == {}
        assert loader.stats["skipped_unverified"] == 2

    def test_approved_candidate_is_loaded(self, tmp_path: Path):
        item = _verified("Одобренная тема")
        item["_provenance_metadata"] = {
            "requires_author_review": True,
            "status": "APPROVED",
        }
        _write(tmp_path / "THEMES_DEEP.json", {"items": [item]})

        loader = ExpansionLoader(knowledge_dir=tmp_path)
        loader.load()

        assert set(loader._knowledge) == {"одобренная тема"}
        assert loader.stats["skipped_unverified"] == 0

    def test_academic_candidate_is_not_loaded(self, tmp_path: Path):
        _write(
            tmp_path / "ACADEMIC_CONFIRMATIONS.json",
            {
                "confirmations": [
                    {"category": "Археология", "book_theme": "Аркаим"},
                    {
                        "category": "Кандидат",
                        "book_theme": "Гипотеза",
                        "_provenance_metadata": dict(_CANDIDATE_META),
                    },
                ]
            },
        )

        loader = ExpansionLoader(knowledge_dir=tmp_path)
        loader.load()

        assert set(loader._knowledge) == {"археология"}
        assert loader.stats["skipped_unverified"] == 1

    def test_real_knowledge_dir_has_no_unverified_candidates(self):
        """Сегодня в KNOWLEDGE нет непроверенных записей — гейт ничего не теряет."""
        loader = ExpansionLoader()
        loader.load()

        assert loader.stats["topics"] >= 150, loader.stats
        assert loader.stats["skipped_unverified"] == 0, loader.stats


class TestKnowledgeCardGate:
    def test_candidate_is_not_iterated(self):
        data = {"references": [_verified("Обычная"), _candidate(), _verified("Вторая")]}

        items = list(KnowledgeCardBuilder._iter_list(data, "references"))

        assert [item.get("topic") for item in items] == ["Обычная", "Вторая"]

    def test_file_level_candidate_is_not_iterated(self):
        data = {
            "_provenance_metadata": dict(_CANDIDATE_META),
            "items": [_verified("Обычная")],
        }

        assert list(KnowledgeCardBuilder._iter_list(data, "items")) == []

    def test_bare_list_candidate_is_not_iterated(self):
        assert list(KnowledgeCardBuilder._iter_list([_candidate(), _verified()])) == [_verified()]


class TestPulseFallbackGate:
    def _layer(self):
        from pulse.layers import ExpansionLayer

        layer = object.__new__(ExpansionLayer)
        layer._knowledge = {}
        return layer

    def test_fallback_file_skips_candidate(self, tmp_path: Path):
        path = tmp_path / "THEMES_DEEP.json"
        _write(path, {"themes": [_verified(), _candidate()]})
        layer = self._layer()

        layer._load_file(path)

        assert set(layer._knowledge) == {"проверенная тема"}

    def test_fallback_academic_skips_candidate(self, tmp_path: Path):
        path = tmp_path / "ACADEMIC_CONFIRMATIONS.json"
        _write(
            path,
            {
                "confirmations": [
                    {"category": "Археология"},
                    {
                        "category": "Кандидат",
                        "_provenance_metadata": dict(_CANDIDATE_META),
                    },
                ]
            },
        )
        layer = self._layer()

        layer._load_academic(path)

        assert set(layer._knowledge) == {"археология"}


class TestApiLoader:
    def test_cached_expansion_loader_initializes(self):
        """Регресс: импорт KNOWLEDGE_DIR из store падал и отключал поиск."""
        from core.routes.book import _get_expansion_loader, reset_expansion_loader_cache

        reset_expansion_loader_cache()
        try:
            loader = _get_expansion_loader()
        finally:
            reset_expansion_loader_cache()

        assert loader is not None
        assert loader.stats["topics"] >= 150
        assert loader.stats["skipped_unverified"] == 0
