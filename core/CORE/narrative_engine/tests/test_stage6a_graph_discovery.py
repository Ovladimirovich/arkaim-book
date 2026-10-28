"""Этап 6a: discovery на реальном графе без LLM.

Проверяется:
  - резолв имени в ``entity_id``: id / точное имя / алиас / уникальная часть;
  - дубликаты имён не привязываются к случайной сущности;
  - ``GraphLinker`` находит реальные рёбра и помечает их
    ``SYSTEM_INTERPRETATION`` + ``requires_author_review``;
  - ``WorldExplorer.find_new_connections`` ищет по резолву имени, а не по
    тексту, и находит связь, добавленную в граф.
"""

import sys
from pathlib import Path

CORE = Path(__file__).resolve().parents[4] / "core" / "CORE"
RUNTIME = Path(__file__).resolve().parents[4] / "runtime"
for path in (CORE, RUNTIME):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import asyncio

from book_os.entity_store import EntityStore
from book_os.fact_store import FactStore
from book_os.relationship_store import RelationshipStore
from knowledge_expansion.linkers.graph_linker import GraphLinker
from knowledge_expansion.models import EnrichedKnowledge
from knowledge_graph.graph_engine import GraphEngine
from narrative_engine.branch_manager import ScenarioStore
from narrative_engine.hypothesis_generator import (
    Hypothesis,
    HypothesisStore,
    HypothesisType,
)
from narrative_engine.world_explorer import WorldExplorer
from narrative_engine.world_model import WorldModel
from schemas.entity import Entity
from schemas.relationship import Relationship


def _stores(tmp_path):
    entities = EntityStore(data_dir=tmp_path / "os")
    relationships = RelationshipStore(data_dir=tmp_path / "os")
    facts = FactStore(data_dir=tmp_path / "os")
    engine = GraphEngine(entities, relationships, facts)
    return entities, relationships, engine


def _add(entities, entity_id, name, aliases=None):
    entities.add(
        Entity(
            id=entity_id,
            name=name,
            type="concept",
            aliases=aliases or [],
        )
    )


def _linked(entities, relationships, engine, source, target, rel_type):
    relationships.add(Relationship(source_id=source, target_id=target, type=rel_type))
    engine.build()


def _knowledge(topic, cross_references=None):
    return EnrichedKnowledge(
        source="unit-test",
        topic=topic,
        content="проверка discovery",
        cross_references=cross_references or [],
    )


# ── Резолв имени ─────────────────────────────────────────────


def test_resolve_by_id_name_and_alias(tmp_path):
    entities, _, engine = _stores(tmp_path)
    _add(entities, "e-ark", "Аркаим", aliases=["Город-храм"])

    assert engine.resolve_entity_id("e-ark") == "e-ark"
    assert engine.resolve_entity_id("Аркаим") == "e-ark"
    assert engine.resolve_entity_id("Город-храм") == "e-ark"
    assert engine.resolve_entity_ids("Аркаим") == ["e-ark"]


def test_duplicate_names_never_pick_one_random_entity(tmp_path):
    entities, _, engine = _stores(tmp_path)
    _add(entities, "e-1", "Аркаим")
    _add(entities, "e-2", "Аркаим")

    # Строгий резолв честно отказывается выбирать дубликат.
    assert engine.resolve_entity_id("Аркаим") is None
    # Множественный — видит оба узла (ни одного не теряет).
    assert sorted(engine.resolve_entity_ids("Аркаим")) == ["e-1", "e-2"]


def test_unique_partial_resolves_ambiguous_partial_does_not(tmp_path):
    entities, _, engine = _stores(tmp_path)
    _add(entities, "e-sin", "Синташта")
    _add(entities, "e-ark", "Аркаим")
    _add(entities, "e-ark2", "Аркаим")

    assert engine.resolve_entity_id("Синташт") == "e-sin"
    assert engine.resolve_entity_id("Арка") is None
    assert engine.resolve_entity_ids("Арка") == []
    assert engine.resolve_entity_ids("несуществующее") == []


# ── GraphLinker ──────────────────────────────────────────────


def test_graph_linker_finds_real_edge_and_marks_interpretation(tmp_path):
    entities, relationships, engine = _stores(tmp_path)
    _add(entities, "e-ark", "Аркаим")
    _add(entities, "e-sin", "Синташта")
    _linked(entities, relationships, engine, "e-ark", "e-sin", "located_in")

    [linked] = asyncio.run(GraphLinker(engine).link([_knowledge("Аркаим")]))

    graph_links = [link for link in linked.graph_links if link["depth"] > 0]
    assert len(graph_links) == 1
    link = graph_links[0]
    assert link["target_id"] == "e-sin"
    assert link["target"] == "Синташта"
    assert link["type"] == "located_in"
    assert link["source_id"] == "e-ark"
    assert link["source_ambiguous"] is False
    assert link["provenance_category"] == "SYSTEM_INTERPRETATION"
    assert link["source_level"] == "SYSTEM_INTERPRETATION"
    assert link["requires_author_review"] is True


