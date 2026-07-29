"""Shared sample data for Sprint 7 Job Discovery Engine tests."""

import uuid
from datetime import UTC, date, datetime

from app.career_profile.models import (
    ApplicationPreference,
    CareerProfile,
    ExperienceProfile,
    PersonalInfo,
    PreferenceProfile,
    SkillProfile,
)
from app.intelligence.models import MissingSkill, ProjectRanking, ResumeBlueprint
from app.job_discovery.models import DiscoveredJob
from app.models.enums import EmploymentType, ExperienceLevel, JobSource, RemoteType, SkillCategory


def sample_job(**overrides: object) -> DiscoveredJob:
    defaults: dict[str, object] = {
        "title": "Backend Engineer",
        "company": "Acme Corp",
        "location": "San Francisco, CA",
        "remote_type": RemoteType.REMOTE,
        "salary_min": 130000.0,
        "salary_max": 160000.0,
        "currency": "USD",
        "employment_type": EmploymentType.FULL_TIME,
        "experience_level": ExperienceLevel.MID,
        "description": "Build APIs with Python and FastAPI.",
        "requirements": ["3+ years of Python"],
        "skills": ["Python", "FastAPI", "PostgreSQL"],
        "source": JobSource.COMPANY_SITE,
        "source_url": "https://boards.example.com/acme/backend-engineer",
        "posted_date": datetime(2026, 1, 1, tzinfo=UTC),
        "metadata": {},
    }
    defaults.update(overrides)
    return DiscoveredJob(**defaults)  # type: ignore[arg-type]


def sample_career_profile(**preference_overrides: object) -> CareerProfile:
    application_defaults: dict[str, object] = {
        "preferred_employment_types": [EmploymentType.FULL_TIME],
        "preferred_remote_types": [RemoteType.REMOTE],
        "preferred_locations": ["San Francisco", "Remote"],
        "observed_salary_min": 120000.0,
        "observed_salary_max": 170000.0,
    }
    application_defaults.update(preference_overrides)

    return CareerProfile(
        user_id=uuid.uuid4(),
        generated_at=datetime.now(UTC),
        personal_info=PersonalInfo(
            full_name="Jordan Smith",
            email="jordan.smith@example.com",
        ),
        experience=[
            ExperienceProfile(
                title="Backend Engineer",
                company_name="Old Corp",
                start_date=date(2021, 1, 1),
                is_current=True,
                technologies=["Python", "FastAPI"],
            ),
            ExperienceProfile(
                title="Junior Developer",
                company_name="First Job Inc",
                start_date=date(2019, 1, 1),
                end_date=date(2020, 12, 31),
                technologies=["Python"],
            ),
        ],
        skills=[
            SkillProfile(name="Python", category=SkillCategory.LANGUAGE, years_experience=5),
            SkillProfile(name="FastAPI", category=SkillCategory.FRAMEWORK, years_experience=3),
            SkillProfile(name="Docker", category=SkillCategory.DEVOPS_TOOL, years_experience=2),
        ],
        preferences=PreferenceProfile(application=ApplicationPreference(**application_defaults)),
    )


def sample_blueprint(**overrides: object) -> ResumeBlueprint:
    defaults: dict[str, object] = {
        "match_score": 82.0,
        "recommended_projects": [
            ProjectRanking(
                name="Market Data Platform", confidence=90.0, matched_keywords=["Python"]
            )
        ],
        "recommended_skills": ["Python", "FastAPI", "PostgreSQL"],
        "missing_skills": [MissingSkill(name="Kubernetes", importance="preferred")],
        "resume_sections": ["Summary", "Experience", "Skills", "Education"],
        "reasoning": ["Strong backend match."],
    }
    defaults.update(overrides)
    return ResumeBlueprint(**defaults)  # type: ignore[arg-type]
