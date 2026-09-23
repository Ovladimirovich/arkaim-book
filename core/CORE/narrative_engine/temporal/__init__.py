"""Temporal package — обновлённый __init__.py с M3."""

from __future__ import annotations

from narrative_engine.temporal.precision import TemporalPrecision
from narrative_engine.temporal.node import TemporalNode
from narrative_engine.temporal.relation import TemporalRelationType, TemporalRelation
from narrative_engine.temporal.chain import TemporalChain, ChainDirection
from narrative_engine.temporal.gap import TemporalGap, EvidenceStatus
from narrative_engine.temporal.reconstruction_path import ReconstructionPath
from narrative_engine.temporal.present_anchor import PresentAnchor
from narrative_engine.temporal.arkaim_anchor import ArkaimAnchor
from narrative_engine.temporal.graph import TemporalGraph
from narrative_engine.temporal.path_validator import PathValidator, PathValidationResult
from narrative_engine.temporal.reconstruction_engine import (
    TemporalReconstructionEngine,
    ReconstructionResult,
)

__all__ = [
    # M2
    "TemporalPrecision",
    "TemporalNode",
    "TemporalRelationType",
    "TemporalRelation",
    "TemporalChain",
    "ChainDirection",
    "TemporalGap",
    "EvidenceStatus",
    "ReconstructionPath",
    "PresentAnchor",
    "ArkaimAnchor",
    # M3
    "TemporalGraph",
    "PathValidator",
    "PathValidationResult",
    "TemporalReconstructionEngine",
    "ReconstructionResult",
]
