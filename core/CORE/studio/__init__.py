"""Studio — Arkaim Studio v2 domain module.

Phase 1A: VideoScenario contract + VideoScenarioBuilder.
Phase 1B: Studio models + Store + API.
"""
from .scenario_schemas import (
    VideoScenario,
    ScenarioShot,
    ScenarioCharacterAction,
    ScenarioEnvironmentAction,
    ScenarioRhythm,
    ScenarioSoundDesign,
    ScenarioProvenance,
    SCENARIO_VERSION,
)
from .scenario_builder import VideoScenarioBuilder
from .session_models import (
    StudioSession, StudioSessionStatus,
    StudioMessage, StudioMessageRole,
    StudioVersion, UserModification,
    ReferenceAsset, StudioExport, ExportedReference,
)
from .store import StudioStore

__all__ = [
    "VideoScenario", "ScenarioShot", "ScenarioCharacterAction",
    "ScenarioEnvironmentAction", "ScenarioRhythm", "ScenarioSoundDesign",
    "ScenarioProvenance", "SCENARIO_VERSION",
    "VideoScenarioBuilder",
    "StudioSession", "StudioSessionStatus",
    "StudioMessage", "StudioMessageRole",
    "StudioVersion", "UserModification",
    "ReferenceAsset", "StudioExport", "ExportedReference",
    "StudioStore",
]
