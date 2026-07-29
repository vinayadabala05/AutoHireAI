"""Structural interfaces for the Application Planning Engine.

Every concrete class in this package satisfies one of these `Protocol`s,
so `ApplicationPlanner`/`ApplicationPlanningService` depend on shape, not
on `JobMatchScorer`/`DecisionEngine`/`ApplicationPackageBuilder` directly —
a future alternative scorer or decision policy only needs to satisfy the
same `Protocol`.
"""

from typing import Protocol

from app.application_planning.models import (
    ApplicationDecision,
    ApplicationPackage,
    ApplicationPriority,
    MatchEvaluation,
)
from app.career_profile.models import CareerProfile
from app.intelligence.models import ResumeBlueprint
from app.job_discovery.models import DiscoveredJob, JobSearchPreferences

__all__ = [
    "ApplicationPackageBuilderProtocol",
    "DecisionEngineProtocol",
    "JobMatchScorerProtocol",
]


class JobMatchScorerProtocol(Protocol):
    def evaluate(
        self,
        job: DiscoveredJob,
        profile: CareerProfile,
        blueprint: ResumeBlueprint | None = None,
        *,
        preferences: JobSearchPreferences | None = None,
    ) -> MatchEvaluation: ...


class DecisionEngineProtocol(Protocol):
    def decide(
        self, evaluation: MatchEvaluation
    ) -> tuple[ApplicationDecision, ApplicationPriority, list[str]]: ...


class ApplicationPackageBuilderProtocol(Protocol):
    async def build(
        self,
        job: DiscoveredJob,
        profile: CareerProfile,
        blueprint: ResumeBlueprint,
        job_id: str,
    ) -> ApplicationPackage: ...
