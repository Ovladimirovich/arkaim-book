"""M2 — Evidence resolver.

Resolution boundary between the Knowledge Core Evidence model and the existing
Book OS / source infrastructure. The resolver answers a single question:

    given a book locator (canonical chunk_id or a raw chunk/retrieval dict),
    can we produce a valid ``Evidence`` record, and if not, why?

Policy (M2 STOP GATE):
  * Officially supported locators in this scope:
      - ``book:chunk:<chunk_id>``
      - a book catalog entry exposing an existing ``chunk_id``/``id``.
      - ``external:<source_id>:<locator>`` — provider-owned, versioned and
        opaque. The Knowledge Core does not parse DOI/URL/archive schemes; the
        trailing locator is resolved only through the registered provider.
  * Unsupported locator formats (no known namespace) resolve to UNKNOWN.
  * The resolver never fabricates Evidence for a missing fragment. It returns
    an explicit status and reason instead.

This module does not perform broken-reference persistence migrations and does
not touch WorldModel, Temporal or crosswalk.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from schemas.evidence import Evidence

BOOK_CHUNK_PREFIX = "book:chunk:"
EXTERNAL_PREFIX = "external:"


class ExternalLocatorSource:
    """Minimal provider-owned storage for external locator fragments.

    External sources are addressed by an opaque, versioned namespace
    ``external:<source_id>:<locator>``. The Knowledge Core treats the trailing
    ``<locator>`` as provider-owned and opaque: it does not parse DOI/URL/archive
    schemes itself. If a provider cannot present the fragment, the resolver
    reports UNAVAILABLE (checked) or UNKNOWN (unsupported) — it never fabricates
    evidence.
    """

    def __init__(self, fragments: Optional[dict[str, dict]] = None):
        # Maps the full external locator string to a fragment dict with optional
        # keys: text, source_version, content_hash.
        self.fragments: dict[str, dict] = fragments or {}

    def get_fragment(self, locator: str) -> Optional[dict]:
        return self.fragments.get(locator)


class ResolutionStatus(str, Enum):
    """Outcome of an evidence resolution attempt."""

    RESOLVED = "RESOLVED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


@dataclass
class ResolutionResult:
    """Typed result of resolving a locator into Evidence."""

    status: ResolutionStatus
    evidence: Optional[Evidence] = None
    reason: str = ""
    locator: str = ""

    @property
    def resolved(self) -> bool:
        return self.status is ResolutionStatus.RESOLVED


@dataclass
class BookChunkSource:
    """Minimal read interface over the existing book chunk/catalog data.

    The resolver depends on this interface, not on Chroma or the filesystem,
    so it stays compatible with the current Book Intelligence pipeline.
    """

    chunks: dict[str, dict] = field(default_factory=dict)

    def get_chunk(self, chunk_id: str) -> Optional[dict]:
        return self.chunks.get(chunk_id)

    @classmethod
    def from_retrieval_results(cls, results: list[dict]) -> "BookChunkSource":
        chunks: dict[str, dict] = {}
        for item in results:
            chunk_id = str(item.get("chunk_id") or (item.get("metadata") or {}).get("id") or "")
            if chunk_id:
                chunks[chunk_id] = item
        return cls(chunks=chunks)


class EvidenceResolver:
    """Resolve book locators into Evidence records against a chunk source."""

    def __init__(
        self,
        chunk_source: Optional[BookChunkSource] = None,
        external_source: Optional[ExternalLocatorSource] = None,
    ):
        self.chunk_source = chunk_source or BookChunkSource()
        self.external_source = external_source or ExternalLocatorSource()

    def resolve_locator(self, locator: str, *, source_id: str = "book") -> ResolutionResult:
        """Resolve a canonical locator string into Evidence."""
        locator = (locator or "").strip()
        if not locator:
            return ResolutionResult(
                status=ResolutionStatus.UNKNOWN,
                reason="empty locator",
                locator=locator,
            )

        if locator.startswith(BOOK_CHUNK_PREFIX):
            chunk_id = locator[len(BOOK_CHUNK_PREFIX):]
            return self.resolve_chunk_id(chunk_id, source_id=source_id)

        if locator.startswith(EXTERNAL_PREFIX):
            return self.resolve_external(locator)

        # A bare chunk id is only accepted when it exists in the known source.
        if self.chunk_source.get_chunk(locator) is not None:
            return self.resolve_chunk_id(locator, source_id=source_id)

        return ResolutionResult(
            status=ResolutionStatus.UNKNOWN,
            reason=f"unsupported locator format: {locator}",
            locator=locator,
        )

    def resolve_chunk_id(self, chunk_id: str, *, source_id: str = "book") -> ResolutionResult:
        """Resolve an existing book chunk id into Evidence."""
        chunk_id = (chunk_id or "").strip()
        locator = f"{BOOK_CHUNK_PREFIX}{chunk_id}" if chunk_id else ""
        if not chunk_id:
            return ResolutionResult(
                status=ResolutionStatus.UNKNOWN,
                reason="empty chunk_id",
                locator=locator,
            )

        chunk = self.chunk_source.get_chunk(chunk_id)
        if chunk is None:
            return ResolutionResult(
                status=ResolutionStatus.UNAVAILABLE,
                reason=f"chunk not found in source: {chunk_id}",
                locator=locator,
            )

        try:
            evidence = Evidence.from_chunk(chunk, source_id=source_id)
        except ValueError as exc:
            return ResolutionResult(
                status=ResolutionStatus.UNAVAILABLE,
                reason=str(exc),
                locator=locator,
            )

        return ResolutionResult(
            status=ResolutionStatus.RESOLVED,
            evidence=evidence,
            reason="",
            locator=locator,
        )

    def resolve_retrieval_hit(self, hit: dict, *, source_id: str = "book") -> ResolutionResult:
        """Resolve a RAG retrieval hit.

        A retrieval hit is not automatically an Evidence claim: this method
        only adapts the *fragment* into an Evidence record with a resolvable
        locator. The assertion/extraction step remains explicit and external.
        """
        chunk_id = str(hit.get("chunk_id") or (hit.get("metadata") or {}).get("id") or "")
        if not chunk_id:
            return ResolutionResult(
                status=ResolutionStatus.UNKNOWN,
                reason="retrieval hit has no chunk_id",
                locator="",
            )
        if self.chunk_source.get_chunk(chunk_id) is None:
            self.chunk_source.chunks[chunk_id] = hit
        return self.resolve_chunk_id(chunk_id, source_id=source_id)


    def resolve_external(self, locator: str) -> ResolutionResult:
        """Resolve a provider-owned ``external:<source_id>:<locator>`` reference.

        The namespace is the only contract here; the trailing locator is opaque.
        A namespace without a registered provider/fragment is UNKNOWN; a known
        namespace whose fragment is absent is UNAVAILABLE.
        """
        body = locator[len(EXTERNAL_PREFIX):]
        source_id, sep, rest = body.partition(":")
        if not source_id or not sep or not rest.strip():
            return ResolutionResult(
                status=ResolutionStatus.UNKNOWN,
                reason=f"malformed external locator (expected external:<source_id>:<locator>): {locator}",
                locator=locator,
            )

        fragment = self.external_source.get_fragment(locator)
        if fragment is None:
            return ResolutionResult(
                status=ResolutionStatus.UNAVAILABLE,
                reason=f"external fragment not available for provider: {source_id}",
                locator=locator,
            )

        try:
            evidence = Evidence.from_locator(
                source_id=source_id,
                source_type="external",
                locator=locator,
                text=fragment.get("text"),
                source_version=fragment.get("source_version"),
                metadata={"external_locator": rest},
            )
        except ValueError as exc:
            return ResolutionResult(
                status=ResolutionStatus.UNAVAILABLE,
                reason=str(exc),
                locator=locator,
            )

        if fragment.get("content_hash") and evidence.content_hash is None:
            # Provider supplied a hash but no text; adopt provider hash so lifecycle
            # version checks stay possible without fabricating text.
            evidence = evidence.model_copy(update={"content_hash": fragment["content_hash"]})

        return ResolutionResult(
            status=ResolutionStatus.RESOLVED,
            evidence=evidence,
            reason="",
            locator=locator,
        )


def locator_for_chunk(chunk_id: str) -> str:
    """Return the canonical book locator for a chunk id."""
    return f"{BOOK_CHUNK_PREFIX}{chunk_id}"


def locator_for_external(source_id: str, locator: str) -> str:
    """Return the canonical external locator for a provider-owned reference."""
    return f"{EXTERNAL_PREFIX}{source_id}:{locator}"


__all__ = [
    "EvidenceResolver",
    "BookChunkSource",
    "ExternalLocatorSource",
    "ResolutionResult",
    "ResolutionStatus",
    "locator_for_chunk",
    "locator_for_external",
    "BOOK_CHUNK_PREFIX",
    "EXTERNAL_PREFIX",
]
