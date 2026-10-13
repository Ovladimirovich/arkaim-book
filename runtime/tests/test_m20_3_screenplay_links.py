# -*- coding: utf-8 -*-
"""M20.3 — одна одобренная OWNER связь сценарий↔книга.

Проверяет, что в core/KNOWLEDGE/screenplay_links.json ровно 15 одобренных
пар (M16.1 + M20.1 + M20.3), новая пара scene_081 ↔ chunk_p_0529
разрешается через ScreenplayBookLinker, дословное ядро фразы совпадает в
источниках (сцена и книжный фрагмент), а книжный текст содержит
дополнительные уточнения и отличается по продолжению.

Запреты OWNER соблюдены: scene_079 ↔ chunk_p_0037, chunk_p_0008 и
chunk_p_0061 в реестр не попали; claim_temporal_links.json не изменён.
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
    RESOLVED_BY_M20_3,
    SCREENPLAY_LINKS_PATH,
    validate_screenplay_links,
)

# Одобренная пара M20.3 (OWNER-GO). Same content as
# core/CORE/knowledge/screenplay_links_provenance.py::M20_3_APPROVED_PAIRS.
M20_3_PAIRS: set[tuple[str, str]] = {
    ("scene_081", "chunk_p_0529_abdcaff6f8bd"),
}

# Полный ожидаемый набор: 9 пар M16.1 + 5 пар M20.1 + 1 пара M20.3 = 15.
EXPECTED_ALL_PAIRS: set[tuple[str, str]] = {
    ("scene_003", "chunk_p_0006_104f39f72f26"),
    ("scene_006", "chunk_p_0010_77326a31efd2"),
    ("scene_014", "chunk_p_0027_4c6873e98b66"),
    ("scene_019", "chunk_p_0043_a5a83219bbd8"),
    ("scene_020", "chunk_p_0046_407df13f675f"),
    ("scene_021", "chunk_p_0047_387817db08e3"),
    ("scene_022", "chunk_p_0048_bbe88490fb62"),
    ("scene_027", "chunk_p_0049_9d39268ad94c"),
    ("scene_047", "chunk_p_0102_1d2e617e135e"),
    ("scene_004", "chunk_p_0007_b812dfae0ff4"),
    ("scene_009", "chunk_p_0018_89a09e6d3d55"),
    ("scene_020", "chunk_p_0045_bc4a72fed70b"),
    ("scene_086", "chunk_p_0570_e94101594d2f"),
    ("scene_117", "chunk_p_0799_57e67fec2309"),
} | M20_3_PAIRS

# Дословное ядро фразы Учителя, совпадающее в сцене и в книжном чанке.
SHARED_CORE = "потребует от человечества полной самоотверженной самоотдачи"

_ENRICHED_CATALOG = _REPO / "core" / "KNOWLEDGE" / "enriched_catalog.json"
_CLAIM_TEMPORAL_LINKS = _REPO / "core" / "KNOWLEDGE" / "claim_temporal_links.json"


@lru_cache(maxsize=1)
def _scene_chunks() -> tuple[dict, ...]:
    return tuple(ScreenplayChunker().chunk_by_scene())


def _scene_text(scene_id: str) -> str:
    for chunk in _scene_chunks():
        if chunk["scene_id"] == scene_id:
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


# ── Реестр: ровно 15 одобренных пар ────────────────────────────────────


class TestRegistryState:
    def test_exactly_fifteen_unique_pairs(self):
        linker = _linker()
        actual = {(link.screenplay_scene_id, link.book_chunk_id) for link in linker.links}
        assert len(linker.links) == 15
        assert len(actual) == 15
        assert actual == EXPECTED_ALL_PAIRS

    def test_module_constants_match_registry(self):
        assert set(M20_3_APPROVED_PAIRS) == M20_3_PAIRS
        assert set(M16_1_APPROVED_PAIRS) | set(M20_1_APPROVED_PAIRS) | M20_3_PAIRS == EXPECTED_ALL_PAIRS
        assert set(APPROVED_PAIRS) == EXPECTED_ALL_PAIRS

    def test_persisted_file_passes_validation(self):
        data = json.loads(SCREENPLAY_LINKS_PATH.read_text(encoding="utf-8"))
        assert len(data) == 15
        assert validate_screenplay_links(data) == []


# ── Новая пара разрешается линкером ────────────────────────────────────


class TestNewPairResolves:
    def test_scene_081_pair_resolves_via_linker(self):
        for scene_id, chunk_id in M20_3_PAIRS:
            link = _link_for(scene_id, chunk_id)
            assert link.confidence == 1.0
            assert link.notes, f"{scene_id}→{chunk_id}: обоснование отсутствует"
            assert isinstance(link.provenance, dict)
            assert link.provenance["category"] == "AUTHOR_CANON"
            assert link.provenance["evidence_ref"] == f"book:{chunk_id}"
            assert link.provenance["screenplay_ref"] == f"screenplay:scene:{scene_id}"
            assert link.provenance["resolved_by"] == RESOLVED_BY_M20_3
            assert any(item.screenplay_scene_id == scene_id for item in _linker().get_links_for_chunk(chunk_id))

    def test_scene_081_has_exactly_one_link(self):
        links = _linker().get_links_for_scene("scene_081")
        assert len(links) == 1
        assert links[0].book_chunk_id == "chunk_p_0529_abdcaff6f8bd"


# ── Дословное ядро фразы (источники, не детектор) ──────────────────────


class TestVerbatimCoreMatch:
    def test_shared_core_present_in_both_sources(self):
        assert SHARED_CORE in _scene_text("scene_081")
        assert SHARED_CORE in _book_text("chunk_p_0529_abdcaff6f8bd")

    def test_scene_081_starts_with_clean_core(self):
        # Сцена: «Наступление эпохи Кали Юги потребует…» — без вставок.
        assert "Наступление эпохи Кали Юги потребует от человечества полной самоотверженной самоотдачи" in _scene_text("scene_081")

    def test_book_contains_insertions_absent_from_scene(self):
        # Книга расширяет фразу вставками, которых нет в сцене.
        book = _book_text("chunk_p_0529_abdcaff6f8bd")
        assert "Наступление нынешней эпохи Кали Юги, когда приходит время темных сил на всей Земле, потребует" in book
        assert "нынешней" not in _scene_text("scene_081")
        assert "темных сил" not in _scene_text("scene_081")

    def test_book_and_scene_differ_in_continuation(self):
        # Книжное продолжение отсутствует в сцене (сцена обрывается иначе).
        assert "во всеоружии" in _book_text("chunk_p_0529_abdcaff6f8bd")
        assert "во всеоружии" not in _scene_text("scene_081")


# ── Обоснование (notes) ────────────────────────────────────────────────


class TestJustificationNotes:
    def test_notes_state_text_match_not_event_identity(self):
        for scene_id, chunk_id in M20_3_PAIRS:
            notes = _link_for(scene_id, chunk_id).notes
            assert "Дословная цитата" in notes
            assert "не утверждение о полной идентичности" in notes

    def test_notes_describe_insertions_and_continuation(self):
        notes = _link_for("scene_081", "chunk_p_0529_abdcaff6f8bd").notes
        assert "дополнительные уточнения" in notes
        assert "отличается по продолжению" in notes
        assert "claim_8ebb1ec3ae30" in notes
        assert "event_kali_yuga_onset" in notes


# ── Запреты OWNER и неизменность claim-цепочки ─────────────────────────


class TestForbiddenAndStableState:
    def test_forbidden_pairs_absent(self):
        actual = {(link.screenplay_scene_id, link.book_chunk_id) for link in _linker().links}
        assert ("scene_079", "chunk_p_0037_c691e48e3362") not in actual
        assert ("scene_081", "chunk_p_0037_c691e48e3362") not in actual
        assert not any(chunk.startswith("chunk_p_0008") for _, chunk in actual)
        assert not any(chunk.startswith("chunk_p_0061") for _, chunk in actual)

    def test_claim_temporal_links_untouched(self):
        temporal = json.loads(_CLAIM_TEMPORAL_LINKS.read_text(encoding="utf-8"))
        assert len(temporal) == 9
        kali = [link for link in temporal if link.get("claim_id") == "claim_8ebb1ec3ae30"]
        assert len(kali) == 1
        assert kali[0]["event_id"] == "event_kali_yuga_onset"


# ── Потребители: связь видна в Knowledge Card ──────────────────────────


class TestConsumersSeeLink:
    def test_card_builder_resolves_scene_081_chunk(self):
        from knowledge_card import KnowledgeCardBuilder

        links = KnowledgeCardBuilder._screenplay_links("chunk_p_0529_abdcaff6f8bd")
        assert [item["screenplay_scene_id"] for item in links] == ["scene_081"]
        assert links[0]["confidence"] == 1.0
