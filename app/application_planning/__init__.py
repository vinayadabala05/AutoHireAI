"""Application Planning Engine.

The decision-making layer between Job Discovery (Sprint 7) and future
Browser Automation: scores a `DiscoveredJob` against a `CareerProfile` +
`ResumeBlueprint` (Sprint 3), decides APPLY/SKIP with a priority, and — for
jobs worth applying to — builds a tailored resume + cover letter via
Sprint 5/6 through Sprint 8's Graph Orchestration Engine.
`ApplicationPlanningService` is the single entrypoint callers should use.
"""

from app.application_planning.decision import DecisionEngine, DecisionThresholds
from app.application_planning.exceptions import (
    ApplicationPlanningError,
    PackageBuildError,
    PlanningConfigurationError,
)
from app.application_planning.models import (
    ApplicationDecision,
    ApplicationPackage,
    ApplicationPlan,
    ApplicationPriority,
    EvaluatedJob,
    MatchEvaluation,
)
from app.application_planning.package_builder import ApplicationPackageBuilder
from app.application_planning.planner import ApplicationPlanner
from app.application_planning.scorer import JobMatchScorer
from app.application_planning.service import ApplicationPlanningService

__all__ = [
    "ApplicationDecision",
    "ApplicationPackage",
    "ApplicationPackageBuilder",
    "ApplicationPlan",
    "ApplicationPlanner",
    "ApplicationPlanningError",
    "ApplicationPlanningService",
    "ApplicationPriority",
    "DecisionEngine",
    "DecisionThresholds",
    "EvaluatedJob",
    "JobMatchScorer",
    "MatchEvaluation",
    "PackageBuildError",
    "PlanningConfigurationError",
]
