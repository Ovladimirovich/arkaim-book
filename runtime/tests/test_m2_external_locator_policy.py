"""M2 — External locator policy tests.

Covers the M2 STOP GATE decision that external sources are addressed through an
opaque, provider-owned namespace ``external:<source_id>:<locator>``. The
Knowledge Core does not parse DOI/URL/archive schemes; it only routes to a
registered provider and reports UNKNOWN/UNAVAILABLE explicitly.
"""

from __future__ import annotations

import sys
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from schemas.evidence import EvidenceStatus
from evidence.repository import ClaimEvidenceLinkRepository, EvidenceRepository
from evidence.resolver import (
    EXTERNAL_PREFIX,
    BookChunkSource,
    EvidenceResolver,
    ExternalLocatorSource,
    ResolutionStatus,
    locator_for_external,
)
from evidence.lifecycle import EvidenceLifecycle


class TestM2ExternalLocatorNamespace:
    def test_locator_for_external_is_opaque_namespace(self):
        loc = locator_for_external("archive_ru", "doc/123")
        assert loc == f"{EXTERNAL_PREFIX}archive_ru:doc/123"
        assert loc.startswith(EXTERNAL_PREFIX)

    def test_malformed_external_is_unknown(self):
        resolver = EvidenceResolver()
        for bad in ["external:", "external:onlyprovider", "external::x", "external:p:"]:
            result = resolver.resolve_locator(bad)
            assert result.status is ResolutionStatus.UNKNOWN, bad
            assert result.reason

    def test_absent_provider_fragment_is_unavailable_not_unknown(self):
        resolver = EvidenceResolver(external_source=ExternalLocatorSource(fragments={}))
        result = resolver.resolve_locator("external:archive_ru:doc/123")
        # Namespace is well-formed but fragment is not present -> checked UNAVAILABLE.
        assert result.status is ResolutionStatus.UNAVAILABLE
        assert "archive_ru" in result.reason

    def test_present_fragment_resolves_to_external_evidence(self):
        loc = "external:archive_ru:doc/123"
        resolver = EvidenceResolver(
            external_source=ExternalLocatorSource(
                fragments={loc: {"text": "фрагмент", "source_version": "v1"}}
            )
        )
        result = resolver.resolve_locator(loc)
        assert result.status is ResolutionStatus.RESOLVED
        assert result.evidence is not None
        assert result.evidence.source_type == "external"
        assert result.evidence.source_id == "archive_ru"
        assert result.evidence.locator == loc

    def test_provider_hash_adopted_when_no_text(self):
        loc = "external:archive_ru:doc/hashonly"
        resolver = EvidenceResolver(
            external_source=ExternalLocatorSource(
                fragments={loc: {"content_hash": "deadbeef", "source_version": "v2"}}
            )
        )
        result = resolver.resolve_locator(loc)
        assert result.status is ResolutionStatus.RESOLVED
        assert result.evidence.content_hash == "deadbeef"

    def test_unknown_scheme_still_unsupported(self):
        resolver = EvidenceResolver()
        # A raw DOI is not a supported namespace and must not be parsed ad hoc.
        result = resolver.resolve_locator("10.1000/xyz123")
        assert result.status is ResolutionStatus.UNKNOWN


class TestM2ExternalLifecycle:
    def _lifecycle(self, tmp_path: Path, fragments: dict) -> EvidenceLifecycle:
        resolver = EvidenceResolver(
            chunk_source=BookChunkSource(),
            external_source=ExternalLocatorSource(fragments=fragments),
        )
        return EvidenceLifecycle(
            resolver=resolver,
            link_repository=ClaimEvidenceLinkRepository(data_dir=tmp_path),
            evidence_repository=EvidenceRepository(data_dir=tmp_path),
        )

    def test_external_fragment_loss_becomes_unavailable_and_kept(self, tmp_path):
        loc = "external:archive_ru:doc/123"
        lifecycle = self._lifecycle(tmp_path, {loc: {"text": "фрагмент", "source_version": "v1"}})
        evidence = lifecycle.resolver.resolve_locator(loc).evidence
        link = lifecycle.bind(claim_id="claim_ext", evidence=evidence)
        assert link.status is EvidenceStatus.RESOLVED

        # Provider loses the fragment.
        lifecycle.resolver.external_source.fragments.pop(loc)
        result = lifecycle.check(link.link_id)

        assert result.status is EvidenceStatus.UNAVAILABLE
        # Record preserved with the original claim.
        persisted = lifecycle.links.get(link.link_id)
        assert persisted.claim_id == "claim_ext"
        assert persisted.status is EvidenceStatus.UNAVAILABLE

    def test_external_provider_version_change_supersedes(self, tmp_path):
        loc = "external:archive_ru:doc/123"
        lifecycle = self._lifecycle(
            tmp_path, {loc: {"text": "старая версия", "source_version": "v1"}}
        )
        evidence = lifecycle.resolver.resolve_locator(loc).evidence
        link = lifecycle.bind(claim_id="claim_ext", evidence=evidence)

        lifecycle.resolver.external_source.fragments[loc] = {
            "text": "новая версия",
            "source_version": "v2",
        }
        result = lifecycle.check(link.link_id)

        assert result.status is EvidenceStatus.SUPERSEDED
        assert result.new_link is not None
        assert result.new_link.supersedes_link_id == link.link_id
        assert len(lifecycle.links.for_claim("claim_ext")) == 2