"""Очередь проверки кандидатов LLM (Q1: индекс, Q2: решения).

Очередь — это представление, а не хранилище: статус проверки живёт в самой
записи знания (``_provenance_metadata.status``), а индекс каждый раз строится
сканированием файлов. Так у гейтов 6d/6e остаётся один источник истины.

Экспорт:
    CandidateRecord, scan_candidates, find_candidate, filter_candidates,
    candidate_stats, KNOWN_STATUSES
    decide, ReviewError и его подклассы, iter_decisions
"""

from __future__ import annotations

from .candidates import (
    KNOWN_STATUSES,
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    CandidateRecord,
    candidate_stats,
    filter_candidates,
    find_candidate,
    scan_candidates,
)
from .service import (
    CandidateNotFound,
    InvalidTransition,
    PermissionDenied,
    ReviewError,
    StaleCandidate,
    ValidationError,
    decide,
    iter_decisions,
)

__all__ = [
    "KNOWN_STATUSES",
    "STATUS_APPROVED",
    "STATUS_PENDING",
    "STATUS_REJECTED",
    "CandidateNotFound",
    "CandidateRecord",
    "InvalidTransition",
    "PermissionDenied",
    "ReviewError",
    "StaleCandidate",
    "ValidationError",
    "candidate_stats",
    "decide",
    "filter_candidates",
    "find_candidate",
    "iter_decisions",
    "scan_candidates",
]
