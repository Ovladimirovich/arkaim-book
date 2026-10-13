"""Тесты полного цикла переиндексации генома: книга + сценарий.

OWNER-GO: после любой штатной полной переиндексации в геноме обязаны быть и
книжные записи, и все 119 сцен сценария. Единая точка — KnowledgeKernel.reindex_full();
её же обязаны вызывать обе точки запуска (CI — core/run_index_book_v2.py,
cron — scripts/cron_reindex.py). Ошибка индексации сценария должна ронять
процесс, а не превращаться в «успешное обновление генома».

OWNER-GO: после index_book() цикл обязан сверить реально сохранённое число
книжных записей (count_source) с числом подготовленных чанков и при расхождении
упасть ДО индексации сценария — batch_index проглатывает ошибки записи,
а chunks_indexed отражает размер пачки, а не число сохранённых записей.
"""

from __future__ import annotations

import ast
import logging
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CORE_DIR = REPO_ROOT / "core" / "CORE"
TESTS_DIR = Path(__file__).resolve().parent
for _path in (str(CORE_DIR), str(TESTS_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from intelligence.chunker import ScreenplayChunker  # noqa: E402
from intelligence.retriever import BookRetriever  # noqa: E402
from knowledge_isolation import assert_isolated_kernel, working_knowledge_snapshot  # noqa: E402
from test_screenplay_parsing import EXPECTED_TOTAL  # noqa: E402

# chapter-режим (17 книжных чанков): контракт «книга + сценарий» от режима не
# зависит, а paragraph/hybrid (824/841 чанк) дороги для каждого теста —
# их покрывает test_knowledge_kernel::test_index_and_search.
MODE = "chapter"

ENTRY_POINTS = {
    "core/run_index_book_v2.py": REPO_ROOT / "core" / "run_index_book_v2.py",
    "scripts/cron_reindex.py": REPO_ROOT / "scripts" / "cron_reindex.py",
}


def _reindex_calls(source: str):
    """Все вызовы reindex_full в скрипте + цепочка Try-блоков вокруг них."""
    tree = ast.parse(source)
    parents: dict = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node

    calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute):
            name = func.attr
        else:
            name = getattr(func, "id", None)
        if name != "reindex_full":
            continue
        tries = []
        parent = parents.get(node)
        while parent is not None:
            if isinstance(parent, ast.Try):
                tries.append(parent)
            parent = parents.get(parent)
        calls.append((node, tries))
    return calls


class TestFullReindexCycle:
    def test_full_reindex_creates_book_and_scenes(self, isolated_kernel, tmp_path):
        kernel, retriever = isolated_kernel

        result = kernel.reindex_full(mode=MODE)

        assert result["status"] == "ok"
        book = result["book"]
        screenplay = result["screenplay"]
        assert book["status"] == "ok"
        assert book["chunks_total"] > 0
        assert screenplay == {"status": "ok", "scenes": EXPECTED_TOTAL, "indexed": EXPECTED_TOTAL}

        assert retriever.count_source("book") == book["chunks_total"]
        assert retriever.count_source("screenplay") == EXPECTED_TOTAL
        stats = retriever.get_collection_stats()
        assert stats["count"] == book["chunks_total"] + EXPECTED_TOTAL
        assert result["chroma"]["count"] == stats["count"]

        # enriched_* пишутся в BASE/KNOWLEDGE — во временном каталоге, а не в пользовательский.
        assert (tmp_path / "base" / "KNOWLEDGE" / "enriched_chunks.json").exists()
        assert (tmp_path / "base" / "KNOWLEDGE" / "enriched_catalog.json").exists()

    def test_second_run_creates_no_duplicates(self, isolated_kernel):
        kernel, retriever = isolated_kernel

        kernel.reindex_full(mode=MODE)
        first_ids = sorted(retriever._get_collection().get(include=[])["ids"])

        second = kernel.reindex_full(mode=MODE)

        assert second["status"] == "ok"
        second_ids = sorted(retriever._get_collection().get(include=[])["ids"])
        assert second_ids == first_ids
        assert len(second_ids) == len(set(second_ids))
        assert retriever.count_source("screenplay") == EXPECTED_TOTAL
        assert retriever.count_source("book") == second["book"]["chunks_total"]

    def test_screenplay_rerun_replaces_stale_records(self, isolated_kernel):
        """Повтор без очистки: устаревшие сцены (другой парсер) не копятся."""
        kernel, retriever = isolated_kernel

        kernel.reindex_full(mode=MODE)
        book_count = retriever.count_source("book")
        retriever.index_chunk(
            "scene_000_stale",
            "устаревшая версия сцены",
            {"source": "screenplay", "scene_id": "scene_000"},
        )
        assert retriever.count_source("screenplay") == EXPECTED_TOTAL + 1

        result = kernel.index_screenplay()

        assert result["status"] == "ok"
        assert result["scenes"] == EXPECTED_TOTAL
        assert retriever.count_source("screenplay") == EXPECTED_TOTAL
        ids = retriever._get_collection().get(include=[])["ids"]
        assert "scene_000_stale" not in ids
        # Чужой источник не пострадал.
        assert retriever.count_source("book") == book_count

    def test_search_finds_book_fragment_and_whole_scene(self, isolated_kernel):
        kernel, retriever = isolated_kernel
        kernel.reindex_full(mode=MODE)

        book_hits = retriever.search("Аркаим", n_results=20)
        book_results = [h for h in book_hits if h.get("source") == "book"]
        assert book_results, f"поиск не вернул книжный фрагмент: {[h.get('source') for h in book_hits]}"

        whole = {s["text"] for s in ScreenplayChunker().chunk_by_scene()}
        scene_hits = retriever.search("дорега дорога городок", n_results=20)
        scene_results = [h for h in scene_hits if h.get("source") == "screenplay"]
        assert scene_results, f"поиск не вернул ни одной сцены: {[h.get('source') for h in scene_hits]}"
        for hit in scene_results:
            assert hit["text"] in whole, "поиск вернул склеенный/обрезанный фрагмент вместо целой сцены"

    def test_screenplay_write_failure_fails_the_cycle(self, isolated_kernel, monkeypatch):
        """ChromaDB «проглотил» запись сценария — цикл обязан упасть, а не доложить об успехе."""
        kernel, retriever = isolated_kernel
        real_batch = retriever.batch_index

        def _book_only(chunks):
            # Глотаем запись только сценария: книжные записи доезжают полностью,
            # чтобы проверка дошла именно до шага «сценарий».
            book_chunks = [c for c in chunks if (c.get("metadata") or {}).get("source") == "book"]
            real_batch(book_chunks)

        monkeypatch.setattr(retriever, "batch_index", _book_only)

        with pytest.raises(RuntimeError, match="screenplay_index_failed"):
            kernel.reindex_full(mode=MODE)

        # Успех не доложен, и неполные данные не выдаются за полные.
        assert retriever.count_source("screenplay") == 0
        assert retriever.count_source("book") > 0  # книга прошла проверку до сценария

    def test_missing_screenplay_fails_the_cycle(self, isolated_kernel, monkeypatch):
        kernel, retriever = isolated_kernel
        monkeypatch.setattr(kernel, "index_screenplay", lambda: {"status": "no_screenplay", "scenes": 0})

        with pytest.raises(RuntimeError, match="screenplay_index_failed"):
            kernel.reindex_full(mode=MODE)

        assert retriever.count_source("screenplay") == 0

    def test_index_order_is_clear_then_book_then_screenplay(self, isolated_kernel, monkeypatch):
        kernel, retriever = isolated_kernel
        calls: list[str] = []
        monkeypatch.setattr(retriever, "clear_collection", lambda: calls.append("clear"))
        monkeypatch.setattr(
            kernel,
            "index_book",
            lambda mode="hybrid": calls.append(f"book:{mode}") or {"status": "ok", "chunks_total": 1, "chunks_indexed": 1},
        )
        # Проверка книги сверяется с count_source: сам index_book замокан,
        # поэтому подставляем ровно 1 книжную запись (1 подготовленный чанк).
        monkeypatch.setattr(retriever, "count_source", lambda source: 1 if source == "book" else 0)
        monkeypatch.setattr(
            kernel,
            "index_screenplay",
            lambda: calls.append("screenplay") or {"status": "ok", "scenes": EXPECTED_TOTAL, "indexed": EXPECTED_TOTAL},
        )

        result = kernel.reindex_full(mode=MODE)

        assert calls == ["clear", f"book:{MODE}", "screenplay"]
        assert result["status"] == "ok"


class TestBookIndexVerification:
    """Проверка полноты книжной индексации после index_book()."""

    def test_successful_run_saves_exactly_prepared_book_chunks(self, isolated_kernel, caplog):
        kernel, retriever = isolated_kernel

        with caplog.at_level(logging.INFO):
            result = kernel.reindex_full(mode=MODE)

        expected = result["book"]["chunks_total"]
        stored = retriever.count_source("book")
        assert expected > 0
        assert stored == expected, f"подготовлено {expected} чанков, в индексе {stored}"
        assert any("book_index_verified" in rec.getMessage() for rec in caplog.records), "проверка полноты книги не отработала"

    def test_partial_book_write_fails_before_screenplay(self, isolated_kernel, monkeypatch):
        """batch_index «проглотил» часть книжных записей — цикл обязан упасть до сценария."""
        kernel, retriever = isolated_kernel
        real_batch = retriever.batch_index
        seen: dict[str, int] = {}

        def _half_written(chunks):
            seen["total"] = len(chunks)
            real_batch(chunks[: max(1, len(chunks) // 2)])

        monkeypatch.setattr(retriever, "batch_index", _half_written)
        screenplay_calls: list[bool] = []
        monkeypatch.setattr(
            kernel,
            "index_screenplay",
            lambda: screenplay_calls.append(True) or {"status": "ok", "scenes": EXPECTED_TOTAL, "indexed": EXPECTED_TOTAL},
        )

        with pytest.raises(RuntimeError, match="book_index_failed") as exc_info:
            kernel.reindex_full(mode=MODE)

        # Никакого ложного успеха: исключение, а не возврат status=ok.
        assert "book_index_failed" in str(exc_info.value)
        assert seen["total"] > 0
        partial = retriever.count_source("book")
        assert partial == max(1, seen["total"] // 2)
        assert partial < seen["total"]
        # Сценарий не запускался до успешной проверки книги.
        assert not screenplay_calls, "сценарий обязан индексироваться только после проверки книги"
        assert retriever.count_source("screenplay") == 0


class TestIsolationFromWorkingDb:
    """Полный цикл выполняется только во временном хранилище."""

    def test_kernel_uses_only_temporary_storage(self, isolated_kernel, tmp_path):
        kernel, retriever = isolated_kernel

        paths = assert_isolated_kernel(kernel, retriever, tmp_path)

        assert paths["chroma"].startswith(str(tmp_path.resolve())), paths
        assert paths["knowledge_base"].startswith(str(tmp_path.resolve())), paths

    def test_full_cycle_keeps_working_db_intact(self, isolated_kernel, tmp_path):
        kernel, retriever = isolated_kernel
        before = working_knowledge_snapshot()

        kernel.reindex_full(mode=MODE)
        kernel.reindex_full(mode=MODE)  # очистка + повторный цикл

        after = working_knowledge_snapshot()
        assert after == before, f"тест перестроил рабочую базу знаний (до: {before}, после: {after})"

        # Цикл действительно отработал — но во временной базе.
        assert retriever.count_source("screenplay") == EXPECTED_TOTAL
        assert retriever.count_source("book") > 0
        assert Path(retriever.persist_dir).resolve().is_relative_to(tmp_path.resolve())

    def test_snapshot_detects_working_db_rebuild(self, tmp_path):
        """Контроль не фиктивный: отпечаток ловит очистку, перестройку и перезапись файлов."""
        knowledge_dir = tmp_path / "KNOWLEDGE"
        knowledge_dir.mkdir()
        enriched = knowledge_dir / "enriched_chunks.json"
        enriched.write_text("{}", encoding="utf-8")
        chroma_dir = tmp_path / "CHROMA_DB"

        retriever = BookRetriever(persist_dir=chroma_dir)
        retriever.index_chunk("chunk_1", "первый фрагмент", {"source": "book"})
        before = working_knowledge_snapshot(knowledge_dir, chroma_dir)
        assert before["collection"]["count"] == 1

        # Очистка + перестройка другой базы.
        retriever.clear_collection()
        retriever.index_chunk("chunk_1", "другой фрагмент", {"source": "book"})
        retriever.index_chunk("chunk_2", "второй фрагмент", {"source": "book"})
        rebuilt = working_knowledge_snapshot(knowledge_dir, chroma_dir)
        assert rebuilt["collection"] != before["collection"], "отпечаток не заметил перестройку коллекции"

        # Перезапись файлов-артефактов.
        enriched.write_text('{"пересобрано": true}', encoding="utf-8")
        after = working_knowledge_snapshot(knowledge_dir, chroma_dir)
        assert after["enriched_chunks"] != before["enriched_chunks"], "отпечаток не заметил перезапись enriched_chunks.json"


class TestEntryPointContracts:
    def test_both_entry_points_use_shared_reindex(self):
        """CI и cron идут через одну и ту же функцию — порядок не расходится."""
        for name, path in ENTRY_POINTS.items():
            source = path.read_text(encoding="utf-8")
            assert "reindex_full(" in source, f"{name}: обязан вызывать kernel.reindex_full()"
            assert "index_screenplay(" not in source, f"{name}: не должен вызывать index_screenplay напрямую"
            assert "index_book(" not in source, f"{name}: не должен вызывать index_book напрямую (порядок задаёт reindex_full)"

    def test_ci_entry_point_does_not_swallow_errors(self):
        source = ENTRY_POINTS["core/run_index_book_v2.py"].read_text(encoding="utf-8")
        calls = _reindex_calls(source)
        assert len(calls) == 1, "ожидался один вызов reindex_full"
        _, tries = calls[0]
        assert not tries, "ошибка переиндексации не должна перехватываться в CI-скрипте"

    def test_cron_entry_point_logs_and_reraises(self):
        source = ENTRY_POINTS["scripts/cron_reindex.py"].read_text(encoding="utf-8")
        assert "reindex_failed" in source
        assert "reindex_completed" in source

        calls = _reindex_calls(source)
        assert len(calls) == 1, "ожидался один вызов reindex_full"
        _, tries = calls[0]
        assert tries, "cron-скрипт обязан оборачивать переиндексацию в try/except"
        handler_raises = any(isinstance(node, ast.Raise) for handler in tries[0].handlers for node in ast.walk(handler))
        assert handler_raises, "после reindex_failed ошибка должна быть перевыброшена, а не поглощена"
