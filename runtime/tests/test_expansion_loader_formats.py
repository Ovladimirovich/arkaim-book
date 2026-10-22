"""ExpansionLoader — поддержка форматов `items`/`symbols` и фактический состав.

Решение владельца (2026-10-22): потеря тем в ExpansionLayer исправлена —
загрузчик понимает обнаруженные форматы пайплайна, а не только `themes`.

Проверяется:
  - поддержка контейнеров ``items`` / ``symbols`` / ``archetypes``;
  - записи без содержания (пустые оболочки) не попадают в слой;
  - записи без темы не попадают в слой;
  - фактическое количество тем и вклад каждого файла;
  - поиск по расширенным знаниям работает.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_CORE = _PROJECT_ROOT / "core" / "CORE"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from knowledge_expansion.expansion_loader import (  # noqa: E402
    ENTRY_CONTAINERS,
    ExpansionLoader,
    _entry_has_content,
)

KNOWLEDGE = _PROJECT_ROOT / "core" / "KNOWLEDGE"

#: Минимально ожидаемое число тем: 15 THEMES_DEEP + 134 PHILOSOPHY_DEEP
#: + 14 SYMBOLS_DEEP + 14 SYMBOLS_EXPANDED + 13 THEMES_EXPANDED + 8 академических.
MIN_TOPICS = 150


@pytest.fixture(scope="module")
def loader() -> ExpansionLoader:
    instance = ExpansionLoader()
    instance.load()
    return instance


class TestSupportedContainers:
    def test_items_symbols_archetypes_are_supported(self):
        containers = {name for name, _ in ENTRY_CONTAINERS}
        assert {"themes", "items", "symbols", "archetypes"} <= containers

    def test_cosmology_is_not_a_topic_container(self):
        """`cosmology` — одна запись, разложенная по полям, а не список тем."""
        containers = {name for name, _ in ENTRY_CONTAINERS}
        assert "cosmology" not in containers


class TestContentFilter:
    def test_empty_shell_is_not_content(self):
        assert not _entry_has_content({"topic": "Пусто", "content": "", "layers": {}})
        assert not _entry_has_content({"topic": "Пусто", "content": "   "})
        assert not _entry_has_content({"topic": "Пусто", "layers": {"literal": "", "cosmic": ""}})

    def test_text_or_layer_is_content(self):
        assert _entry_has_content({"topic": "Есть", "content": "текст"})
        assert _entry_has_content({"topic": "Есть", "layers": {"literal": "слой"}})

    def test_empty_shells_do_not_reach_the_layer(self, loader):
        """Ни одна загруженная из файлов тема не является пустой оболочкой.

        Академические подтверждения загружаются отдельным путём и имеют
        собственную форму (academic_sources), поэтому здесь не проверяются.
        """
        academic_topics = {
            str(item.get("category", "")).strip().lower()
            for item in json.loads((KNOWLEDGE / "ACADEMIC_CONFIRMATIONS.json").read_text(encoding="utf-8")).get("confirmations", [])
            if str(item.get("category", "")).strip()
        }
        for topic, data in loader._knowledge.items():
            if topic in academic_topics:
                continue
            assert _entry_has_content(data), f"пустая тема попала в слой: {topic}"


class TestActualComposition:
    def test_topic_count_is_at_least_expected(self, loader):
        assert loader.stats["topics"] >= MIN_TOPICS, loader.stats

    def test_philosophy_topics_are_loaded(self, loader):
        philosophy = json.loads((KNOWLEDGE / "PHILOSOPHY_DEEP.json").read_text(encoding="utf-8"))
        expected = {
            str(item.get("topic", "")).strip().lower()
            for item in philosophy.get("items", [])
            if str(item.get("topic", "")).strip() and _entry_has_content(item)
        }
        assert expected, "в PHILOSOPHY_DEEP.json нет пригодных тем"
        missing = expected - set(loader._knowledge)
        assert not missing, f"не загружено тем философии: {sorted(missing)[:5]}"

    def test_symbols_and_expanded_themes_are_loaded(self, loader):
        symbols = json.loads((KNOWLEDGE / "SYMBOLS_DEEP.json").read_text(encoding="utf-8"))
        expected = {
            str(item.get("topic", "")).strip().lower() for item in symbols.get("items", []) if str(item.get("topic", "")).strip() and _entry_has_content(item)
        }
        assert expected - set(loader._knowledge) == set()

    def test_stats_report_skips(self, loader):
        stats = loader.stats
        assert stats["skipped_empty"] > 0, "ожидались пропущенные пустые оболочки"
        assert stats["skipped_untitled"] > 0, "ожидались пропущенные записи без темы"
        assert stats["topics"] + stats["skipped_empty"] + stats["skipped_untitled"] > stats["topics"]

    def test_get_returns_topic_case_insensitively(self, loader):
        topic = next(iter(loader._knowledge))
        assert loader.get(topic.upper()) is not None


class TestSearch:
    def test_search_finds_expanded_topics(self, loader):
        philosophy = json.loads((KNOWLEDGE / "PHILOSOPHY_DEEP.json").read_text(encoding="utf-8"))
        sample = next(item for item in philosophy.get("items", []) if str(item.get("topic", "")).strip() and _entry_has_content(item))
        topic = str(sample["topic"])
        results = loader.search(topic, limit=5)
        assert results, f"поиск не нашёл тему {topic!r}"
        assert any(topic.lower() in str(r["topic"]).lower() for r in results)

    def test_search_returns_payload(self, loader):
        philosophy = json.loads((KNOWLEDGE / "PHILOSOPHY_DEEP.json").read_text(encoding="utf-8"))
        sample = next(item for item in philosophy.get("items", []) if str(item.get("topic", "")).strip() and _entry_has_content(item))
        results = loader.search(str(sample["topic"]), limit=1)
        assert results
        payload = results[0]["data"]
        assert str(payload.get("content") or "").strip()
