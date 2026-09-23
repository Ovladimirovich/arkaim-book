"""Narrative Engine — Движок повествования с ограничениями.

World Explorer: подсистема исследования мира.
"""

from narrative_engine.source_levels import SourceLevel, ProvenanceTag, SOURCE_LEVEL_WEIGHTS
from narrative_engine.world_model import WorldModel
from narrative_engine.canon_validator import CanonValidator, CanonCheckResult
from narrative_engine.world_state import WorldStateBuilder, WorldState
from narrative_engine.context_assembler import ContextAssembler, FullContext
from narrative_engine.planner import UnifiedPlanner, NarrativePlan

# World Explorer — Этап 1: Canon Engine + World Model
from narrative_engine.compatibility_checker import (
    CompatibilityChecker,
    CompatibilityReport,
    AxisScore,
    AxisViolation,
)
from narrative_engine.ability_model import AbilityModel, WorldPossibility

# World Explorer — Этап 2: Logic Engine
from narrative_engine.impact_assessor import (
    ImpactAssessor,
    ImpactReport,
    CharacterImpact,
    LocationImpact,
    CivilizationImpact,
    TimelineImpact,
    ValueImpact,
)
from narrative_engine.contradiction_detector import (
    ContradictionDetector,
    ContradictionReport,
    Contradiction,
)
from narrative_engine.world_delta import (
    WorldDeltaCalculator,
    WorldDelta,
    CharacterDelta,
    LocationDelta,
    CivilizationDelta,
    TimelineDelta,
    ValueDelta,
)

# World Explorer — Этап 3: Exploration Core
from narrative_engine.hypothesis_generator import (
    HypothesisGenerator,
    Hypothesis,
    HypothesisGraph,
    HypothesisType,
)
from narrative_engine.scenario_modeler import (
    ScenarioModeler,
    ScenarioTree,
    ScenarioBranch,
)
from narrative_engine.branch_manager import (
    BranchManager,
    ExplorationTree,
    BranchNode,
)

# World Explorer — Этап 4: Quality Evaluator
from narrative_engine.quality_evaluator import (
    QualityEvaluator,
    QualityReport,
    CriterionScore,
    CRITERIA_WEIGHTS,
)

# World Explorer — Этап 5: Integration
from narrative_engine.world_explorer import (
    WorldExplorer,
    ExplorationRequest,
    ExplorationResult,
    RankedBranch,
)

__all__ = [
    "SourceLevel", "ProvenanceTag", "SOURCE_LEVEL_WEIGHTS",
    "WorldModel",
    "CanonValidator", "CanonCheckResult",
    "WorldStateBuilder", "WorldState",
    "ContextAssembler", "FullContext",
    "UnifiedPlanner", "NarrativePlan",
    # World Explorer — Этап 1
    "CompatibilityChecker", "CompatibilityReport",
    "AxisScore", "AxisViolation",
    "AbilityModel", "WorldPossibility",
    # World Explorer — Этап 2
    "ImpactAssessor", "ImpactReport",
    "CharacterImpact", "LocationImpact", "CivilizationImpact",
    "TimelineImpact", "ValueImpact",
    "ContradictionDetector", "ContradictionReport", "Contradiction",
    "WorldDeltaCalculator", "WorldDelta",
    "CharacterDelta", "LocationDelta", "CivilizationDelta",
    "TimelineDelta", "ValueDelta",
    # World Explorer — Этап 3
    "HypothesisGenerator", "Hypothesis", "HypothesisGraph", "HypothesisType",
    "ScenarioModeler", "ScenarioTree", "ScenarioBranch",
    "BranchManager", "ExplorationTree", "BranchNode",
    # World Explorer — Этап 4
    "QualityEvaluator", "QualityReport", "CriterionScore", "CRITERIA_WEIGHTS",
    # World Explorer — Этап 5
    "WorldExplorer", "ExplorationRequest", "ExplorationResult", "RankedBranch",
]
