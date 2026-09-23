"""Provenance package — категория происхождения и трассировка фактов.

M1 foundation:
  - ProvenanceCategory: семантическая категория (author canon / external / hypothesis / ...)
  - ProvenanceRegistry: единый реестр всех provenance тегов
  - CanonClaim: атомарное утверждение с трассировкой до источника
  - SourceHierarchy: иерархия авторских источников с приоритетами
"""

from __future__ import annotations

from narrative_engine.source_levels import (
    ProvenanceCategory,
    ProvenanceTag,
    SourceLevel,
)

__all__ = [
    "ProvenanceCategory",
    "ProvenanceTag",
    "SourceLevel",
    "ProvenanceRegistry",
    "CanonClaim",
    "SourceHierarchy",
    "canonical_provenance",
    "external_provenance",
    "hypothesis_provenance",
    "derived_provenance",
]
