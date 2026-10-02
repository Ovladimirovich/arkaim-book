"""M2 — Evidence Core integration package.

Thin boundary between the canonical ``Evidence`` model and the existing
Book OS / source infrastructure:

  * ``EvidenceRepository`` — persistence of Evidence records.
  * ``EvidenceResolver``  — resolution of book locators into Evidence.

This package deliberately keeps a narrow scope: it does not introduce a new
FactStore, does not modify WorldModel/Temporal/crosswalk, and does not
redefine claim semantics.
"""

from schemas.evidence import ClaimEvidenceLink, Evidence, EvidenceStatus
from evidence.repository import (
    ClaimEvidenceLinkNotFoundError,
    ClaimEvidenceLinkRepository,
    EvidenceNotFoundError,
    EvidenceRepository,
)
from evidence.resolver import (
    BOOK_CHUNK_PREFIX,
    EXTERNAL_PREFIX,
    BookChunkSource,
    EvidenceResolver,
    ExternalLocatorSource,
    ResolutionResult,
    ResolutionStatus,
    locator_for_chunk,
    locator_for_external,
)
from evidence.lifecycle import EvidenceLifecycle, LifecycleResult

__all__ = [
    "Evidence",
    "ClaimEvidenceLink",
    "EvidenceStatus",
    "EvidenceRepository",
    "EvidenceNotFoundError",
    "ClaimEvidenceLinkRepository",
    "ClaimEvidenceLinkNotFoundError",
    "EvidenceResolver",
    "BookChunkSource",
    "ExternalLocatorSource",
    "ResolutionResult",
    "ResolutionStatus",
    "locator_for_chunk",
    "locator_for_external",
    "BOOK_CHUNK_PREFIX",
    "EXTERNAL_PREFIX",
    "EvidenceLifecycle",
    "LifecycleResult",
]
