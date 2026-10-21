"""M24 — tests: измеримый критерий полноты тем книги в Knowledge Core.

Тесты изолированы (tmp_path-фикстуры, без реального генома/каталога/
ExpansionLoader): проверяем контракт критерия — полная тема / частичная /
отсутствующая / retrieval trap / метрики и воспроизводимость отчёта.
Реальные данные гоняются ручным прогоном сервиса, не pytest-фикстурами.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.services.theme_completeness import (
    STATUS_COMPLETE,
    STATUS_MISSING,
    STATUS_PARTIAL,
    build_catalog_theme_index,
    build_theme_completeness_report,
    evaluate_theme,
    load_reference_themes,
)


def _write_genome(path: Path, themes: list[dict]) -> Path:
    path.write_text(json.dumps({"modules": {"themes": themes}}, ensure_ascii=False), encoding="utf-8")
    return path


def _write_catalog(path: Path, entries: list[dict]) -> Path:
    path.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    return path


# ─── 1. Reference list ─────────────────────────────────────────────────────────


class TestReferenceList:
    def test_valid_theme_accepted(self, tmp_path: Path):
        genome = _write_genome(tmp_path / "g.json", [{"id": "theme_1", "name": "Аркаим", "description": "x", "strength": 0.9}])
        valid, invalid = load_reference_themes(genome)
        assert len(valid) == 1
        assert invalid == []

    def test_bad_id_recorded_as_invalid_not_fabricated(self, tmp_path: Path):
        genome = _write_genome(tmp_path / "g.json", [{"id": "topic_7", "name": "X"}, {"id": "theme_2", "name": ""}])
        valid, invalid = load_reference_themes(genome)
        assert valid == []
        assert len(invalid) == 2
        assert all("reason" in item for item in invalid)

    def test_missing_modules_themes_returns_empty(self, tmp_path: Path):
        genome = tmp_path / "g.json"
        genome.write_text("{}", encoding="utf-8")
        valid, invalid = load_reference_themes(genome)
        assert valid == [] and invalid == []


# ─── 2. Catalog index ──────────────────────────────────────────────────────────


class TestCatalogIndex:
    def test_tag_normalization_and_dedup(self, tmp_path: Path):
        catalog = _write_catalog(
            tmp_path / "c.json",
            [
                {"id": "chunk_a", "themes": ["Кали  Юга", "Гиперборея"]},
                {"id": "chunk_b", "themes": "Кали Юга, Аркаим"},
            ],
        )
        index = build_catalog_theme_index(catalog)
        assert index["кали юга"] == ["chunk_a", "chunk_b"]
        assert index["гиперборея"] == ["chunk_a"]
        assert index["аркаим"] == ["chunk_b"]

    def test_entry_without_id_skipped(self, tmp_path: Path):
        catalog = _write_catalog(tmp_path / "c.json", [{"themes": ["Аркаим"]}, {"id": "chunk_x", "themes": []}])
        index = build_catalog_theme_index(catalog)
        assert index == {}


# ─── 3. Presence statuses ──────────────────────────────────────────────────────


class TestThemePresence:
    def test_full_topic_exact_tag_is_complete(self):
        index = {"аркаим": ["chunk_p_1"]}
        result = evaluate_theme({"id": "theme_1", "name": "Аркаим"}, index)
        assert result.status == STATUS_COMPLETE
        assert result.exact_chunk_ids == ("chunk_p_1",)
        assert result.needs_resolution is False

    def test_missing_topic(self):
        result = evaluate_theme({"id": "theme_9", "name": "Несуществующая тема"}, {"аркаим": ["c"]})
        assert result.status == STATUS_MISSING
        assert result.needs_resolution is False
        assert result.exact_chunk_ids == ()

    def test_partial_topic_near_tag_needs_resolution(self):
        result = evaluate_theme({"id": "theme_2", "name": "Энергетика"}, {"энергетика мест": ["c1"]})
        assert result.status == STATUS_PARTIAL
        assert result.near_matches == ("энергетика мест",)
        assert result.needs_resolution is True

    def test_partial_topic_expansion_only(self):
        result = evaluate_theme({"id": "theme_3", "name": "Звукознание"}, {}, expansion_keys={"звукознание"})
        assert result.status == STATUS_PARTIAL
        assert result.in_expansion is True
        assert result.needs_resolution is False

    def test_complete_wins_over_expansion_flag(self):
        result = evaluate_theme({"id": "theme_4", "name": "Аркаим"}, {"аркаим": ["c"]}, expansion_keys={"аркаим"})
        assert result.status == STATUS_COMPLETE
        assert result.in_expansion is True

    def test_normalization_casefold_and_yo(self):
        index = {"энергетика мест": ["c1"], "роль посвященных": ["c2"]}
        assert evaluate_theme({"id": "theme_5", "name": "ЭНЕРГЕТИКА  мест"}, index).status == STATUS_COMPLETE
        assert evaluate_theme({"id": "theme_6", "name": "роль посвящённых"}, index).status == STATUS_COMPLETE

    def test_retrieval_trap_theme_present_stays_complete(self):
        """Тема есть в знаниях (точный тег каталога), retrieval-поиск её не вернул.

        Контракт: статус зависит только от прямого catalog lookup; мок-«retriever»,
        возвращающий пусто, не может изменить результат (retrieval trap).
        """

        class _EmptyRetriever:
            def search(self, query: str, n_results: int = 5):
                return []

        retriever = _EmptyRetriever()
        assert retriever.search("Гиперборея") == []  # retrieval не нашёл
        # но прямой lookup по каталогу находит точный тег → тема присутствует
        result = evaluate_theme({"id": "theme_7", "name": "Гиперборея"}, {"гиперборея": ["chunk_p_9"]})
        assert result.status == STATUS_COMPLETE
        assert result.exact_chunk_ids == ("chunk_p_9",)

    def test_service_does_not_use_retrieval(self):
        """Сервис критерия не зависит от retrieval-подсистемы (контракт импортов)."""
        import ast

        import core.services.theme_completeness as module

        tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        assert not any(name.startswith(("intelligence", "chromadb")) for name in imported)
        assert "knowledge_expansion.expansion_loader" in imported  # DERIVED-сигнал разрешён


# ─── 4. Report metrics ─────────────────────────────────────────────────────────


class TestReportMetrics:
    def _fixture(self, tmp_path: Path) -> dict:
        genome = _write_genome(
            tmp_path / "g.json",
            [
                {"id": "theme_1", "name": "Аркаим"},
                {"id": "theme_2", "name": "Энергетика"},
                {"id": "theme_3", "name": "Звукознание"},
                {"id": "theme_4", "name": "Потерянная тема"},
                {"id": "theme_5", "name": "Идея Вечности"},
            ],
        )
        catalog = _write_catalog(
            tmp_path / "c.json",
            [{"id": "chunk_p_1", "themes": ["Аркаим", "энергетика мест"]}],
        )
        return build_theme_completeness_report(
            genome_path=genome,
            catalog_path=catalog,
            expansion_keys={"звукознание"},
        )

    def test_counts_and_percent(self, tmp_path: Path):
        report = self._fixture(tmp_path)
        assert report["total"] == 5
        assert report["present"] == 1
        assert report["partial"] == 2
        assert report["missing"] == 2
        assert report["percent_complete"] == 20.0

    def test_needs_resolution_only_near_matches(self, tmp_path: Path):
        report = self._fixture(tmp_path)
        assert report["needs_resolution"] == 1

    def test_problem_topics_list_and_order(self, tmp_path: Path):
        report = self._fixture(tmp_path)
        ids = [item["theme_id"] for item in report["problem_topics"]]
        assert ids == ["theme_2", "theme_3", "theme_4", "theme_5"]
        statuses = {item["theme_id"]: item["status"] for item in report["problem_topics"]}
        assert statuses["theme_2"] == STATUS_PARTIAL
        assert statuses["theme_3"] == STATUS_PARTIAL
        assert statuses["theme_4"] == STATUS_MISSING

    def test_reference_invalid_records_surfaced(self, tmp_path: Path):
        genome = _write_genome(tmp_path / "g.json", [{"id": "bad", "name": "X"}, {"id": "theme_1", "name": "Аркаим"}])
        catalog = _write_catalog(tmp_path / "c.json", [{"id": "c1", "themes": ["Аркаим"]}])
        report = build_theme_completeness_report(genome_path=genome, catalog_path=catalog, expansion_keys=set())
        assert report["total"] == 1
        assert report["present"] == 1
        assert len(report["reference"]["invalid_records"]) == 1

    def test_report_is_deterministic(self, tmp_path: Path):
        first = self._fixture(tmp_path)
        second = self._fixture(tmp_path)
        assert first == second

    def test_empty_reference_zero_metrics(self, tmp_path: Path):
        genome = _write_genome(tmp_path / "g.json", [])
        catalog = _write_catalog(tmp_path / "c.json", [])
        report = build_theme_completeness_report(genome_path=genome, catalog_path=catalog, expansion_keys=set())
        assert report["total"] == 0
        assert report["percent_complete"] == 0.0
        assert report["problem_topics"] == []
