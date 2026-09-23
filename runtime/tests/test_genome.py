"""Tests for Book Genome Extraction."""

import sys
from pathlib import Path

import pytest

# Add CORE to path for genome imports
_CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))

try:
    from genome.schema import BookGenome, WorldEntity, Archetype, Symbol
    HAS_GENOME_SCHEMA = True
except ImportError:
    HAS_GENOME_SCHEMA = False

try:
    from genome.loader import load_book_structure
    HAS_GENOME_LOADER = True
except ImportError:
    HAS_GENOME_LOADER = False


@pytest.mark.skipif(not HAS_GENOME_SCHEMA, reason="genome.schema module not found")
class TestGenomeSchemas:
    def test_book_genome_minimal(self):
        genome = BookGenome(
            themes=["духовное развитие"],
            core_values=["истина"],
            archetypes=[Archetype(name="Странник", role="поиск истины", characters=["Велик"])],
            symbols=[Symbol(name="Аркаим", meaning="место силы", chapters=[1])],
            conflicts=["Материя vs Дух"],
            mission_statement="Тест",
            world_entities=[WorldEntity(name="Гиперборея", type="civilization", description="тест")],
        )
        assert len(genome.themes) == 1


@pytest.mark.skipif(not HAS_GENOME_LOADER, reason="genome.loader module not found")
class TestBookLoader:
    def test_loads_book_structure(self):
        structure = load_book_structure()
        assert structure.title == "Наследие Аркаима"
        assert structure.author == "Автор: ОВладимирович"
        assert len(structure.chapters) > 0

    def test_chapters_have_content(self):
        structure = load_book_structure()
        for ch in structure.chapters[:5]:
            assert len(ch.paragraphs) > 0
            assert ch.number > 0

    def test_annotation_not_empty(self):
        structure = load_book_structure()
        assert len(structure.annotation) > 0