def test_graph_linker_uses_all_duplicates_without_fake_link(tmp_path):
    entities, relationships, engine = _stores(tmp_path)
    _add(entities, "e-1", "Аркаим")
    _add(entities, "e-2", "Аркаим")
    _add(entities, "e-sin", "Синташта")
    _linked(entities, relationships, engine, "e-2", "e-sin", "located_in")

    [linked] = asyncio.run(GraphLinker(engine).link([_knowledge("Аркаим")]))

    graph_links = [link for link in linked.graph_links if link["depth"] > 0]
    assert [link["target_id"] for link in graph_links] == ["e-sin"]
    assert graph_links[0]["source_ambiguous"] is True

    # Тема без сущности: рёбер не выдумываем.
    [unknown] = asyncio.run(GraphLinker(engine).link([_knowledge("Нет такой")]))
    assert [link for link in unknown.graph_links if link["depth"] > 0] == []


def test_graph_linker_marks_cross_references(tmp_path):
    entities, _, engine = _stores(tmp_path)
    _add(entities, "e-ark", "Аркаим")
    _add(entities, "e-sin", "Синташта")

    [linked] = asyncio.run(
        GraphLinker(engine).link(
            [_knowledge("Аркаим", cross_references=["Синташта", "Неизвестное"])]
        )
    )

    refs = {link["target"]: link for link in linked.graph_links if link["depth"] == 0}
    assert refs["Синташта"]["target_id"] == "e-sin"
    assert refs["Неизвестное"]["target_id"] is None
    for link in refs.values():
        assert link["type"] == "cross_reference"
        assert link["provenance_category"] == "SYSTEM_INTERPRETATION"
        assert link["requires_author_review"] is True


# ── WorldExplorer ────────────────────────────────────────────


def _world_model():
    return WorldModel(
        {
            "epochs": [
                {"id": "past", "name": "Past", "name_ru": "Прошлое", "order": 1}
            ],
            "locations": [{"id": "loc_a", "name": "A", "name_ru": "А"}],
        }
    )


def _hypothesis(*, elements):
    return Hypothesis(
        id="hyp_0001",
        title="test",
        title_ru="Проверка",
        hypothesis_type=HypothesisType.PROACTIVE,
        required_elements=list(elements),
    )


def _explorer(tmp_path, engine):
    return WorldExplorer(
        _world_model(),
        graph_engine=engine,
        hypothesis_store=HypothesisStore(data_dir=tmp_path / "lifecycle"),
        scenario_store=ScenarioStore(data_dir=tmp_path / "lifecycle"),
    )


def test_explorer_discovers_edge_added_to_graph(tmp_path):
    entities, relationships, engine = _stores(tmp_path)
    _add(entities, "e-ark", "Аркаим")
    _add(entities, "e-sin", "Синташта")
    explorer = _explorer(tmp_path, engine)
    hypothesis = _hypothesis(elements=["Аркаим"])

    assert explorer.find_new_connections(hypothesis) == []

    _linked(entities, relationships, engine, "e-ark", "e-sin", "located_in")
    connections = explorer.find_new_connections(hypothesis)

    assert len(connections) == 1
    connection = connections[0]
    assert connection["source_id"] == "e-ark"
    assert connection["target_id"] == "e-sin"
    assert connection["type"] == "located_in"
    assert connection["source_ambiguous"] is False
    assert connection["provenance_category"] == "SYSTEM_INTERPRETATION"
    assert connection["source_level"] == "SYSTEM_INTERPRETATION"
    assert connection["requires_author_review"] is True


def test_explorer_resolves_name_instead_of_passing_it_as_id(tmp_path):
    entities, relationships, engine = _stores(tmp_path)
    _add(entities, "e-ark", "Аркаим")
    _add(entities, "e-sin", "Синташта")
    _linked(entities, relationships, engine, "e-ark", "e-sin", "located_in")
    explorer = _explorer(tmp_path, engine)

    calls = []
    original = engine.get_neighbors

    def spy(entity_id, *args, **kwargs):
        calls.append(entity_id)
        return original(entity_id, *args, **kwargs)

    engine.get_neighbors = spy
    explorer.find_new_connections(_hypothesis(elements=["Аркаим"]))

    assert calls == ["e-ark"]
