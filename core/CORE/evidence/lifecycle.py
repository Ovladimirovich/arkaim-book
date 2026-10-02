"""M2 — Evidence reference lifecycle.

Governs how a claim→evidence link behaves when the referenced fragment breaks,
changes or comes back. Implements the M2 STOP GATE policy:

  * records are never deleted on breakage;
  * a broken reference becomes ``UNAVAILABLE`` (checked) with a reason;
  * a reference that cannot be verified is ``UNKNOWN``;
  * when the fragment content changed so that the old hash/version no longer
    matches, the old link becomes ``SUPERSEDED`` and a new link version is
    created pointing at the new evidence;
  * a link returns to ``RESOLVED`` only when the fragment hash/version matches
    again.

This module does not touch WorldModel, Temporal or crosswalk, and it does not
fabricate evidence for a missing fragment.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from schemas.evidence import ClaimEvidenceLink, Evidence, EvidenceStatus
from evidence.repository import ClaimEvidenceLinkRepository, EvidenceRepository
from evidence.resolver import (
    BOOK_CHUNK_PREFIX,
    EvidenceResolver,
    ResolutionStatus,
    locator_for_chunk,
)


def canonicalize_locator(locator: str) -> str:
    """Normalize a stored locator so lifecycle resolution stays deterministic.

    A bare chunk id (no namespace/scheme, e.g. ``chunk_1``) becomes the
    canonical ``book:chunk:<id>`` form, so a later missing chunk resolves to
    ``UNAVAILABLE`` (checked) instead of ``UNKNOWN`` (unsupported format).
    Namespaced or external locators (containing ``:``) are kept verbatim.
    """
    locator = (locator or "").strip()
    if not locator:
        return locator
    if locator.startswith(BOOK_CHUNK_PREFIX) or ":" in locator:
        return locator
    return locator_for_chunk(locator)


@dataclass
class LifecycleResult:
    """Outcome of a lifecycle check/transition for one link."""

    link: ClaimEvidenceLink
    status: EvidenceStatus
    changed: bool
    reason: str = ""
    new_link: Optional[ClaimEvidenceLink] = None


class EvidenceLifecycle:
    """Applies and persists reference lifecycle transitions.

    The lifecycle is the single place that decides whether a reference is
    ``RESOLVED``, ``UNAVAILABLE``, ``UNKNOWN`` or ``SUPERSEDED``. A claim never
    loses provenance: only the link status changes, and history is preserved.
    """

    def __init__(
        self,
        *,
        resolver: Optional[EvidenceResolver] = None,
        link_repository: Optional[ClaimEvidenceLinkRepository] = None,
        evidence_repository: Optional[EvidenceRepository] = None,
    ):
        self.resolver = resolver or EvidenceResolver()
        self.links = link_repository or ClaimEvidenceLinkRepository()
        self.evidence = evidence_repository or EvidenceRepository()

    @staticmethod
    def _now() -> datetime:
        return datetime.now(tz=timezone.utc)

    def bind(
        self,
        *,
        claim_id: str,
        evidence: Evidence,
        relation: str = "supports",
        notes: str = "",
    ) -> ClaimEvidenceLink:
        """Create and persist a RESOLVED link, capturing the expected hash."""
        link = ClaimEvidenceLink(
            claim_id=claim_id,
            evidence_id=evidence.id,
            relation=relation,
            notes=notes,
            status=EvidenceStatus.RESOLVED,
            source_id=evidence.source_id,
            locator=canonicalize_locator(evidence.locator),
            expected_content_hash=evidence.content_hash,
            expected_source_version=evidence.source_version,
            checked_at=self._now(),
        )
        self.evidence.add(evidence)
        return self.links.add(link)

    def check(self, link_id: str) -> LifecycleResult:
        """Re-resolve a link against the current source and update its status.

        Transitions:
          * matches expected hash/version            -> RESOLVED
          * fragment missing (checked)               -> UNAVAILABLE
          * fragment present but content changed      -> SUPERSEDED + new link
          * locator not verifiable in this scope      -> UNKNOWN
        """
        link = self.links.get(link_id)
        result = self.resolver.resolve_locator(link.locator, source_id=link.source_id or "book")

        if result.status is ResolutionStatus.UNKNOWN:
            return self._transition(link, EvidenceStatus.UNKNOWN, result.reason)

        if result.status is ResolutionStatus.UNAVAILABLE:
            return self._transition(link, EvidenceStatus.UNAVAILABLE, result.reason)

        # RESOLVED from the resolver: verify hash/version stability.
        new_evidence = result.evidence
        assert new_evidence is not None  # resolver guarantees evidence on RESOLVED

        if self._unchanged(link, new_evidence):
            return self._transition(link, EvidenceStatus.RESOLVED, "")

        # Content changed: keep old link as SUPERSEDED, create a new version.
        self.links.mark_status(
            link.link_id,
            EvidenceStatus.SUPERSEDED,
            reason="referenced fragment content changed; superseded by newer version",
        )
        superseded = self.links.get(link.link_id)

        new_link = ClaimEvidenceLink(
            claim_id=link.claim_id,
            evidence_id=new_evidence.id,
            relation=link.relation,
            notes=link.notes,
            status=EvidenceStatus.RESOLVED,
            source_id=new_evidence.source_id,
            locator=canonicalize_locator(new_evidence.locator),
            expected_content_hash=new_evidence.content_hash,
            expected_source_version=new_evidence.source_version,
            supersedes_link_id=superseded.link_id,
            checked_at=self._now(),
        )
        self.evidence.add(new_evidence)
        self.links.add(new_link)

        return LifecycleResult(
            link=superseded,
            status=EvidenceStatus.SUPERSEDED,
            changed=True,
            reason="referenced fragment changed; new link version created",
            new_link=new_link,
        )

    def restore(self, link_id: str) -> LifecycleResult:
        """Attempt to bring an UNAVAILABLE/UNKNOWN link back to RESOLVED.

        Restoration succeeds only when the fragment is reachable and its
        hash/version matches the expected values. Otherwise the link stays in
        its non-resolved state and the reason is updated.
        """
        link = self.links.get(link_id)
        result = self.resolver.resolve_locator(link.locator, source_id=link.source_id or "book")

        if result.status is not ResolutionStatus.RESOLVED or result.evidence is None:
            reason = result.reason or "fragment still not reachable"
            return self._transition(link, EvidenceStatus.UNAVAILABLE, reason)

        if not self._unchanged(link, result.evidence):
            # Reappeared but content differs: treat as superseded, not restored.
            self.links.mark_status(
                link.link_id,
                EvidenceStatus.SUPERSEDED,
                reason="fragment reappeared with different content; not restored",
            )
            superseded = self.links.get(link.link_id)
            new_link = ClaimEvidenceLink(
                claim_id=link.claim_id,
                evidence_id=result.evidence.id,
                relation=link.relation,
                notes=link.notes,
                status=EvidenceStatus.RESOLVED,
                source_id=result.evidence.source_id,
                locator=canonicalize_locator(result.evidence.locator),
                expected_content_hash=result.evidence.content_hash,
                expected_source_version=result.evidence.source_version,
                supersedes_link_id=superseded.link_id,
                checked_at=self._now(),
            )
            self.evidence.add(result.evidence)
            self.links.add(new_link)
            return LifecycleResult(
                link=superseded,
                status=EvidenceStatus.SUPERSEDED,
                changed=True,
                reason="fragment reappeared with different content; new version created",
                new_link=new_link,
            )

        self.evidence.add(result.evidence)
        return self._transition(link, EvidenceStatus.RESOLVED, "")

    def _transition(self, link: ClaimEvidenceLink, status: EvidenceStatus, reason: str) -> LifecycleResult:
        changed = link.status is not status or (bool(reason) and reason != link.reason)
        updated = self.links.mark_status(link.link_id, status, reason=reason) if changed else link
        return LifecycleResult(link=updated, status=status, changed=changed, reason=reason)

    @staticmethod
    def _unchanged(link: ClaimEvidenceLink, evidence: Evidence) -> bool:
        """A link is unchanged when expected hash/version still match.

        If the link never recorded an expected hash/version, a reachable
        fragment is accepted as still valid (cannot disprove it), which keeps
        legacy links usable without fabricating a change.
        """
        if link.expected_content_hash is not None and evidence.content_hash is not None:
            return link.expected_content_hash == evidence.content_hash
        if link.expected_source_version is not None and evidence.source_version is not None:
            return link.expected_source_version == evidence.source_version
        return True


__all__ = ["EvidenceLifecycle", "LifecycleResult", "canonicalize_locator"]
