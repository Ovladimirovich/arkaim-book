# -*- coding: utf-8 -*-
"""M20.1 — пять одобренных OWNER связей сценарий↔книга.

Проверяет, что в core/KNOWLEDGE/screenplay_links.json ровно 15 одобренных
пар (M16.1 + M20.1 + M20.3), пять пар M20.1 разрешаются через
ScreenplayBookLinker, сцена scene_020 несёт две независимые связи, а
дословное совпадение текста подтверждается на уровне источников (сцена и
книжный фрагмент), а не ранжирования детектора.

Запреты OWNER соблюдены: claim-based неоднозначная пара scene_079 в реестр
не попала; scene_081 добавлена отдельным решением M20.3 (см.
test_m20_3_screenplay_links.py). Позиция детектора не проверялась и не
менялась.
"""

from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent
_CORE = _REPO / "core" / "CORE"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from intelligence.chunker import ScreenplayChunker  # noqa: E402
from knowledge.screenplay_linker import ScreenplayBookLinker  # noqa: E402
from knowledge.screenplay_links_provenance import (  # noqa: E402
    APPROVED_PAIRS,
    M16_1_APPROVED_PAIRS,
    M20_1_APPROVED_PAIRS,
    M20_3_APPROVED_PAIRS,
    SCREENPLAY_LINKS_PATH,
    validate_screenplay_links,
)

# Пять одобренных пар M20.1 (OWNER-GO). Same content as
# core/CORE/knowledge/screenplay_links_provenance.py::M20_1_APPROVED_PAIRS.
M20_1_PAIRS: set[tuple[str, str]] = {
    ("scene_004", "chunk_p_0007_b812dfae0ff4"),
    ("scene_009", "chunk_p_0018_89a09e6d3d55"),
    ("scene_020", "chunk_p_0045_bc4a72fed70b"),
    ("scene_086", "chunk_p_0570_e94101594d2f"),
    ("scene_117", "chunk_p_0799_57e67fec2309"),
}

# Полный ожидаемый набор: 9 пар M16.1 + 5 пар M20.1 + 1 пара M20.3 = 15.
EXPECTED_ALL_PAIRS: set[tuple[str, str]] = (
    {
        ("scene_003", "chunk_p_0006_104f39f72f26"),
        ("scene_006", "chunk_p_0010_77326a31efd2"),
        ("scene_014", "chunk_p_0027_4c6873e98b66"),
        ("scene_019", "chunk_p_0043_a5a83219bbd8"),
        ("scene_020", "chunk_p_0046_407df13f675f"),
        ("scene_021", "chunk_p_0047_387817db08e3"),
        ("scene_022", "chunk_p_0048_bbe88490fb62"),
        ("scene_027", "chunk_p_0049_9d39268ad94c"),
        ("scene_047", "chunk_p_0102_1d2e617e135e"),
    }
    | M20_1_PAIRS
    | set(M20_3_APPROVED_PAIRS)
)

# Дословные фрагменты, совпадающие в сцене и в книжном чанке (M20.1).
SHARED_QUOTES: dict[tuple[str, str], str] = {
    ("scene_004", "chunk_p_0007_b812dfae0ff4"): ("Настал момент, когда космические сроки и законы совпали и пришло время возникновения импульса"),
    ("scene_009", "chunk_p_0018_89a09e6d3d55"): ("Возникновение импульса было сигналом к переходу сознания в материю физического тела"),
    ("scene_020", "chunk_p_0045_bc4a72fed70b"): ("цивилизация Океании переживала упадок и закат своего существования"),
    ("scene_086", "chunk_p_0570_e94101594d2f"): ("Наступающая эпоха Кали Юги, время чрезвычайно жёсткое и суровое"),
    ("scene_117", "chunk_p_0799_57e67fec2309"): ("пробуждая тем самым сознание человечества в преданном служении общему благу"),
}

_ENRICHED_CATALOG = _REPO / "core" / "KNOWLEDGE" / "enriched_catalog.json"


@lru_cache(maxsize=1)
def _scene_chunks() -> tuple[dict, ...]:
    """Все сцены сценария: {scene_id, text, scene_title, ...} (кэш на модуль)."""
    return tuple(ScreenplayChunker().chunk_by_scene())


