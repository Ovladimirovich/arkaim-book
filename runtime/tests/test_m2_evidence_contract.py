"""M2 — Evidence/source-fragment contract tests."""

from __future__ import annotations

import sys
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

import pytest

from schemas.evidence import ClaimEvidenceLink, Evidence


class TestM2EvidenceIdentity:
    def test_stable_id_for_same_source_and_locator(self):
        first = Evidence.from_locator(
            source_id="book",
            source_type="book",
            locator="chapter:1 paragraph:5",
            text="Аркаим — древнее городище.",
        )
        second = Evidence.from_locator(
            source_id="book",
            source_type="book",
            locator="chapter:1 paragraph:5",
            text="Аркаим — древнее городище.",
        )
        assert first.id == second.id

    def test_different_locator_produces_different_evidence(self):
        a = Evidence.from_locator(source_id="book", source_type="book", locator="chapter:1")
        b = Evidence.from_locator(source_id="book", source_type="book", locator="chapter:2")
        assert a.id != b.id

    def test_content_hash_recorded_when_text_present(self):
        ev = Evidence.from_locator(
            source_id="book",
            source_type="book",
            locator="chapter:1",
            text="текст",
        )
        assert ev.content_hash is not None
        assert len(ev.content_hash) == 64

    def test_missing_text_leaves_unknown_hash(self):
        ev = Evidence.from_locator(source_id="book", source_type="book", locator="chapter:1")
        assert ev.content_hash is None
        assert ev.text is None


class TestM2EvidenceFromChunk:
    def test_chunk_adapts_without_changing_retrieval_semantics(self):
        chunk = {
            "chunk_id": "chunk_42",
            "text": "фрагмент книги",
            "chapter_title": "Глава 1",
            "chapter_number": 1,
            "source": "book",
        }
        ev = Evidence.from_chunk(chunk)
        assert ev.locator == "chunk_42"
        assert ev.source_type == "book"
        assert ev.metadata["chapter_title"] == "Глава 1"
        assert ev.metadata["chapter_number"] == 1

    def test_chunk_without_locator_is_rejected(self):
        with pytest.raises(ValueError):
            Evidence.from_chunk({"text": "no locator here"}, source_id="book")

    def test_empty_locator_rejected(self):
        with pytest.raises(ValueError):
            Evidence.from_locator(source_id="book", source_type="book", locator="   ")


class TestM2ClaimEvidenceLink:
    def test_link_binds_claim_to_evidence(self):
        link = ClaimEvidenceLink(claim_id="claim_abc", evidence_id="evidence_xyz")
        assert link.relation == "supports"
        assert link.claim_id == "claim_abc"
        assert link.evidence_id == "evidence_xyz"

    def test_link_requires_non_empty_ids(self):
        with pytest.raises(ValueError):
            ClaimEvidenceLink(claim_id="", evidence_id="evidence_xyz")
        with pytest.raises(ValueError):
            ClaimEvidenceLink(claim_id="claim_abc", evidence_id="")

    def test_one_evidence_can_back_many_claims(self):
        ev = Evidence.from_locator(source_id="book", source_type="book", locator="chapter:1")
        link_a = ClaimEvidenceLink(claim_id="claim_a", evidence_id=ev.id)
        link_b = ClaimEvidenceLink(claim_id="claim_b", evidence_id=ev.id)
        assert link_a.evidence_id == link_b.evidence_id == ev.id
        assert link_a.claim_id != link_b.claim_id

    def test_claim_may_reference_multiple_evidence(self):
        ev1 = Evidence.from_locator(source_id="book", source_type="book", locator="chapter:1")
        ev2 = Evidence.from_locator(source_id="archaeology", source_type="external", locator="doi:10.1")
        links = [
            ClaimEvidenceLink(claim_id="claim_a", evidence_id=ev1.id),
            ClaimEvidenceLink(claim_id="claim_a", evidence_id=ev2.id),
        ]
        assert {link.evidence_id for link in links} == {ev1.id, ev2.id}