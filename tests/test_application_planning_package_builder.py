"""Unit tests for `app.application_planning.package_builder.ApplicationPackageBuilder`."""

import pytest

from app.application_planning.exceptions import PackageBuildError
from app.application_planning.package_builder import ApplicationPackageBuilder
from tests.application_planning_fixtures import (
    sample_blueprint,
    sample_cover_letter_service,
    sample_discovered_job,
    sample_resume_service,
)
from tests.resume_fixtures import profile_with_no_skills, sample_career_profile


async def test_build_produces_resume_and_cover_letter() -> None:
    builder = ApplicationPackageBuilder(
        sample_resume_service(), sample_cover_letter_service(), enhance_with_llm=False
    )
    job = sample_discovered_job()
    package = await builder.build(job, sample_career_profile(), sample_blueprint(), "job-1")
    assert package.job_id == "job-1"
    assert package.company == job.company
    assert package.title == job.title
    assert package.application_url == job.source_url
    assert package.resume_markdown
    assert package.cover_letter_markdown


async def test_build_raises_package_build_error_on_generation_failure() -> None:
    builder = ApplicationPackageBuilder(
        sample_resume_service(), sample_cover_letter_service(), enhance_with_llm=False
    )
    job = sample_discovered_job()
    with pytest.raises(PackageBuildError) as exc_info:
        await builder.build(job, profile_with_no_skills(), sample_blueprint(), "job-2")
    assert exc_info.value.job_id == "job-2"
    assert "job-2" in str(exc_info.value)


async def test_build_uses_configured_templates() -> None:
    from app.cover_letter.models import CoverLetterTemplate
    from app.resume.models import ResumeTemplate

    builder = ApplicationPackageBuilder(
        sample_resume_service(),
        sample_cover_letter_service(),
        resume_template=ResumeTemplate.AI_ENGINEER,
        cover_letter_template=CoverLetterTemplate.AI_ENGINEER,
        enhance_with_llm=False,
    )
    package = await builder.build(
        sample_discovered_job(), sample_career_profile(), sample_blueprint(), "job-3"
    )
    assert package.resume_document.template.value == "ai_engineer"
    assert package.cover_letter_document.template.value == "ai_engineer"