def _scene_text(scene_id: str) -> str:
    for chunk in _scene_chunks():
        if chunk["scene_id"] == scene_id:
            # Переводы строк внутри реплик не разрывают дословную цитату.
            return " ".join(chunk["text"].split())
    raise AssertionError(f"сцена {scene_id} не найдена в сценарии")


@lru_cache(maxsize=1)
def _catalog() -> tuple[dict, ...]:
    return tuple(json.loads(_ENRICHED_CATALOG.read_text(encoding="utf-8")))


def _book_text(chunk_id: str) -> str:
    for item in _catalog():
        if item.get("id") == chunk_id:
            return " ".join(item["text"].split())
    raise AssertionError(f"чанк {chunk_id} не найден в enriched_catalog.json")


def _linker() -> ScreenplayBookLinker:
    return ScreenplayBookLinker.from_json()


def _link_for(scene_id: str, chunk_id: str):
    matching = [link for link in _linker().get_links_for_scene(scene_id) if link.book_chunk_id == chunk_id]
    assert len(matching) == 1, f"{scene_id}→{chunk_id}: ожидалась ровно 1 связь"
    return matching[0]


# ── Реестр: ровно 14 одобренных пар ────────────────────────────────────


class TestRegistryState:
    def test_exactly_fifteen_unique_pairs(self):
        linker = _linker()
        actual = {(link.screenplay_scene_id, link.book_chunk_id) for link in linker.links}
        assert len(linker.links) == 15
        assert len(actual) == 15
        assert actual == EXPECTED_ALL_PAIRS

    def test_module_constants_match_registry(self):
        assert set(M20_1_APPROVED_PAIRS) == M20_1_PAIRS
        assert set(M16_1_APPROVED_PAIRS) | M20_1_PAIRS == EXPECTED_ALL_PAIRS - set(M20_3_APPROVED_PAIRS)
        assert set(M16_1_APPROVED_PAIRS) | set(M20_1_APPROVED_PAIRS) | set(M20_3_APPROVED_PAIRS) == EXPECTED_ALL_PAIRS
        assert set(APPROVED_PAIRS) == EXPECTED_ALL_PAIRS

    def test_persisted_file_passes_validation(self):
        data = json.loads(SCREENPLAY_LINKS_PATH.read_text(encoding="utf-8"))
        assert len(data) == 15
        assert validate_screenplay_links(data) == []


# ── Новые пары разрешаются линкером ────────────────────────────────────


class TestNewPairsResolve:
    def test_each_new_pair_resolves_via_linker(self):
        for scene_id, chunk_id in M20_1_PAIRS:
            link = _link_for(scene_id, chunk_id)
            assert link.confidence == 1.0
            assert link.notes, f"{scene_id}→{chunk_id}: обоснование отсутствует"
            assert isinstance(link.provenance, dict)
            assert link.provenance["category"] == "AUTHOR_CANON"
            assert link.provenance["evidence_ref"] == f"book:{chunk_id}"
            assert link.provenance["screenplay_ref"] == f"screenplay:scene:{scene_id}"
            # ссылка и в обратном направлении (chunk → scene)
            assert any(item.screenplay_scene_id == scene_id for item in _linker().get_links_for_chunk(chunk_id))

    def test_scene_020_has_two_independent_links(self):
        links = _linker().get_links_for_scene("scene_020")
        assert len(links) == 2
        assert {link.book_chunk_id for link in links} == {
            "chunk_p_0045_bc4a72fed70b",
            "chunk_p_0046_407df13f675f",
        }
        # Обе связи независимы: разные обоснования, обе непустые.
        notes = {link.notes for link in links}
        assert len(notes) == 2
        m16_link = next(link for link in links if link.book_chunk_id.startswith("chunk_p_0046"))
        m20_link = next(link for link in links if link.book_chunk_id.startswith("chunk_p_0045"))
        # Обоснование M16.1 не перезаписано добавлением пары M20.1.
        assert "(M16)" in m16_link.notes
        assert "(M20.1)" in m20_link.notes


# ── Дословное совпадение текста (источники, не детектор) ───────────────


