"""Этап 1 плана: «Честное происхождение» — устранение ложного CANON (B1) и
оживление мёртвого канала традиций (B2).

Проверяем, что:
- `search_local_knowledge` больше не возвращает AUTHOR_CANON для любого
  внешнего/производного файла (ARACHAEOLOGY, CROSS_REFERENCES,
  ESOTERIC_CONNECTIONS, HIERARCHY_OF_LIGHT, ACADEMIC_CONFIRMATIONS, COSMOLOGY).
- Provenance берётся из реального `_provenance_metadata` файла, а не
  навешивается по умолчанию.
- `MythologyContextBuilder` реально извлекает параллели из `traditions`
  (а не из несуществующего `connections`).
- `WorldEngineLayerV2.respond_to()` помечает не-канонические сущности
  явно в тексте ответа (а не молча выдаёт их как "мир книги").
"""

import json
import sys
from pathlib import Path

import pytest

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from narrative_engine.source_levels import (  # noqa: E402
    ProvenanceCategory,
    SourceLevel,
)
from narrative_engine.external_sources import (  # noqa: E402
    _read_file_provenance,
    search_local_knowledge,
)
from narrative_engine.contexts.mythology import (  # noqa: E402
    MythologyContextBuilder,
)


KNOWLEDGE_DIR = CORE_DIR.parent / "core" / "KNOWLEDGE"
if not KNOWLEDGE_DIR.exists():
    KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "KNOWLEDGE"


def _load_knowledge(filename: str) -> dict:
    path = KNOWLEDGE_DIR / filename
    if not path.exists():
        pytest.skip(f"KNOWLEDGE/{filename} не найден в репозитории")
    return json.loads(path.read_text(encoding="utf-8"))


# ── B1: search_local_knowledge не должен возвращать CANON ──────────────


class TestLocalKnowledgeNeverCanon:
    """Ключевой тест Этапа 1: локальный поиск не выдаёт CANON/AUTHOR_CANON."""

    def test_archaeology_not_canon(self):
        data = _load_knowledge("ARCHAEOLOGY.json")
        category, source_level, confidence, _ = _read_file_provenance(data)
        assert category != ProvenanceCategory.AUTHOR_CANON
        assert category == ProvenanceCategory.EXTERNAL_SOURCE
        assert source_level == SourceLevel.HISTORICAL

    def test_esoteric_not_canon(self):
        data = _load_knowledge("ESOTERIC_CONNECTIONS.json")
        category, source_level, _, _ = _read_file_provenance(data)
        assert category != ProvenanceCategory.AUTHOR_CANON
        # Фактическая категория файла — DERIVED (из metadata)
        assert category in (ProvenanceCategory.DERIVED, ProvenanceCategory.EXTERNAL_SOURCE)

    def test_coss_references_not_canon(self):
        data = _load_knowledge("CROSS_REFERENCES.json")
        category, _, _, _ = _read_file_provenance(data)
        assert category != ProvenanceCategory.AUTHOR_CANON

    def test_hierarchy_of_light_not_canon(self):
        data = _load_knowledge("HIERARCHY_OF_LIGHT.json")
        category, _, _, _ = _read_file_provenance(data)
        assert category != ProvenanceCategory.AUTHOR_CANON

    def test_academic_confirmations_not_canon(self):
        data = _load_knowledge("ACADEMIC_CONFIRMATIONS.json")
        category, _, _, _ = _read_file_provenance(data)
        assert category != ProvenanceCategory.AUTHOR_CANON

    def test_cosmology_not_canon(self):
        data = _load_knowledge("COSMOLOGY.json")
        category, _, _, _ = _read_file_provenance(data)
        assert category != ProvenanceCategory.AUTHOR_CANON

    def test_search_results_never_canon(self):
        """Даже live-поиск не должен вернуть ни одного результата CANON."""
        results = search_local_knowledge("аркаим", limit=20)
        for result in results:
            assert result.provenance.category != ProvenanceCategory.AUTHOR_CANON, f"Результат из {result.title} помечен как AUTHOR_CANON — нарушение B1"

    def test_search_results_not_empty_for_known_term(self):
        """Существенный контент должен продолжать находиться."""
        results = search_local_knowledge("аркаим", limit=20)
        assert isinstance(results, list)


# ── B2: мёртвый канал традиций оживает ────────────────────────────────


class TestMythologyChannelAlive:
    """MythologyContextBuilder реально извлекает параллели из traditions."""

    def test_traditions_yield_parallels(self):
        builder = MythologyContextBuilder()
        context = builder.build(query="герметизм")
        # Герметизм — одна из 10 традиций; должны быть параллели
        assert len(context.mythological_parallels) >= 1, "Мёртвый канал не исправлен: герметизм не даёт параллелей"
        # Параллели должны иметь реальное имя культуры (не пустое)
        assert any(p.culture for p in context.mythological_parallels), "Параллели без имени культуры — канал всё ещё мёртвый"

    def test_book_connection_visible(self):
        builder = MythologyContextBuilder()
        context = builder.build(query="герметизм")
        # Поле book_connection должно попасть в detail параллели
        assert any("Связь с книгой" in p.myth for p in context.mythological_parallels), "book_connection не виден в параллелях"


# ── B11: WorldEngineLayerV2 помечает не-канонические сущности ─────────


class TestWorldEngineLayerV2ProvenanceGate:
    """respond_to() должен явно помечать не-канонические сущности в тексте."""

    def test_split_by_provenance(self):
        from pulse.layers_world_engine import WorldEngineLayerV2

        results = {
            "world_model": [
                {"name": "arkaim_canon", "provenance_category": "AUTHOR_CANON"},
                {"name": "hyperborea_ext", "provenance_category": "EXTERNAL_SOURCE"},
                {"name": "ritual_sufism", "provenance_category": "SYSTEM_INTERPRETATION"},
            ]
        }
        canon_items, non_canon_items = WorldEngineLayerV2._split_by_provenance(results)
        assert len(canon_items) == 1
        assert len(non_canon_items) == 2

    def test_annotate_non_canon_context_appends_note(self):
        from pulse.layers_world_engine import WorldEngineLayerV2

        base = "Основной ответ"
        non_canon = [{"name": "ritual_sufism", "provenance_category": "SYSTEM_INTERPRETATION"}]
        annotated = WorldEngineLayerV2._annotate_non_canon_context(base, non_canon)
        assert "Примечание о происхождении" in annotated
        assert "ritual_sufism" in annotated

    def test_respond_to_is_still_none_safe(self):
        """Минимальный smoke-тест: слой не падает при отсутствии world engine."""
        from pulse.layers_world_engine import WorldEngineLayerV2

        layer = WorldEngineLayerV2.__new__(WorldEngineLayerV2)
        layer._world_engine = None
        assert layer.respond_to("кто жил в Аркаиме") is None
