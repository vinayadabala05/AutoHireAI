"""Integration tests for `app.application_planning.service.ApplicationPlanningService`."""

import pytest

from app.application_planning.decision import DecisionEngine, DecisionThresholds
from app.application_planning.exceptions import PlanningConfigurationError
from app.application_planning.models import ApplicationDecision
from app.application_planning.package_builder import ApplicationPackageBuilder
from app.application_planning.planner import ApplicationPlanner
from app.application_planning.service import ApplicationPlanningService
from app.job_discovery.deduplication import content_hash
from tests.application_planning_fixtures import (
    sample_blueprint,
    sample_career_profile,
    sample_cover_letter_service,
    sample_discovered_job,
    sample_resume_service,
)


def _builder() -> ApplicationPackageBuilder:
    return ApplicationPackageBuilder(
        sample_resume_service(), sample_cover_letter_service(), enhance_with_llm=False
    )


async def test_create_plan_apply_path_generates_documents() -> None:
    service = ApplicationPlanningService(package_builder=_builder())
    job = sample_discovered_job(skills=["Python", "FastAPI", "PostgreSQL"])
    plan = await service.create_plan(job, sample_career_profile(), sample_blueprint())
    assert plan.decision is ApplicationDecision.APPLY
    assert plan.generated_resume is not None
    assert plan.generated_cover_letter is not None
    assert plan.job_id == content_hash(job)


async def test_create_plan_skip_path_does_not_generate_documents() -> None:
    strict_planner = ApplicationPlanner(
        decision_engine=DecisionEngine(DecisionThresholds(apply_score_threshold=99.9))
    )
    service = ApplicationPlanningService(planner=strict_planner, package_builder=_builder())
    job = sample_discovered_job()
    plan = await service.create_plan(job, sample_career_profile(), sample_blueprint())
    assert plan.decision is ApplicationDecision.SKIP
    assert plan.generated_resume is None
    assert plan.generated_cover_letter is None


async def test_create_plan_without_package_builder_skips_generation_even_on_apply() -> None:
    service = ApplicationPlanningService()  # no package builder configured
    job = sample_discovered_job(skills=["Python", "FastAPI", "PostgreSQL"])
    plan = await service.create_plan(job, sample_career_profile(), sample_blueprint())
    assert plan.decision is ApplicationDecision.APPLY
    assert plan.generated_resume is None


async def test_create_plan_uses_explicit_job_id_when_given() -> None:
    service = ApplicationPlanningService(package_builder=_builder())
    job = sample_discovered_job(skills=["Python"])
    plan = await service.create_plan(
        job, sample_career_profile(), sample_blueprint(), job_id="custom-id"
    )
    assert plan.job_id == "custom-id"


def test_evaluate_job_delegates_to_planner() -> None:
    service = ApplicationPlanningService()
    job = sample_discovered_job()
    result = service.evaluate_job(job, sample_career_profile())
    assert result.job is job


async def test_build_application_package_without_builder_raises() -> None:
    service = ApplicationPlanningService()
    job = sample_discovered_job()
    with pytest.raises(PlanningConfigurationError):
        await service.build_application_package(job, sample_career_profile(), sample_blueprint())


async def test_build_application_package_with_builder_succeeds() -> None:
    service = ApplicationPlanningService(package_builder=_builder())
    job = sample_discovered_job()
    package = await service.build_application_package(
        job, sample_career_profile(), sample_blueprint()
    )
    assert package.job_id == content_hash(job)


async def test_build_application_package_uses_explicit_job_id() -> None:
    service = ApplicationPlanningService(package_builder=_builder())
    job = sample_discovered_job()
    package = await service.build_application_package(
        job, sample_career_profile(), sample_blueprint(), job_id="explicit-id"
    )
    assert package.job_id == "explicit-id"


async def test_same_job_produces_same_default_job_id_across_calls() -> None:
    service = ApplicationPlanningService(package_builder=_builder())
    job_a = sample_discovered_job()
    job_b = sample_discovered_job()  # identical content -> same content_hash
    plan_a = await service.create_plan(job_a, sample_career_profile(), sample_blueprint())
    plan_b = await service.create_plan(job_b, sample_career_profile(), sample_blueprint())
    assert plan_a.job_id == plan_b.job_id