class TestVerbatimTextMatch:
    def test_shared_fragments_present_in_both_sources(self):
        for (scene_id, chunk_id), quote in SHARED_QUOTES.items():
            assert quote in _scene_text(scene_id), f"цитата не найдена в сцене {scene_id}"
            assert quote in _book_text(chunk_id), f"цитата не найдена в чанке {chunk_id}"

    def test_scene_004_quote_is_partial_book_fragment(self):
        # Сценарий содержит только часть книжного фрагмента (обрыв многоточием):
        # книжное продолжение в сцене отсутствует.
        book_tail = "бывшего в системе причинно-следственных связей"
        assert book_tail in _book_text("chunk_p_0007_b812dfae0ff4")
        assert book_tail not in _scene_text("scene_004")

    def test_scene_020_opening_is_rephrased(self):
        # Начало фразы перефразировано; основная часть совпадает дословно.
        assert "В те времена цивилизация Океании" in _scene_text("scene_020")
        assert "Во времена Велика цивилизация Океании" in _book_text("chunk_p_0045_bc4a72fed70b")

    def test_scene_117_differs_only_in_punctuation(self):
        # Единственное различие — запятая после «энтузиазма» в сценарии.
        assert "энтузиазма, развивая" in _scene_text("scene_117")
        assert "энтузиазма развивая" in _book_text("chunk_p_0799_57e67fec2309")
        assert "энтузиазма, развивая" not in _book_text("chunk_p_0799_57e67fec2309")


# ── Обоснования (notes) ────────────────────────────────────────────────


class TestJustificationNotes:
    def test_new_notes_state_text_match_not_event_identity(self):
        for scene_id, chunk_id in M20_1_PAIRS:
            notes = _link_for(scene_id, chunk_id).notes
            assert "Дословная цитата" in notes, f"{scene_id}: нет маркера дословной цитаты"
            assert "не утверждение о полной идентичности" in notes, f"{scene_id}: нет оговорки о неидентичности событий"

    def test_scene_004_notes_describe_partial_quote(self):
        notes = _link_for("scene_004", "chunk_p_0007_b812dfae0ff4").notes
        assert "многоточием" in notes
        assert "только часть книжного фрагмента" in notes

    def test_scene_020_notes_describe_rephrase_and_second_link(self):
        notes = _link_for("scene_020", "chunk_p_0045_bc4a72fed70b").notes
        assert "перефразировано" in notes
        assert "chunk_p_0046_407df13f675f" in notes
        assert "обе связи независимы" in notes


# ── Запреты OWNER и стабильность идентификаторов ──────────────────────


class TestForbiddenAndStableIds:
    def test_ambiguous_claims_did_not_add_scenes(self):
        # Неоднозначная claim-based пара scene_079 OWNER не одобрил — в
        # реестре её быть не должно. scene_081 добавлена только M20.3.
        scenes = {link.screenplay_scene_id for link in _linker().links}
        assert "scene_079" not in scenes
        scene_081_links = _linker().get_links_for_scene("scene_081")
        assert [link.book_chunk_id for link in scene_081_links] == ["chunk_p_0529_abdcaff6f8bd"]

    def test_visible_numbers_do_not_resolve_as_ids(self):
        linker = _linker()
        assert linker.get_links_for_scene("9") == []
        assert linker.get_links_for_scene("scene_9") == []
        assert linker.get_links_for_scene("10") == []
        assert linker.get_links_for_scene("scene_009"), "стабильный id scene_009 должен разрешаться"

    def test_scene_id_is_parsing_index_not_visible_number(self):
        # scene_009 — индекс парсинга; видимый номер сцены в сценарии — «10.».
        scene_009 = next(chunk for chunk in _scene_chunks() if chunk["scene_id"] == "scene_009")
        assert scene_009["scene_title"].startswith("10.")


# ── Потребители: связи не потеряны ────────────────────────────────────


class TestConsumersKeepLinks:
    def test_card_builder_resolves_both_scene_020_chunks(self):
        from knowledge_card import KnowledgeCardBuilder

        links_0045 = KnowledgeCardBuilder._screenplay_links("chunk_p_0045_bc4a72fed70b")
        assert [item["screenplay_scene_id"] for item in links_0045] == ["scene_020"]

        links_0046 = KnowledgeCardBuilder._screenplay_links("chunk_p_0046_407df13f675f")
        assert [item["screenplay_scene_id"] for item in links_0046] == ["scene_020"]

    def test_all_new_chunk_ids_visible_to_card_builder(self):
        from knowledge_card import KnowledgeCardBuilder

        for _scene_id, chunk_id in M20_1_PAIRS:
            links = KnowledgeCardBuilder._screenplay_links(chunk_id)
            assert links, f"карточка не получила связей для {chunk_id}"
            assert links[0]["confidence"] == 1.0
