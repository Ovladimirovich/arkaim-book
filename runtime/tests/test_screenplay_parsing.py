"""Тесты парсинга киносценария «Наследие Аркаима» на сцены.

Проверяют, что API-парсер (runtime/core/routes/book.py) и парсер индексации
(core/CORE/intelligence/chunker.py, ScreenplayChunker) одинаково распознают
заголовки сцен во всех встречающихся форматах исходника и не сливают сцены.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from intelligence.chunker import ScreenplayChunker  # noqa: E402

from core.routes.book import (  # noqa: E402
    _extract_screenplay_location,
    _is_screenplay_scene_header,
    _parse_screenplay_scenes,
)

_CORE = Path(__file__).resolve().parent.parent.parent / "core"
SCREENPLAY_PATH = _CORE / "SOURCE_OF_TRUTH" / "SYNOPSIS" / "Наследие_Аркаима_Сценарий_Full.md"

# Фактический контрольный подсчёт по текущему исходнику — 119 элементов:
#   118 нумерованных заголовков (115 обычных сцен + 3 монтажных блока 42/47/48)
#   + 1 финальная сцена без номера («INT. ПОЕЗД - ПЛАЦКАРТ - ДЕНЬ»).
#
# Ожидание из OWNER-GO — 117 (113 обычных + 3 монтажных + 1 финальная).
# Расхождение ровно +2 и объясняется конкретными заголовками исходника:
#   1) Номера сцен идут 1..113, пропусков нет, но ПЯТЬ номеров повторяются —
#      60, 79, 80, 86, 93. Каждое повторение начинает новую сцену с другой
#      локацией/временем (см. test_duplicate_numbers_detail), поэтому это
#      отдельные элементы, а не одно «число сцен» = 113.
#   2) Монтажные блоки 42/47/48 уже НУМЕРОВАНЫ и входят в диапазон 1..113,
#      поэтому отдельно к 113 они не прибавляются.
# Итого: 113 уникальных номеров + 5 повторов = 118 нумерованных,
# из них обычных 115 и монтажных 3; + финальная = 119.
EXPECTED_TOTAL = 119
EXPECTED_MONTAGE = 3
EXPECTED_FINAL = 1
EXPECTED_ORDINARY = EXPECTED_TOTAL - EXPECTED_MONTAGE - EXPECTED_FINAL  # 115

# Повторяющиеся номера сцен в исходнике: номер -> число вхождений.
DUPLICATE_SCENE_NUMBERS = {60: 2, 79: 2, 80: 2, 86: 2, 93: 2}

# Синтетический фрагмент, покрывающий все форматы заголовков.
SAMPLE = "\n".join(
    [
        "TITLE: Тестовый сценарий",
        "1. EXT. НАЧАЛО - ДЕНЬ",
        "Текст сцены один.",
        "13.EXT. БЕЗ ПРОБЕЛА - ДЕНЬ",
        "Текст сцены тринадцать.",
        " 21. EXT. С ОТСТУПОМ - ДЕНЬ",
        "Текст сцены двадцать один.",
        "20 EXT. НОМЕР БЕЗ ТОЧКИ - ДЕНЬ",
        "Текст сцены двадцать.",
        "78.ВНУТРЕННИЙ ЗАЛ",
        "Текст сцены семьдесят восемь.",
        "42. МОНТАЖ - ОБУЧЕНИЕ",
        "Текст монтажа сорок два.",
        "47. MONTAGE - ЭПИЗОДЫ",
        "Текст монтажа сорок семь.",
        "60.INT. ДУБЛЬ - ВЕЧЕР",
        "Первый текст шестьдесят.",
        "60.INT. ДУБЛЬ - УТРО",
        "Второй текст шестьдесят.",
        "88.",
        "EXT.ДОЛИНА.ПРИГОРОК.",
        "Текст сцены восемьдесят восемь.",
        "INT. ПОЕЗД - ПЛАЦКАРТ - ДЕНЬ",
        "Текст финальной сцены.",
    ]
)

SAMPLE_TITLES = [
    "1. EXT. НАЧАЛО - ДЕНЬ",
    "13.EXT. БЕЗ ПРОБЕЛА - ДЕНЬ",
    "21. EXT. С ОТСТУПОМ - ДЕНЬ",
    "20 EXT. НОМЕР БЕЗ ТОЧКИ - ДЕНЬ",
    "78.ВНУТРЕННИЙ ЗАЛ",
    "42. МОНТАЖ - ОБУЧЕНИЕ",
    "47. MONTAGE - ЭПИЗОДЫ",
    "60.INT. ДУБЛЬ - ВЕЧЕР",
    "60.INT. ДУБЛЬ - УТРО",
    "88. EXT.ДОЛИНА.ПРИГОРОК.",
    "INT. ПОЕЗД - ПЛАЦКАРТ - ДЕНЬ",
]


def _real_scenes():
    text = SCREENPLAY_PATH.read_text(encoding="utf-8")
    return _parse_screenplay_scenes(text)


# ── Синтетический фрагмент: все форматы заголовков ─────────────


class TestHeaderFormats:
    def test_all_formats_parsed(self):
        scenes = _parse_screenplay_scenes(SAMPLE)
        assert [s["title"] for s in scenes] == SAMPLE_TITLES

    def test_header_without_space_after_dot(self):
        assert _is_screenplay_scene_header("13.EXT. БЕЗ ПРОБЕЛА - ДЕНЬ")

    def test_header_with_leading_indent(self):
        assert _is_screenplay_scene_header("21. EXT. С ОТСТУПОМ - ДЕНЬ")

    def test_header_without_dot_after_number(self):
        assert _is_screenplay_scene_header("20 EXT. НОМЕР БЕЗ ТОЧКИ - ДЕНЬ")

    def test_russian_marker(self):
        assert _is_screenplay_scene_header("78.ВНУТРЕННИЙ ЗАЛ")
        assert _is_screenplay_scene_header("95.ИНТ. ДОМ - ДЕНЬ")
        assert _is_screenplay_scene_header("96. ЭКСТ. ГОРОДОК - ДЕНЬ")

    def test_montage_markers(self):
        assert _is_screenplay_scene_header("42. МОНТАЖ - ОБУЧЕНИЕ")
        assert _is_screenplay_scene_header("47. MONTAGE - ЭПИЗОДЫ")

    def test_plain_remark_is_not_a_scene(self):
        # Ремарка, начинающаяся с EXT., сценой не является (локация не в верхнем регистре).
        assert not _is_screenplay_scene_header("EXT. Заснеженные горы, ледники.")

    def test_split_header_merged(self):
        scenes = _parse_screenplay_scenes(SAMPLE)
        titles = [s["title"] for s in scenes]
        assert "88. EXT.ДОЛИНА.ПРИГОРОК." in titles


class TestNoMerging:
    def test_no_scene_contains_another_header(self):
        for scene in _parse_screenplay_scenes(SAMPLE):
            for line in scene["content"].split("\n"):
                assert not _is_screenplay_scene_header(line.strip()), f"Сцена '{scene['title']}' вобрала заголовок: {line.strip()!r}"

    def test_duplicate_numbers_preserved_as_separate(self):
        scenes = _parse_screenplay_scenes(SAMPLE)
        sixties = [s for s in scenes if s["title"].startswith("60.")]
        assert len(sixties) == 2
        assert sixties[0]["content"] != sixties[1]["content"]

    def test_text_not_lost(self):
        # Каждая содержательная строка синтетики попадает в какую-то сцену.
        scenes = _parse_screenplay_scenes(SAMPLE)
        joined = "\n".join(s["content"] for s in scenes)
        for marker in [
            "Текст сцены один.",
            "Текст сцены тринадцать.",
            "Текст сцены двадцать один.",
            "Текст сцены двадцать.",
            "Текст сцены семьдесят восемь.",
            "Текст монтажа сорок два.",
            "Текст монтажа сорок семь.",
            "Первый текст шестьдесят.",
            "Второй текст шестьдесят.",
            "Текст сцены восемьдесят восемь.",
            "Текст финальной сцены.",
        ]:
            assert marker in joined


class TestLocationExtraction:
    def test_latin_with_number(self):
        assert _extract_screenplay_location("113.EXT. ОКЕАН - ДЕНЬ") == "ОКЕАН - ДЕНЬ"

    def test_russian_marker(self):
        assert _extract_screenplay_location("78.ВНУТРЕННИЙ  ЗАЛ") == "ЗАЛ"

    def test_number_without_dot(self):
        assert _extract_screenplay_location("20 EXT. ОСТРОВА АТЛАНТИДЫ - ДЕНЬ") == "ОСТРОВА АТЛАНТИДЫ - ДЕНЬ"

    def test_final_scene_without_number(self):
        assert _extract_screenplay_location("INT. ПОЕЗД - ПЛАЦКАРТ - ДЕНЬ") == "ПОЕЗД - ПЛАЦКАРТ - ДЕНЬ"

    def test_montage(self):
        assert _extract_screenplay_location("47. MONTAGE - ЭПИЗОДЫ") == "- ЭПИЗОДЫ"


# ── Реальный исходник ───────────────────────────────────────────


class TestRealScreenplay:
    def test_total_scene_count(self):
        assert len(_real_scenes()) == EXPECTED_TOTAL

    def test_scenes_107_to_113_separate(self):
        titles = [s["title"] for s in _real_scenes()]
        for n in range(107, 114):
            matches = [t for t in titles if t.strip().startswith(f"{n}.") or t.strip().startswith(f"{n} ")]
            assert matches, f"Сцена {n} не найдена отдельным элементом"

    def test_final_scene_separate(self):
        titles = [s["title"] for s in _real_scenes()]
        finals = [t for t in titles if "ПОЕЗД" in t]
        assert finals == ["INT. ПОЕЗД - ПЛАЦКАРТ - ДЕНЬ"]

    def test_montage_blocks_present(self):
        titles = [s["title"] for s in _real_scenes()]
        assert any("МОНТАЖ" in t.upper() for t in titles)
        assert any("MONTAGE" in t.upper() for t in titles)

    def test_duplicate_numbers_not_collapsed(self):
        titles = [s["title"] for s in _real_scenes()]
        sixties = [t for t in titles if t.strip().startswith("60.")]
        assert len(sixties) == 2

    def test_no_merging_in_real_source(self):
        for scene in _real_scenes():
            for line in scene["content"].split("\n"):
                assert not _is_screenplay_scene_header(line.strip()), f"Сцена '{scene['title']}' вобрала заголовок: {line.strip()!r}"

    def test_duplicate_numbers_detail(self):
        """Все пять повторяющихся номеров дают отдельные сцены с разным содержанием."""
        scenes = _real_scenes()
        for number, expected in DUPLICATE_SCENE_NUMBERS.items():
            group = [s for s in scenes if s["title"].strip().startswith(f"{number}.")]
            assert len(group) == expected, f"Номер {number}: ожидалось {expected} сцены, найдено {len(group)}"
            contents = {s["content"] for s in group}
            assert len(contents) == expected, f"Номер {number}: содержимое сцен совпадает"

    def test_scene_order_follows_source(self):
        """Сцены идут в порядке следования в исходном тексте, без потерь и слияний."""
        source = SCREENPLAY_PATH.read_text(encoding="utf-8")
        cursor = 0
        for scene in _real_scenes():
            pos = source.find(scene["content"], cursor)
            assert pos >= 0, f"Сцена '{scene['title']}' не найдена в исходнике после позиции {cursor}"
            cursor = pos + len(scene["content"])

    def test_scene_boundaries_do_not_overlap(self):
        source = SCREENPLAY_PATH.read_text(encoding="utf-8")
        spans = []
        for scene in _real_scenes():
            start = source.find(scene["content"])
            assert start >= 0
            spans.append((start, start + len(scene["content"])))
        for (a_start, a_end), (b_start, _b_end) in zip(spans, spans[1:]):
            assert a_start < b_start, f"Сцены идут не по порядку: {a_start} >= {b_start}"
            assert a_end <= b_start, f"Границы сцен пересекаются: {a_end} > {b_start}"

    def test_counts_by_type(self):
        types = [s["type"] for s in ScreenplayChunker(screenplay_path=SCREENPLAY_PATH)._scenes]
        assert types.count("MONTAGE") == EXPECTED_MONTAGE
        assert len(types) - types.count("MONTAGE") == EXPECTED_ORDINARY + EXPECTED_FINAL


# ── Согласованность API-парсера и ScreenplayChunker ─────────────


class TestParityWithChunker:
    def test_same_scene_count(self):
        api = _parse_screenplay_scenes(SCREENPLAY_PATH.read_text(encoding="utf-8"))
        chunker = ScreenplayChunker(screenplay_path=SCREENPLAY_PATH)
        assert len(api) == len(chunker._scenes) == EXPECTED_TOTAL

    def test_same_titles_and_content(self):
        api = _parse_screenplay_scenes(SCREENPLAY_PATH.read_text(encoding="utf-8"))
        chunker = ScreenplayChunker(screenplay_path=SCREENPLAY_PATH)
        assert [s["title"] for s in api] == [s["title"] for s in chunker._scenes]
        assert [s["content"] for s in api] == [s["content"] for s in chunker._scenes]

    def test_chunk_by_scene_matches(self):
        chunker = ScreenplayChunker(screenplay_path=SCREENPLAY_PATH)
        assert len(chunker.chunk_by_scene()) == EXPECTED_TOTAL

    def test_scene_types(self):
        chunker = ScreenplayChunker(screenplay_path=SCREENPLAY_PATH)
        types = {s["type"] for s in chunker._scenes}
        assert types <= {"INT", "EXT", "MONTAGE"}
        assert "MONTAGE" in types  # монтажные блоки 42/47/48


# ── Генератор производных структур (SynopsisBuilder) ────────────


class TestSynopsisBuilder:
    def _build(self):
        from intelligence.synopsis_builder import build_synopsis_document, build_synopsis_profile

        doc = build_synopsis_document(screenplay_path=SCREENPLAY_PATH)
        profile = build_synopsis_profile(doc)
        return doc, profile

    def test_scene_count(self):
        doc, _ = self._build()
        assert len(doc["content"]["chapters"]) == EXPECTED_TOTAL

    def test_raw_text_matches_source(self):
        doc, _ = self._build()
        raw = doc["content"]["raw_text"]
        orig = SCREENPLAY_PATH.read_text(encoding="utf-8")
        assert raw == orig

    def test_scene_offsets_self_consistent(self):
        doc, _ = self._build()
        raw = doc["content"]["raw_text"]
        for ch in doc["content"]["chapters"]:
            seg = raw[ch["char_start"] : ch["char_end"]]
            assert seg == ch["text"], f"scene {ch['id']} offset mismatch"

    def test_paragraph_offsets_self_consistent(self):
        doc, _ = self._build()
        raw = doc["content"]["raw_text"]
        for p in doc["content"]["paragraphs"]:
            if p["char_start"] < 0:
                raise AssertionError(f"paragraph {p['id']} has char_start=-1")
            seg = raw[p["char_start"] : p["char_end"]]
            assert seg == p["text"], f"paragraph {p['id']} offset mismatch"

    def test_paragraphs_cover_all_scenes(self):
        doc, _ = self._build()
        scene_ids = {ch["id"] for ch in doc["content"]["chapters"]}
        para_scene_ids = {p["scene_id"] for p in doc["content"]["paragraphs"]}
        assert para_scene_ids == scene_ids

    def test_profile_metrics_match_document(self):
        doc, profile = self._build()
        raw = doc["content"]["raw_text"]
        chapters = doc["content"]["chapters"]
        paragraphs = doc["content"]["paragraphs"]
        assert profile["metrics"]["total_chapters"] == len(chapters)
        assert profile["metrics"]["total_paragraphs"] == len(paragraphs)
        assert profile["metrics"]["total_chars"] == len(raw)

    def test_scene_ids_match_chunker(self):
        doc, _ = self._build()
        chunker = ScreenplayChunker(screenplay_path=SCREENPLAY_PATH)
        doc_ids = {ch["id"] for ch in doc["content"]["chapters"]}
        chunker_ids = {s["scene_id"] for s in chunker.chunk_by_scene()}
        assert doc_ids == chunker_ids

    def test_scenes_non_overlapping(self):
        doc, _ = self._build()
        prev_end = 0
        for ch in doc["content"]["chapters"]:
            assert ch["char_start"] >= prev_end, f"scene {ch['id']} overlaps"
            prev_end = ch["char_end"]


# ── API endpoint ────────────────────────────────────────────────


class TestScreenplayEndpoint:
    def test_api_returns_all_scenes(self):
        from fastapi.testclient import TestClient

        from core.main import app

        client = TestClient(app)
        resp = client.get("/book/screenplay")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["total"] == len(body["data"])
        assert body["total"] == EXPECTED_TOTAL
        # id/index идут по порядку без пропусков
        assert [d["index"] for d in body["data"]] == list(range(EXPECTED_TOTAL))
        assert len({d["id"] for d in body["data"]}) == EXPECTED_TOTAL

    def test_api_scenes_107_to_113_and_final(self):
        from fastapi.testclient import TestClient

        from core.main import app

        client = TestClient(app)
        titles = [d["title"].strip() for d in client.get("/book/screenplay").json()["data"]]
        for n in range(107, 114):
            assert any(t.startswith(f"{n}.") or t.startswith(f"{n} ") for t in titles), f"сцена {n} отсутствует в API"
        assert "INT. ПОЕЗД - ПЛАЦКАРТ - ДЕНЬ" in titles


# ── Индексация сценария в индекс знаний ────────────────────────


@pytest.fixture()
def indexed_retriever(tmp_path):
    """Изолированная индексация: KnowledgeKernel.index_screenplay() на временной ChromaDB.

    cwd не подкладывается: путь к сценарию обязан находиться и из runtime/.
    """
    pytest.importorskip("chromadb")

    from intelligence.kernel import KnowledgeKernel
    from intelligence.retriever import BookRetriever

    retriever = BookRetriever(persist_dir=tmp_path / "chroma")
    # Чужой источник знаний до переиндексации — не должен пострадать.
    retriever.index_chunk("other_source_chunk", "Фрагмент другого источника знаний.", {"source": "book"})
    kernel = KnowledgeKernel(retriever=retriever)
    result = kernel.index_screenplay()
    return retriever, result


class TestScreenplayIndexing:
    def test_index_reports_all_scenes(self, indexed_retriever):
        _, result = indexed_retriever
        assert result["status"] == "ok"
        assert result["scenes"] == EXPECTED_TOTAL

    def test_other_sources_untouched(self, indexed_retriever):
        retriever, _ = indexed_retriever
        col = retriever._get_collection()
        assert col.count() == EXPECTED_TOTAL + 1
        metas = col.get(include=["metadatas"])["metadatas"]
        by_source: dict[str, int] = {}
        for m in metas:
            key = (m or {}).get("source", "?")
            by_source[key] = by_source.get(key, 0) + 1
        assert by_source["book"] == 1
        assert by_source["screenplay"] == EXPECTED_TOTAL

    def test_indexed_documents_are_whole_scenes(self, indexed_retriever):
        retriever, _ = indexed_retriever
        col = retriever._get_collection()
        res = col.get(include=["metadatas", "documents"])
        chunker = ScreenplayChunker(screenplay_path=SCREENPLAY_PATH)
        whole = {s["text"]: s for s in chunker.chunk_by_scene()}
        scene_ids = set()
        for doc, meta in zip(res["documents"], res["metadatas"]):
            meta = meta or {}
            if meta.get("source") != "screenplay":
                continue
            scene_ids.add(meta["scene_id"])
            assert doc in whole, f"Документ {meta['scene_id']} не совпадает ни с одной сценой"
            for line in doc.split("\n"):
                assert not _is_screenplay_scene_header(line.strip()), f"В индекс попал склеенный фрагмент: {line.strip()!r}"
        assert scene_ids == {f"scene_{i:03d}" for i in range(EXPECTED_TOTAL)}

    def test_reindex_is_idempotent(self, indexed_retriever):
        retriever, _ = indexed_retriever
        col = retriever._get_collection()
        before = col.count()
        # Повторный штатный запуск не должен дублировать записи.
        from intelligence.kernel import KnowledgeKernel

        result = KnowledgeKernel(retriever=retriever).index_screenplay()
        assert result["status"] == "ok"
        assert col.count() == before

    def test_search_returns_separate_scenes(self, indexed_retriever):
        retriever, _ = indexed_retriever
        chunker = ScreenplayChunker(screenplay_path=SCREENPLAY_PATH)
        whole = {s["text"] for s in chunker.chunk_by_scene()}
        hits = retriever.search("переселенцы выходят из лагеря", n_results=8)
        screenplay_hits = [h for h in hits if (h.get("metadata") or {}).get("source") == "screenplay"]
        assert screenplay_hits, "поиск по сценарию не вернул ни одной сцены"
        for h in screenplay_hits:
            assert h["text"] in whole, "поиск вернул склеенный/обрезанный фрагмент вместо целой сцены"
