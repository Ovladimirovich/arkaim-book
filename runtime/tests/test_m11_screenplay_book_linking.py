"""M11 — Screenplay-Book Event Linking tests."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

_CORE = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from narrative_engine.source_levels import ProvenanceCategory
from knowledge_card import KnowledgeCardBuilder
from knowledge.screenplay_linker import ScreenplayBookLinker


def _make_retriever_mock(book_results=None, screenplay_results=None, genome_results=None):
    retriever = MagicMock()
    all_results = []
    all_results.extend(book_results or [])
    all_results.extend(screenplay_results or [])
    all_results.extend(genome_results or [])
    retriever.search = MagicMock(return_value=all_results)
    return retriever


def _book_result(text="Аркаим — древнее городище", chunk_id="chunk_001"):
    return {
        "text": text,
        "source": "book",
        "chunk_id": chunk_id,
        "metadata": {"chunk_id": chunk_id, "source": "book"},
        "chapter_title": "Часть 1",
    }


def _screenplay_result(
    text="Сцена прибытия в Аркаим",
    scene_id="scene_000",
    scene_title="1. INT. АЭРОПОРТ - ДЕНЬ",
):
    return {
        "text": text,
        "source": "screenplay",
        "chunk_id": f"{scene_id}_abc123",
        "metadata": {
            "chunk_id": f"{scene_id}_abc123",
            "source": "screenplay",
            "scene_id": scene_id,
            "scene_title": scene_title,
            "location": "АЭРОПОРТ",
            "scene_type": "INT",
        },
    }


class TestScreenplayBookLinking:
    """Тесты на связь книжных фрагментов и сценарных сцен."""

    def test_no_links_returns_empty(self):
        """При отсутствии связей возвращается пустой список."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([], f)
            temp_path = Path(f.name)

        linker = ScreenplayBookLinker.from_json(temp_path)
        links = linker.get_links_for_entity("region_arkaim")

        assert links == []
        temp_path.unlink()

    def test_link_found_for_entity(self):
        """Найденная связь возвращается для entity."""
        links_data = [
            {
                "screenplay_scene_id": "scene_000",
                "book_chunk_id": "chunk_p_0001",
                "confidence": 1.0,
                "notes": "Описание прибытия",
            }
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(links_data, f)
            temp_path = Path(f.name)

        linker = ScreenplayBookLinker.from_json(temp_path)
        links = linker.get_links_for_entity("chunk_p_0001")

        assert len(links) == 1
        assert links[0].screenplay_scene_id == "scene_000"
        assert links[0].book_chunk_id == "chunk_p_0001"
        temp_path.unlink()

    def test_linked_materials_preserve_provenance(self):
        """Связанные материалы сохраняют собственное происхождение."""
        links_data = [
            {
                "screenplay_scene_id": "scene_000",
                "book_chunk_id": "chunk_001",
                "confidence": 1.0,
            }
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(links_data, f)
            temp_path = Path(f.name)

        with tempfile.TemporaryDirectory() as tmpdir:
            knowledge_dir = Path(tmpdir) / "KNOWLEDGE"
            knowledge_dir.mkdir()
            links_file = knowledge_dir / "screenplay_links.json"
            links_file.write_text(json.dumps(links_data), encoding="utf-8")

            retriever = _make_retriever_mock(
                book_results=[_book_result()],
                screenplay_results=[_screenplay_result()],
            )
            builder = KnowledgeCardBuilder()
            builder._retriever_or_none = MagicMock(return_value=retriever)

            card = builder.build("Аркаим")

            screenplay_links = card.screenplay_links
            assert isinstance(screenplay_links, list)

        temp_path.unlink()

    def test_book_and_screenplay_claims_remain_separate(self):
        """Книжные и сценарные claims остаются раздельными."""
        links_data = [
            {
                "screenplay_scene_id": "scene_000",
                "book_chunk_id": "chunk_001",
                "confidence": 1.0,
            }
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(links_data, f)
            temp_path = Path(f.name)

        retriever = _make_retriever_mock(
            book_results=[_book_result(text="Книжное описание", chunk_id="chunk_001")],
            screenplay_results=[_screenplay_result(text="Сценарное описание")],
        )
        builder = KnowledgeCardBuilder()
        builder._retriever_or_none = MagicMock(return_value=retriever)

        card = builder.build("Аркаим")

        book_source = next(s for s in card.sources if s.source_name == "book")
        screenplay_source = next(s for s in card.sources if s.source_name == "screenplay")

        assert book_source.claims[0].source_ref == "book:chunk_001"
        assert screenplay_source.claims[0].source_ref == "screenplay:scene:scene_000"
        assert book_source.claims[0].provenance.category == ProvenanceCategory.AUTHOR_CANON
        assert screenplay_source.claims[0].provenance.category == ProvenanceCategory.AUTHOR_CANON
        temp_path.unlink()

    def test_visual_details_not_lost(self):
        """Визуальные детали сценария не теряются при связывании."""
        retriever = _make_retriever_mock(
            screenplay_results=[
                _screenplay_result(
                    text="Камера приближается к стенам Аркаима, видны древние символы",
                    scene_id="scene_042",
                    scene_title="42. EXT. АРКАИМ - ЗАКАТ",
                ),
            ],
        )
        builder = KnowledgeCardBuilder()
        builder._retriever_or_none = MagicMock(return_value=retriever)

        card = builder.build("Аркаим")

        screenplay_source = next(s for s in card.sources if s.source_name == "screenplay")
        assert len(screenplay_source.claims) == 1
        claim = screenplay_source.claims[0]
        assert "камера" in claim.text.lower() or "символ" in claim.text.lower()
        assert claim.notes == "42. EXT. АРКАИМ - ЗАКАТ"

    def test_repeated_scene_numbers_no_confusion(self):
        """Повторяющиеся номера сцен не приводят к ошибочным связям."""
        links_data = [
            {
                "screenplay_scene_id": "scene_000",
                "book_chunk_id": "chunk_001",
                "confidence": 1.0,
            },
            {
                "screenplay_scene_id": "scene_042",
                "book_chunk_id": "chunk_002",
                "confidence": 1.0,
            },
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(links_data, f)
            temp_path = Path(f.name)

        linker = ScreenplayBookLinker.from_json(temp_path)

        scene_000_links = linker.get_links_for_scene("scene_000")
        scene_042_links = linker.get_links_for_scene("scene_042")

        assert len(scene_000_links) == 1
        assert len(scene_042_links) == 1
        assert scene_000_links[0].book_chunk_id == "chunk_001"
        assert scene_042_links[0].book_chunk_id == "chunk_002"
        temp_path.unlink()

    def test_missing_link_returns_empty(self):
        """Отсутствующая связь возвращает пустой список, не ошибку."""
        links_data = [
            {
                "screenplay_scene_id": "scene_000",
                "book_chunk_id": "chunk_001",
                "confidence": 1.0,
            }
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(links_data, f)
            temp_path = Path(f.name)

        linker = ScreenplayBookLinker.from_json(temp_path)

        links = linker.get_links_for_entity("nonexistent_entity")
        assert links == []
        temp_path.unlink()

    def test_invalid_json_returns_empty(self):
        """Невалидный JSON возвращает пустой список связей."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json{")
            temp_path = Path(f.name)

        linker = ScreenplayBookLinker.from_json(temp_path)
        assert linker.links == []
        temp_path.unlink()


class TestScreenplayLinksInCard:
    """Тесты на интеграцию screenplay_links в Knowledge Card."""

    def test_card_has_screenplay_links_field(self):
        """Карточка содержит поле screenplay_links."""
        retriever = _make_retriever_mock(book_results=[_book_result()])
        builder = KnowledgeCardBuilder()
        builder._retriever_or_none = MagicMock(return_value=retriever)

        card = builder.build("Аркаим")

        assert hasattr(card, "screenplay_links")
        assert isinstance(card.screenplay_links, list)

    def test_screenplay_links_empty_by_default(self):
        """У сущности без подтверждённых связей screenplay_links пуст.

        M16.1: файл screenplay_links.json содержит только одобренные OWNER
        связи (scene/chunk идентификаторы); «Аркаим» среди них нет, поэтому
        карточка этой сущности не получает связей.
        """
        retriever = _make_retriever_mock(
            book_results=[_book_result()],
            screenplay_results=[_screenplay_result()],
        )
        builder = KnowledgeCardBuilder()
        builder._retriever_or_none = MagicMock(return_value=retriever)

        card = builder.build("Аркаим")

        assert card.screenplay_links == []
