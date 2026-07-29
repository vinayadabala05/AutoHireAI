"""Application Planning Service: the single entrypoint every caller should use.

Orchestrates `ApplicationPlanner` (score + decide) and
`ApplicationPackageBuilder` (resume + cover letter generation), mirroring
the "one facade per subsystem" convention every prior sprint established
(`CareerProfileService`, `LLMService`, `ResumeGenerationService`,
`CoverLetterGenerationService`, `JobDiscoveryService`, `GraphService`).
"""

from datetime import UTC, datetime

from loguru import logger

from app.application_planning.exceptions import PlanningConfigurationError
from app.application_planning.models import (
    ApplicationDecision,
    ApplicationPackage,
    ApplicationPlan,
    EvaluatedJob,
)
from app.application_planning.package_builder import ApplicationPackageBuilder
from app.application_planning.planner import ApplicationPlanner
from app.career_profile.models import CareerProfile
from app.intelligence.models import ResumeBlueprint
from app.job_discovery.deduplication import content_hash
from app.job_discovery.models import DiscoveredJob, JobSearchPreferences


class ApplicationPlanningService:
    def __init__(
        self,
        planner: ApplicationPlanner | None = None,
        package_builder: ApplicationPackageBuilder | None = None,
    ) -> None:
        self._planner = planner or ApplicationPlanner()
        self._package_builder = package_builder

    def evaluate_job(
        self,
        job: DiscoveredJob,
        profile: CareerProfile,
        blueprint: ResumeBlueprint | None = None,
        *,
        preferences: JobSearchPreferences | None = None,
    ) -> EvaluatedJob:
        return self._planner.evaluate_job(job, profile, blueprint, preferences=preferences)

    async def build_application_package(
        self,
        job: DiscoveredJob,
        profile: CareerProfile,
        blueprint: ResumeBlueprint,
        *,
        job_id: str | None = None,
    ) -> ApplicationPackage:
        if self._package_builder is None:
            raise PlanningConfigurationError(
                "ApplicationPlanningService has no package builder configured; "
                "pass one to the constructor to build application packages."
            )
        return await self._package_builder.build(
            job, profile, blueprint, job_id or content_hash(job)
        )

    async def create_plan(
        self,
        job: DiscoveredJob,
        profile: CareerProfile,
        blueprint: ResumeBlueprint | None = None,
        *,
        preferences: JobSearchPreferences | None = None,
        job_id: str | None = None,
    ) -> ApplicationPlan:
        job_id = job_id or content_hash(job)
        evaluated = self.evaluate_job(job, profile, blueprint, preferences=preferences)

        plan = ApplicationPlan(
            job_id=job_id,
            company=job.company,
            title=job.title,
            match_score=evaluated.evaluation.match_score,
            decision=evaluated.decision,
            priority=evaluated.priority,
            reasons=evaluated.reasons,
            matched_skills=evaluated.evaluation.matched_skills,
            missing_skills=evaluated.evaluation.missing_skills,
            timestamp=datetime.now(UTC),
        )

        if (
            evaluated.decision is ApplicationDecision.APPLY
            and self._package_builder is not None
            and blueprint is not None
        ):
            package = await self._package_builder.build(job, profile, blueprint, job_id)
            plan.generated_resume = package.resume_document
            plan.generated_cover_letter = package.cover_letter_document

        logger.bind(job_id=job_id).info(
            "Created application plan for '{}' at '{}': {} ({}).",
            job.title,
            job.company,
            plan.decision.value,
            plan.priority.value,
        )
        return plan
