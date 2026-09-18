"""MediaPlan v0 — доменный контракт задания на генерацию (MD-3).

ADR_MEDIA_PLAN_V0:
  schemas  — MediaPlan + lineage/provenance-наследование (домен);
  builder  — MediaPlanBuilder: проекция SceneContext → план.

MediaPlan НЕ содержит execution-семантики (model/steps/seed/cfg/
provider/backend/…) — инвариант проверяется тестом (BANNED_FIELDS).

NOTE (MD-5): ExecutionDispatch removed; legacy prompt projection lives
in route-level local variables, not in the plan.
"""
from .schemas import (
    BANNED_FIELDS,
    PLAN_VERSION,
    CameraPlan,
    CharacterPlan,
    ContinuityRef,
    LocationRef,
    MediaKind,
    MediaPlan,
    MotionPlan,
    PlanLineage,
    ShotPlan,
    verify_no_execution_fields,
)
from .builder import MediaPlanBuilder

__all__ = [
    "BANNED_FIELDS",
    "PLAN_VERSION",
    "CameraPlan",
    "CharacterPlan",
    "ContinuityRef",
    "LocationRef",
    "MediaKind",
    "MediaPlan",
    "MotionPlan",
    "PlanLineage",
    "ShotPlan",
    "verify_no_execution_fields",
    "MediaPlanBuilder",
]