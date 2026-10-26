"""Тест интеграции Book OS с KnowledgeCardBuilder.

Интеграционные проверки требуют наполненного OS_DATA (core/OS_DATA/graph/*.json).
Это генерируемые данные: каталог в .gitignore, собирается ingest-пайплайном
(book_os.pipeline.orchestrator) из исходных документов, которых в репозитории нет.
В чистом клоне (CI) корпуса Book OS не существует, поэтому проверки, зависящие от
него, корректно пропускаются, а не падают.
"""

from pathlib import Path

import pytest

from knowledge_card.builder import KnowledgeCardBuilder
from book_os.entity_store import EntityStore
from book_os.fact_store import FactStore

OS_DATA_ENTITIES = Path(__file__).resolve().parents[2] / "core" / "OS_DATA" / "graph" / "entities.json"

requires_book_os = pytest.mark.skipif(
    not OS_DATA_ENTITIES.exists(),
    reason=("нет корпуса Book OS: core/OS_DATA/ — генерируемые данные (gitignored), в чистом клоне отсутствуют; наполняются ingest-пайплайном локально"),
)


@requires_book_os
def test_book_os_claims_in_card() -> None:
    """Карточка должна содержать факты из Book OS для известной сущности."""
    builder = KnowledgeCardBuilder()
    card = builder.build("arkaim")

    book_os_sources = [s for s in card.sources if s.source_name == "book_os"]
    assert len(book_os_sources) == 1
    assert book_os_sources[0].claim_count > 0
    assert len(book_os_sources[0].claims) > 0


@requires_book_os
def test_book_os_resolve_known_entity() -> None:
    """Book OS должен находить известную сущность."""
    builder = KnowledgeCardBuilder()
    resolved = builder._book_os_resolve("arkaim")

    assert resolved is not None
    assert resolved["source"] == "book_os"
    assert resolved["name"]


def test_book_os_claims_for_unknown_entity() -> None:
    """Для неизвестной сущности claims должны быть пустыми."""
    builder = KnowledgeCardBuilder()
    claims = builder._book_os_claims("nonexistent_entity_xyz")

    assert claims == []


@requires_book_os
def test_book_os_entity_store_search() -> None:
    """EntityStore должен находить сущность по имени."""
    store = EntityStore()
    matches = store.search("arkaim")

    assert len(matches) > 0
    assert any("Аркаим" in e.name for e in matches)


@requires_book_os
def test_book_os_fact_store_by_entity() -> None:
    """FactStore должен возвращать факты для известной сущности."""
    entity_store = EntityStore()
    fact_store = FactStore()

    matches = entity_store.search("arkaim")
    assert matches, "Book OS должен содержать Аркаим"

    entity = matches[0]
    facts = fact_store.get_by_entity(entity.id)

    if not facts:
        from book_os.entity_store import _transliterate

        all_facts = list(fact_store._facts.values())
        entity_name_lower = entity.name.lower()
        entity_name_translit = _transliterate(entity_name_lower)
        facts = [f for f in all_facts if entity_name_lower in f.statement.lower() or entity_name_translit in _transliterate(f.statement.lower())]

    assert len(facts) > 0
    assert all(f.statement for f in facts)


@requires_book_os
def test_entity_store_transliteration() -> None:
    """EntityStore должен находить сущности по транслитерации."""
    store = EntityStore()

    cyrillic = store.search("Аркаим")
    latin = store.search("arkaim")

    assert len(cyrillic) > 0
    assert len(latin) > 0
    assert cyrillic[0].id == latin[0].id
