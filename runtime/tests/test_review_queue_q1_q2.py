# -*- coding: utf-8 -*-
"""Q1/Q2 очереди проверки кандидатов LLM.

Покрытие:
- Q1: индекс кандидатов (wrapped/bare-list, статусы, file-level пометка,
  стабильный id, фильтры, статистика);
- Q2: решения (approve/reject/reopen), права, обязательный комментарий,
  конфликты статусов, идемпотентность, атомарная запись, журнал;
- сквозная проверка: до решения кандидат закрыт гейтами 6d/6e, после
  APPROVED — проходит штатным путём.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CORE = REPO_ROOT / "core" / "CORE"
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))

from knowledge_expansion.expansion_loader import ExpansionLoader  # noqa: E402
from knowledge_expansion.provenance_gate import item_is_unverified  # noqa: E402
from knowledge_expansion.review import (  # noqa: E402
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    ReviewError,
    ValidationError,
    candidate_stats,
    decide,
    filter_candidates,
    find_candidate,
    iter_decisions,
    scan_candidates,
)
from knowledge_expansion.review.service import (  # noqa: E402
    CandidateNotFound,
    InvalidTransition,
    PermissionDenied,
    StaleCandidate,
)
from world_extraction.models import ExtractionResult, WorldKnowledge  # noqa: E402
from world_extraction.modules.traditions import project_world_model  # noqa: E402
from world_extraction.provenance import filter_extraction_result  # noqa: E402


def _meta(status: str = STATUS_PENDING, **overrides) -> dict:
    meta = {
        "category": "DERIVED",
        "provenance_category": "SYSTEM_INTERPRETATION",
        "source_level": "SYSTEM_INTERPRETATION",
        "source": "LLM",
        "model": "GigaChat",
        "generated_at": "2026-10-28T12:00:00+00:00",
        "requires_author_review": True,
        "status": status,
    }
    meta.update(overrides)
    return meta


def _item(topic: str = "Сварга", literal: str = "Небесный круг", status: str = STATUS_PENDING) -> dict:
    meta = _meta(status)
    return {
        "topic": topic,
        "content": "",
        "layers": {"literal": literal, "metaphorical": "путь восхождения"},
        "metadata": {"_provenance_metadata": dict(meta)},
        "_provenance_metadata": meta,
    }


def _write(path: Path, payload: object, *, bom: bool = False, newline: bool = True) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if newline:
        text += "\n"
    data = text.encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    path.write_bytes(data)


def _wrapped(*items: dict) -> dict:
    return {"_provenance_metadata": {"category": "DERIVED"}, "items": list(items)}


class TestIndex:
    def test_finds_candidate_in_wrapped_file(self, tmp_path: Path):
        _write(tmp_path / "PHILOSOPHY_DEEP.json", _wrapped(_item()))

        records = scan_candidates(tmp_path)

        assert len(records) == 1
        record = records[0]
        assert record.file == "PHILOSOPHY_DEEP.json"
        assert record.container == "items"
        assert record.index == 0
        assert record.topic == "Сварга"
        assert record.status == STATUS_PENDING
        assert record.source == "LLM"
        assert record.locator == "PHILOSOPHY_DEEP.json#items[0]"
        assert record.preview.startswith("Небесный круг")

    def test_finds_candidate_in_bare_list(self, tmp_path: Path):
        _write(tmp_path / "NEW_OUTPUT.json", [_item("Заря")])

        records = scan_candidates(tmp_path)

        assert [r.locator for r in records] == ["NEW_OUTPUT.json#[0]"]

    def test_plain_record_is_not_a_candidate(self, tmp_path: Path):
        _write(tmp_path / "GEOGRAPHY.json", _wrapped({"topic": "Аркаим", "content": "город"}))

        assert scan_candidates(tmp_path) == []

    def test_approved_and_rejected_stay_visible(self, tmp_path: Path):
        _write(
            tmp_path / "PHILOSOPHY_DEEP.json",
            _wrapped(_item("Одобрено", status=STATUS_APPROVED), _item("Отклонено", status=STATUS_REJECTED)),
        )

        statuses = {r.topic: r.status for r in scan_candidates(tmp_path)}

        assert statuses == {"Одобрено": STATUS_APPROVED, "Отклонено": STATUS_REJECTED}

    def test_file_level_flag_marks_records(self, tmp_path: Path):
        _write(
            tmp_path / "PHILOSOPHY_DEEP.json",
            {
                "_provenance_metadata": _meta(STATUS_PENDING),
                "items": [_item()],
            },
        )

        [record] = scan_candidates(tmp_path)

        assert record.file_blocked is True

    def test_id_survives_reorder_and_changes_with_text(self, tmp_path: Path):
        first = _item("Альфа", "текст альфы")
        second = _item("Бета", "текст беты")
        _write(tmp_path / "PHILOSOPHY_DEEP.json", _wrapped(first, second))
        before = {r.topic: r.candidate_id for r in scan_candidates(tmp_path)}

        _write(tmp_path / "PHILOSOPHY_DEEP.json", _wrapped(second, first))
        after = {r.topic: r.candidate_id for r in scan_candidates(tmp_path)}

        assert before == after
        _write(tmp_path / "PHILOSOPHY_DEEP.json", _wrapped(_item("Альфа", "другой текст"), second))
        changed = {r.topic: r.candidate_id for r in scan_candidates(tmp_path)}
        assert changed["Альфа"] != before["Альфа"]

    def test_filters_and_pagination(self, tmp_path: Path):
        _write(
            tmp_path / "PHILOSOPHY_DEEP.json",
            _wrapped(_item("Альфа"), _item("Бета", status=STATUS_REJECTED)),
        )
        _write(tmp_path / "SYMBOLS_DEEP.json", _wrapped(_item("Гамма", "символ")))

        records = scan_candidates(tmp_path)

        assert [r.topic for r in filter_candidates(records, status=STATUS_PENDING)] == ["Альфа", "Гамма"]
        assert [r.topic for r in filter_candidates(records, file="SYMBOLS_DEEP.json")] == ["Гамма"]
        assert [r.topic for r in filter_candidates(records, query="символ")] == ["Гамма"]
        assert [r.topic for r in filter_candidates(records, limit=1, offset=1)] == ["Бета"]

    def test_stats(self, tmp_path: Path):
        _write(
            tmp_path / "PHILOSOPHY_DEEP.json",
            _wrapped(_item("Альфа"), _item("Бета", status=STATUS_REJECTED)),
        )

        stats = candidate_stats(scan_candidates(tmp_path))

        assert stats["total"] == 2
        assert stats["pending"] == 1
        assert stats["by_status"] == {STATUS_APPROVED: 0, STATUS_PENDING: 1, STATUS_REJECTED: 1}
        assert stats["by_file"] == {"PHILOSOPHY_DEEP.json": 2}
        assert stats["by_source"] == {"LLM": 2}

    def test_unknown_id(self, tmp_path: Path):
        assert find_candidate("cand_000000000000", tmp_path) is None


class TestDecisions:
    @staticmethod
    def _setup(tmp_path: Path, item: dict | None = None) -> tuple[Path, dict, str]:
        item = item or _item()
        _write(tmp_path / "PHILOSOPHY_DEEP.json", _wrapped(item))
        candidate_id = scan_candidates(tmp_path)[0].candidate_id
        return tmp_path, item, candidate_id

    @staticmethod
    def _kwargs(tmp_path: Path, **overrides) -> dict:
        kwargs = {
            "actor": "owner",
            "role": "author",
            "comment": "Согласуется с главой 4",
            "knowledge_dir": tmp_path,
            "journal_path": tmp_path / "journal.jsonl",
            "backup_dir": tmp_path / "backups",
        }
        kwargs.update(overrides)
        return kwargs

    def test_approve_opens_gates(self, tmp_path: Path):
        knowledge, item, candidate_id = self._setup(tmp_path)

        updated = decide(candidate_id, "approve", **self._kwargs(knowledge))

        assert updated.status == STATUS_APPROVED
        assert updated.reviewed_by == "owner"
        assert updated.review_comment == "Согласуется с главой 4"
        document = json.loads((knowledge / "PHILOSOPHY_DEEP.json").read_text(encoding="utf-8"))
        record = document["items"][0]
        assert record["_provenance_metadata"]["status"] == STATUS_APPROVED
        assert record["_provenance_metadata"]["requires_author_review"] is False
        assert record["metadata"]["_provenance_metadata"]["status"] == STATUS_APPROVED
        assert item_is_unverified(record) is False

    def test_approved_candidate_reaches_rag_and_world(self, tmp_path: Path):
        knowledge, _, candidate_id = self._setup(tmp_path)
        decide(candidate_id, "approve", **self._kwargs(knowledge))
        path = knowledge / "PHILOSOPHY_DEEP.json"

        loader = ExpansionLoader(knowledge_dir=knowledge)
        loaded = loader.load()
        assert loader.stats["skipped_unverified"] == 0
        assert "сварга" in loaded

        extraction = ExtractionResult(
            category="philosophy",
            source_files=[path],
            items=[WorldKnowledge(id="p", name="Сварга", source=path.name)],
        )
        assert filter_extraction_result(extraction) == 0
        assert len(extraction.items) == 1

        wm = tmp_path / "WORLD_MODEL"
        wm.mkdir()
        _write(
            wm / "MYTHOLOGY.json",
            [{"id": "myth_сварга", "name": "Сварга", "description": "", "provenance_category": "UNKNOWN"}],
        )
        (knowledge / "SYMBOLS_DEEP.json").write_text(
            json.dumps({"items": [{"topic": "Сварга", "layers": {"literal": "Небесный круг"}}]}),
            encoding="utf-8",
        )
        (knowledge / "COSMOLOGY.json").write_text('{"items": []}', encoding="utf-8")
        (knowledge / "RITUALS.json").write_text('{"items": []}', encoding="utf-8")
        (knowledge / "ESOTERIC_CONNECTIONS.json").write_text('{"traditions": []}', encoding="utf-8")
        project_world_model(wm, knowledge)
        shell = json.loads((wm / "MYTHOLOGY.json").read_text(encoding="utf-8"))[0]
        assert "Небесный круг" in shell["description"]

    def test_pending_candidate_stays_closed(self, tmp_path: Path):
        knowledge, _, _ = self._setup(tmp_path)
        path = knowledge / "PHILOSOPHY_DEEP.json"

        loader = ExpansionLoader(knowledge_dir=knowledge)
        assert loader.load() == {}
        assert loader.stats["skipped_unverified"] == 1

        extraction = ExtractionResult(
            category="philosophy",
            source_files=[path],
            items=[WorldKnowledge(id="p", name="Сварга", source=path.name)],
        )
        assert filter_extraction_result(extraction) == 1
        assert extraction.items == []

    def test_reject_keeps_text_and_blocks(self, tmp_path: Path):
        knowledge, _, candidate_id = self._setup(tmp_path)

        updated = decide(
            candidate_id,
            "reject",
            **self._kwargs(knowledge, comment="Формулировка не из книги"),
        )

        assert updated.status == STATUS_REJECTED
        document = json.loads((knowledge / "PHILOSOPHY_DEEP.json").read_text(encoding="utf-8"))
        record = document["items"][0]
        assert record["layers"]["literal"] == "Небесный круг"
        assert record["_provenance_metadata"]["requires_author_review"] is True
        assert item_is_unverified(record) is True

    def test_reopen_returns_to_review(self, tmp_path: Path):
        knowledge, _, candidate_id = self._setup(tmp_path)
        decide(candidate_id, "reject", **self._kwargs(knowledge, comment="Не подходит"))

        reopened = decide(candidate_id, "reopen", **self._kwargs(knowledge, comment="Проверить ещё раз"))

        assert reopened.status == STATUS_PENDING
        assert reopened.review_comment == "Проверить ещё раз"

    def test_rejected_cannot_be_approved_directly(self, tmp_path: Path):
        knowledge, _, candidate_id = self._setup(tmp_path)
        decide(candidate_id, "reject", **self._kwargs(knowledge, comment="Не подходит"))

        with pytest.raises(InvalidTransition):
            decide(candidate_id, "approve", **self._kwargs(knowledge))

    def test_approved_cannot_be_reopened_directly(self, tmp_path: Path):
        knowledge, _, candidate_id = self._setup(tmp_path)
        decide(candidate_id, "approve", **self._kwargs(knowledge))

        with pytest.raises(InvalidTransition):
            decide(candidate_id, "reopen", **self._kwargs(knowledge, comment="Передумал"))

    def test_only_author_and_admin(self, tmp_path: Path):
        knowledge, _, candidate_id = self._setup(tmp_path)

        with pytest.raises(PermissionDenied):
            decide(candidate_id, "approve", **self._kwargs(knowledge, role="viewer"))
        with pytest.raises(PermissionDenied):
            decide(candidate_id, "approve", **self._kwargs(knowledge, actor="  "))

        assert scan_candidates(knowledge)[0].status == STATUS_PENDING

    def test_comment_is_required(self, tmp_path: Path):
        knowledge, _, candidate_id = self._setup(tmp_path)

        with pytest.raises(ValidationError):
            decide(candidate_id, "approve", **self._kwargs(knowledge, comment="  "))
        with pytest.raises(ValidationError):
            decide(candidate_id, "reject", **self._kwargs(knowledge, comment="ok"))

    def test_unknown_candidate(self, tmp_path: Path):
        knowledge, _, _ = self._setup(tmp_path)

        with pytest.raises(CandidateNotFound):
            decide("cand_ffffffffffff", "approve", **self._kwargs(knowledge))

    def test_stale_expected_status(self, tmp_path: Path):
        knowledge, _, candidate_id = self._setup(tmp_path)

        with pytest.raises(StaleCandidate):
            decide(
                candidate_id,
                "approve",
                **self._kwargs(knowledge, expected_status=STATUS_APPROVED),
            )
        assert scan_candidates(knowledge)[0].status == STATUS_PENDING

    def test_approve_is_idempotent(self, tmp_path: Path):
        knowledge, _, candidate_id = self._setup(tmp_path)
        kwargs = self._kwargs(knowledge)

        first = decide(candidate_id, "approve", **kwargs)
        second = decide(candidate_id, "approve", **kwargs)

        assert first.status == second.status == STATUS_APPROVED
        decisions = list(iter_decisions(candidate_id, journal_path=knowledge / "journal.jsonl"))
        assert len(decisions) == 1

    def test_file_level_block_cannot_be_approved(self, tmp_path: Path):
        _write(
            tmp_path / "PHILOSOPHY_DEEP.json",
            {"_provenance_metadata": _meta(STATUS_PENDING), "items": [_item()]},
        )
        candidate_id = scan_candidates(tmp_path)[0].candidate_id

        with pytest.raises(InvalidTransition) as error:
            decide(candidate_id, "approve", **self._kwargs(tmp_path))

        assert error.value.code == "file_level_blocked"
        document = json.loads((tmp_path / "PHILOSOPHY_DEEP.json").read_text(encoding="utf-8"))
        assert document["items"][0]["_provenance_metadata"]["status"] == STATUS_PENDING

    def test_bare_list_format_is_preserved(self, tmp_path: Path):
        _write(tmp_path / "NEW_OUTPUT.json", [_item()])
        candidate_id = scan_candidates(tmp_path)[0].candidate_id

        decide(candidate_id, "approve", **self._kwargs(tmp_path))

        document = json.loads((tmp_path / "NEW_OUTPUT.json").read_text(encoding="utf-8"))
        assert isinstance(document, list)
        assert document[0]["_provenance_metadata"]["status"] == STATUS_APPROVED

    def test_bom_and_newline_are_preserved(self, tmp_path: Path):
        _write(tmp_path / "PHILOSOPHY_DEEP.json", _wrapped(_item()), bom=True, newline=True)
        candidate_id = scan_candidates(tmp_path)[0].candidate_id

        decide(candidate_id, "approve", **self._kwargs(tmp_path))

        raw = (tmp_path / "PHILOSOPHY_DEEP.json").read_bytes()
        assert raw.startswith(b"\xef\xbb\xbf")
        assert raw.endswith(b"\n")

    def test_unrelated_fields_and_records_untouched(self, tmp_path: Path):
        verified = {"topic": "Проверено", "content": "текст книги"}
        _write(tmp_path / "PHILOSOPHY_DEEP.json", _wrapped(_item(), verified))
        candidate_id = scan_candidates(tmp_path)[0].candidate_id

        decide(candidate_id, "approve", **self._kwargs(tmp_path))

        document = json.loads((tmp_path / "PHILOSOPHY_DEEP.json").read_text(encoding="utf-8"))
        assert document["_provenance_metadata"] == {"category": "DERIVED"}
        assert document["items"][1] == verified

    def test_backup_and_journal_written(self, tmp_path: Path):
        knowledge, _, candidate_id = self._setup(tmp_path)

        decide(
            candidate_id,
            "approve",
            **self._kwargs(knowledge, expected_status=STATUS_PENDING),
        )

        backups = list((knowledge / "backups").glob("*PHILOSOPHY_DEEP.json"))
        assert len(backups) == 1
        [entry] = list(iter_decisions(candidate_id, journal_path=knowledge / "journal.jsonl"))
        assert entry["action"] == "approve"
        assert entry["from"] == STATUS_PENDING
        assert entry["to"] == STATUS_APPROVED
        assert entry["actor"] == "owner"
        assert entry["file"] == "PHILOSOPHY_DEEP.json"
        assert entry["locator"] == "PHILOSOPHY_DEEP.json#items[0]"
        assert entry["comment"]

    def test_duplicate_records_get_distinct_ids(self, tmp_path: Path):
        """Полные дубли в одном файле не должны делить один id."""
        _write(tmp_path / "PHILOSOPHY_DEEP.json", _wrapped(_item(), _item()))

        records = scan_candidates(tmp_path)
        ids = [r.candidate_id for r in records]

        assert len(ids) == 2
        assert len(set(ids)) == 2
        assert ids[1] == f"{ids[0]}-2"

    def test_duplicates_can_be_approved_one_by_one(self, tmp_path: Path):
        _write(tmp_path / "PHILOSOPHY_DEEP.json", _wrapped(_item(), _item()))
        first, second = scan_candidates(tmp_path)

        decide(first.candidate_id, "approve", **self._kwargs(tmp_path))
        decide(second.candidate_id, "approve", **self._kwargs(tmp_path))

        statuses = [r.status for r in scan_candidates(tmp_path)]
        assert statuses == [STATUS_APPROVED, STATUS_APPROVED]

    def test_journal_failure_rolls_back_file(self, tmp_path: Path):
        knowledge, _, candidate_id = self._setup(tmp_path)
        journal_dir = knowledge / "journal_dir"
        journal_dir.mkdir()

        with pytest.raises(ReviewError) as error:
            decide(
                candidate_id,
                "approve",
                **self._kwargs(knowledge, journal_path=journal_dir),
            )

        assert error.value.code == "journal_failed"
        assert scan_candidates(knowledge)[0].status == STATUS_PENDING

    def test_journal_skips_broken_lines(self, tmp_path: Path):
        journal = tmp_path / "journal.jsonl"
        journal.write_text('{"candidate_id": "cand_1", "action": "approve"}\nnot json\n', encoding="utf-8")

        entries = list(iter_decisions(journal_path=journal))

        assert [e["candidate_id"] for e in entries] == ["cand_1"]
