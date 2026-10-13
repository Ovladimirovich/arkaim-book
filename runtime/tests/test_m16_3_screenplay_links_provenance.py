"""M16.3 — Persisted screenplay↔book links carry provenance metadata.

Каждая запись core/KNOWLEDGE/screenplay_links.json несёт обязательное
_provenance_metadata (Milestone B, vocabulary из narrative_engine.source_levels).
Исходный 4-полевой контракт (screenplay_scene_id, book_chunk_id, confidence,
notes) сохранён: read-only потребители (ScreenplayBookLinker) не изменены,
аудитные поля лежат только под _provenance_metadata.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_CORE = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from knowledge.screenplay_linker import ScreenplayBookLinker  # noqa: E402
from knowledge.screenplay_links_provenance import (  # noqa: E402
    APPROVED_PAIRS,
    REPO_ROOT,
    SCREENPLAY_LINKS_PATH,
    build_approved_link_records,
    load_existing_records,
    main,
    save_screenplay_links,
    validate_screenplay_links,
)


def _real_data() -> list[dict]:
    return json.loads(SCREENPLAY_LINKS_PATH.read_text(encoding="utf-8"))


# ── Файл данных на диске ──────────────────────────────────────────────


class TestProvenanceOnDisk:
    """Персистированный файл несёт _provenance_metadata у каждой записи."""

    def test_every_record_has_provenance(self):
        data = _real_data()
        assert len(data) == len(APPROVED_PAIRS)
        for rec in data:
            meta = rec["_provenance_metadata"]
            assert meta["category"] == "AUTHOR_CANON"
            assert meta["source_level"] == "CANON"
            assert meta["enriched_at"] == "Milestone B"
            assert meta["resolved_by"]
            assert meta["resolved_at"]
            assert meta["confidence"] == rec["confidence"] == 1.0

    def test_refs_consistent_with_record_ids(self):
        for rec in _real_data():
            meta = rec["_provenance_metadata"]
            assert meta["evidence_ref"] == f"book:{rec['book_chunk_id']}"
            assert meta["screenplay_ref"] == f"screenplay:scene:{rec['screenplay_scene_id']}"

    def test_evidence_files_exist(self):
        files = {f for rec in _real_data() for f in rec["_provenance_metadata"]["evidence_files"]}
        assert files
        for f in files:
            assert (REPO_ROOT / f).exists(), f"нет файла-доказательства: {f}"

    def test_core_contract_fields_unchanged(self):
        for rec in _real_data():
            for key in ("screenplay_scene_id", "book_chunk_id", "confidence", "notes"):
                assert key in rec, key
            # OWNER-обоснования (M16.1) сохранились при регенерации
            assert "Дословная цитата" in rec["notes"]
            assert "не утверждение о полной идентичности" in rec["notes"]

    def test_validation_passes_on_persisted_file(self):
        assert validate_screenplay_links(_real_data()) == []

    def test_read_only_linker_ignores_provenance(self):
        """4-полевой read-only контракт: линкер читает только базовые поля."""
        linker = ScreenplayBookLinker.from_json()
        assert len(linker.links) == len(APPROVED_PAIRS)
        assert {(link.screenplay_scene_id, link.book_chunk_id) for link in linker.links} == APPROVED_PAIRS


# ── Генератор: сборка, сохранение, round-trip (только tmp) ───────────


class TestGeneratorRoundTrip:
    """Генерация идемпотентна и не трогает рабочую базу знаний."""

    def test_build_preserves_notes_and_adds_nested_provenance(self):
        existing = load_existing_records()
        records = build_approved_link_records(existing=existing)
        assert len(records) == len(APPROVED_PAIRS)
        for rec in records:
            assert "_provenance_metadata" in rec
            meta = rec["_provenance_metadata"]
            assert "_provenance_metadata" not in meta, "вложенность запрещена"
            assert meta["category"] == "AUTHOR_CANON"
            # OWNER-обоснование сохраняется из текущего файла (ключ — пара scene/chunk)
            assert rec["notes"] == existing[(rec["screenplay_scene_id"], rec["book_chunk_id"])]["notes"]

    def test_save_validate_roundtrip_in_tmp(self, tmp_path):
        out = tmp_path / "screenplay_links.json"
        save_screenplay_links(build_approved_link_records(existing=load_existing_records()), out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert validate_screenplay_links(data) == []
        # атомарная запись: временный файл не остаётся
        assert not out.with_name("screenplay_links.json.tmp").exists()

    def test_main_out_option_writes_to_tmp(self, tmp_path):
        out = tmp_path / "links.json"
        assert main(["--out", str(out)]) == 0
        assert validate_screenplay_links(json.loads(out.read_text(encoding="utf-8"))) == []


class TestValidatorNegatives:
    """Валидатор ловит нарушения контракта provenance."""

    def _copy(self) -> list[dict]:
        return json.loads(json.dumps(_real_data()))

    def test_missing_provenance_flagged(self):
        data = self._copy()
        data[0].pop("_provenance_metadata")
        errs = validate_screenplay_links(data)
        assert any("_provenance_metadata" in e for e in errs)

    def test_wrong_category_flagged(self):
        data = self._copy()
        data[0]["_provenance_metadata"]["category"] = "DERIVED"
        errs = validate_screenplay_links(data)
        assert any("category" in e for e in errs)

    def test_unapproved_pair_flagged(self):
        data = self._copy()
        data[0]["book_chunk_id"] = "chunk_p_0001_deadbeef00"
        errs = validate_screenplay_links(data)
        assert any("pair set differs" in e for e in errs)

    def test_duplicate_scene_flagged(self):
        data = self._copy()
        data.append(json.loads(json.dumps(data[0])))
        errs = validate_screenplay_links(data)
        assert any("duplicate" in e for e in errs)

    def test_missing_evidence_file_flagged(self):
        data = self._copy()
        data[0]["_provenance_metadata"]["evidence_files"] = ["core/KNOWLEDGE/absent_file_123.json"]
        errs = validate_screenplay_links(data)
        assert any("not found" in e for e in errs)

    def test_not_a_list_flagged(self):
        errs = validate_screenplay_links({"screenplay_scene_id": "scene_006"})
        assert errs and "JSON array" in errs[0]


# ── CLI-обёртка scripts/generate_screenplay_links.py ──────────────────


class TestScriptWrapper:
    def test_wrapper_main_writes_and_validates(self, tmp_path):
        script = REPO_ROOT / "scripts" / "generate_screenplay_links.py"
        assert script.exists(), "scripts/generate_screenplay_links.py отсутствует"
        spec = importlib.util.spec_from_file_location("_gen_screenplay_links", script)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        out = tmp_path / "links.json"
        assert mod.main(["--out", str(out)]) == 0
        data = json.loads(out.read_text(encoding="utf-8"))
        assert validate_screenplay_links(data) == []
        assert len(data) == len(APPROVED_PAIRS)
