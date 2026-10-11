"""M2 — Evidence integration tests (repository + resolver).

Narrow scope: connect the existing Evidence model to the Book OS / source
infrastructure through a repository and a resolver. These tests do not touch
WorldModel, Temporal, crosswalk or claim semantics.
"""

from __future__ import annotations

import sys
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

import pytest

from evidence.repository import EvidenceNotFoundError, EvidenceRepository
from evidence.resolver import (
    BOOK_CHUNK_PREFIX,
    BookChunkSource,
    EvidenceResolver,
    ResolutionStatus,
    locator_for_chunk,
)
from schemas.evidence import Evidence


def _book_chunk(chunk_id: str = "chunk_1", text: str = "фрагмент книги") -> dict:
    return {
        "chunk_id": chunk_id,
        "text": text,
        "chapter_title": "Глава 1",
        "chapter_number": 1,
        "source": "book",
    }


class TestEvidenceRepository:
    def test_add_and_get_round_trip(self, tmp_path: Path):
        repo = EvidenceRepository(data_dir=tmp_path)
        ev = Evidence.from_locator(
            source_id="book",
            source_type="book",
            locator="book:chunk:chunk_1",
            text="фрагмент книги",
        )
        repo.add(ev)
        loaded = repo.get(ev.id)
        assert loaded.id == ev.id
        assert loaded.locator == ev.locator
        assert loaded.content_hash == ev.content_hash

    def test_missing_evidence_raises(self, tmp_path: Path):
        repo = EvidenceRepository(data_dir=tmp_path)
        with pytest.raises(EvidenceNotFoundError):
            repo.get("evidence_missing")

    def test_find_returns_none_without_raising(self, tmp_path: Path):
        repo = EvidenceRepository(data_dir=tmp_path)
        assert repo.find("evidence_missing") is None

    def test_identical_add_is_idempotent(self, tmp_path: Path):
        repo = EvidenceRepository(data_dir=tmp_path)
        ev = Evidence.from_locator(
            source_id="book",
            source_type="book",
            locator="book:chunk:chunk_1",
            text="фрагмент книги",
        )
        repo.add(ev)
        repo.add(ev)
        assert repo.count() == 1

    def test_changing_content_creates_distinct_record(self, tmp_path: Path):
        repo = EvidenceRepository(data_dir=tmp_path)
        first = Evidence.from_locator(
            source_id="book",
            source_type="book",
            locator="book:chunk:chunk_1",
            text="версия один",
        )
        second = Evidence.from_locator(
            source_id="book",
            source_type="book",
            locator="book:chunk:chunk_1",
            text="версия два",
        )
        repo.add(first)
        repo.add(second)
        assert first.id != second.id
        assert repo.count() == 2

    def test_list_isolated_per_data_dir(self, tmp_path: Path):
        repo = EvidenceRepository(data_dir=tmp_path)
        assert repo.list() == []


class TestEvidenceResolver:
    def test_resolves_canonical_book_locator(self):
        source = BookChunkSource.from_retrieval_results([_book_chunk()])
        resolver = EvidenceResolver(chunk_source=source)
        result = resolver.resolve_locator(locator_for_chunk("chunk_1"))
        assert result.status is ResolutionStatus.RESOLVED
        assert result.evidence is not None
        assert result.evidence.locator == "chunk_1"

    def test_resolves_bare_known_chunk_id(self):
        source = BookChunkSource.from_retrieval_results([_book_chunk()])
        resolver = EvidenceResolver(chunk_source=source)
        result = resolver.resolve_locator("chunk_1")
        assert result.status is ResolutionStatus.RESOLVED

    def test_missing_chunk_is_unavailable_not_fabricated(self):
        resolver = EvidenceResolver(chunk_source=BookChunkSource())
        result = resolver.resolve_locator(locator_for_chunk("chunk_missing"))
        assert result.status is ResolutionStatus.UNAVAILABLE
        assert result.evidence is None
        assert "chunk" in result.reason

    def test_unsupported_locator_is_unknown(self):
        resolver = EvidenceResolver(chunk_source=BookChunkSource())
        result = resolver.resolve_locator("doi:10.1234/not-supported")
        assert result.status is ResolutionStatus.UNKNOWN
        assert result.evidence is None

    def test_empty_locator_is_unknown(self):
        resolver = EvidenceResolver(chunk_source=BookChunkSource())
        result = resolver.resolve_locator("   ")
        assert result.status is ResolutionStatus.UNKNOWN

    def test_unknown_and_unavailable_are_distinguished(self):
        resolver = EvidenceResolver(chunk_source=BookChunkSource())
        # An unsupported scheme (not book:/external:) is UNKNOWN.
        unknown = resolver.resolve_locator("doi:10.1234/not-supported")
        unavailable = resolver.resolve_locator(locator_for_chunk("chunk_missing"))
        assert unknown.status is ResolutionStatus.UNKNOWN
        assert unavailable.status is ResolutionStatus.UNAVAILABLE
        assert unknown.status is not unavailable.status

    def test_resolve_retrieval_hit_adapts_fragment(self):
        resolver = EvidenceResolver(chunk_source=BookChunkSource())
        hit = _book_chunk(chunk_id="chunk_99")
        result = resolver.resolve_retrieval_hit(hit)
        assert result.status is ResolutionStatus.RESOLVED
        assert result.evidence is not None
        assert result.evidence.locator == "chunk_99"

    def test_retrieval_hit_without_chunk_id_is_unknown(self):
        resolver = EvidenceResolver(chunk_source=BookChunkSource())
        result = resolver.resolve_retrieval_hit({"text": "no id"})
        assert result.status is ResolutionStatus.UNKNOWN

    def test_resolved_evidence_persists_via_repository(self, tmp_path: Path):
        source = BookChunkSource.from_retrieval_results([_book_chunk()])
        resolver = EvidenceResolver(chunk_source=source)
        repo = EvidenceRepository(data_dir=tmp_path)
        result = resolver.resolve_locator(locator_for_chunk("chunk_1"))
        assert result.resolved
        repo.add(result.evidence)
        assert repo.count() == 1
        assert repo.get(result.evidence.id).locator == "chunk_1"

    def test_prefix_constant_is_canonical(self):
        assert locator_for_chunk("chunk_1") == f"{BOOK_CHUNK_PREFIX}chunk_1"
