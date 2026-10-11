"""M2 — Evidence broken/missing reference lifecycle tests."""

from __future__ import annotations

import sys
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

import pytest

from schemas.evidence import ClaimEvidenceLink, Evidence, EvidenceStatus
from evidence.repository import ClaimEvidenceLinkRepository, EvidenceRepository
from evidence.resolver import BookChunkSource, EvidenceResolver
from evidence.lifecycle import EvidenceLifecycle


def _make_lifecycle(tmp_path: Path, chunks: dict) -> EvidenceLifecycle:
    source = BookChunkSource(chunks=chunks)
    resolver = EvidenceResolver(chunk_source=source)
    return EvidenceLifecycle(
        resolver=resolver,
        link_repository=ClaimEvidenceLinkRepository(data_dir=tmp_path),
        evidence_repository=EvidenceRepository(data_dir=tmp_path),
    )


class TestM2LifecycleStatuses:
    def test_unknown_is_distinct_from_unavailable(self, tmp_path):
        lifecycle = _make_lifecycle(tmp_path, chunks={})
        evidence = Evidence.from_locator(
            source_id="book",
            source_type="book",
            locator="doi:10.1",
            text=None,
        )
        link = lifecycle.bind(claim_id="claim_a", evidence=evidence)
        # Unsupported locator format -> UNKNOWN (not UNAVAILABLE).
        result = lifecycle.check(link.link_id)
        assert result.status is EvidenceStatus.UNKNOWN
        assert result.link.status is EvidenceStatus.UNKNOWN

    def test_missing_fragment_becomes_unavailable_and_is_kept(self, tmp_path):
        chunks = {"chunk_1": {"chunk_id": "chunk_1", "text": "текст", "source": "book"}}
        lifecycle = _make_lifecycle(tmp_path, chunks=chunks)
        evidence = Evidence.from_chunk(chunks["chunk_1"], source_id="book")
        link = lifecycle.bind(claim_id="claim_a", evidence=evidence)
        assert link.status is EvidenceStatus.RESOLVED

        # Fragment disappears from source.
        lifecycle.resolver.chunk_source.chunks.pop("chunk_1")
        result = lifecycle.check(link.link_id)

        assert result.status is EvidenceStatus.UNAVAILABLE
        assert result.changed is True
        # Record still exists (never deleted) with original claim link.
        persisted = lifecycle.links.get(link.link_id)
        assert persisted.status is EvidenceStatus.UNAVAILABLE
        assert persisted.claim_id == "claim_a"
        assert result.reason


class TestM2LifecycleRestore:
    def test_restore_returns_to_resolved_when_content_matches(self, tmp_path):
        original = {"chunk_id": "chunk_1", "text": "текст", "source": "book"}
        lifecycle = _make_lifecycle(tmp_path, chunks={"chunk_1": dict(original)})
        evidence = Evidence.from_chunk(original, source_id="book")
        link = lifecycle.bind(claim_id="claim_a", evidence=evidence)

        lifecycle.resolver.chunk_source.chunks.pop("chunk_1")
        lifecycle.check(link.link_id)

        # Fragment reappears with identical content (same id/hash).
        lifecycle.resolver.chunk_source.chunks["chunk_1"] = dict(original)
        result = lifecycle.restore(link.link_id)

        assert result.status is EvidenceStatus.RESOLVED
        assert result.link.status is EvidenceStatus.RESOLVED
        assert result.changed is True

    def test_restore_stays_unavailable_when_still_missing(self, tmp_path):
        original = {"chunk_id": "chunk_1", "text": "текст", "source": "book"}
        lifecycle = _make_lifecycle(tmp_path, chunks={"chunk_1": dict(original)})
        evidence = Evidence.from_chunk(original, source_id="book")
        link = lifecycle.bind(claim_id="claim_a", evidence=evidence)

        lifecycle.resolver.chunk_source.chunks.pop("chunk_1")
        lifecycle.check(link.link_id)
        result = lifecycle.restore(link.link_id)

        assert result.status is EvidenceStatus.UNAVAILABLE
        assert result.changed is False


class TestM2LifecycleSupersede:
    def test_changed_content_supersedes_and_creates_new_version(self, tmp_path):
        chunks = {"chunk_1": {"chunk_id": "chunk_1", "text": "старый текст", "source": "book"}}
        lifecycle = _make_lifecycle(tmp_path, chunks=chunks)
        evidence = Evidence.from_chunk(chunks["chunk_1"], source_id="book")
        link = lifecycle.bind(claim_id="claim_a", evidence=evidence)
        assert link.status is EvidenceStatus.RESOLVED

        # Fragment changes content.
        lifecycle.resolver.chunk_source.chunks["chunk_1"] = {
            "chunk_id": "chunk_1",
            "text": "новый текст",
            "source": "book",
        }
        result = lifecycle.check(link.link_id)

        assert result.status is EvidenceStatus.SUPERSEDED
        assert result.new_link is not None
        assert result.new_link.status is EvidenceStatus.RESOLVED
        assert result.new_link.supersedes_link_id == link.link_id
        # Old link is kept as history.
        old = lifecycle.links.get(link.link_id)
        assert old.status is EvidenceStatus.SUPERSEDED
        # Both links exist for the claim.
        assert len(lifecycle.links.for_claim("claim_a")) == 2

    def test_restore_with_changed_content_supersedes_not_restores(self, tmp_path):
        chunks = {"chunk_1": {"chunk_id": "chunk_1", "text": "старый текст", "source": "book"}}
        lifecycle = _make_lifecycle(tmp_path, chunks=chunks)
        evidence = Evidence.from_chunk(chunks["chunk_1"], source_id="book")
        link = lifecycle.bind(claim_id="claim_a", evidence=evidence)

        lifecycle.resolver.chunk_source.chunks.pop("chunk_1")
        lifecycle.check(link.link_id)

        lifecycle.resolver.chunk_source.chunks["chunk_1"] = {
            "chunk_id": "chunk_1",
            "text": "совсем другой текст",
            "source": "book",
        }
        result = lifecycle.restore(link.link_id)

        assert result.status is EvidenceStatus.SUPERSEDED
        assert result.new_link is not None


class TestM2LifecyclePersistence:
    def test_link_repository_persists_and_lists(self, tmp_path):
        repo = ClaimEvidenceLinkRepository(data_dir=tmp_path)
        link = ClaimEvidenceLink(claim_id="claim_x", evidence_id="evidence_y")
        assert link.link_id  # auto-generated
        repo.add(link)
        fetched = repo.get(link.link_id)
        assert fetched.claim_id == "claim_x"
        assert len(repo.for_claim("claim_x")) == 1

    def test_mark_status_preserves_record(self, tmp_path):
        repo = ClaimEvidenceLinkRepository(data_dir=tmp_path)
        link = repo.add(ClaimEvidenceLink(claim_id="claim_x", evidence_id="evidence_y"))
        updated = repo.mark_status(link.link_id, EvidenceStatus.UNAVAILABLE, reason="gone")
        assert updated.status is EvidenceStatus.UNAVAILABLE
        assert updated.reason == "gone"
        assert updated.checked_at is not None
        assert repo.get(link.link_id).status is EvidenceStatus.UNAVAILABLE
