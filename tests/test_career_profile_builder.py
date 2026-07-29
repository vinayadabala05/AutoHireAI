"""Unit tests for `CareerProfileBuilder` — pure transformation, no database.

ORM instances are constructed in-memory (never added to a session), so
`id` is set by hand rather than relying on the column's server/Python-side
default, which only applies at flush time.
"""

import uuid
from datetime import date, datetime

from app.career_profile.builder import CareerProfileBuilder
from app.career_profile.loader import RawProfileData
from app.models.application import Application
from app.models.enums import (
    EmploymentType,
    InterviewType,
    JobSource,
    ProjectPriority,
    RemoteType,
    SkillCategory,
)
from app.models.interview import Interview
from app.models.job import Job
from app.models.profile import Certificate, Education, Experience, GithubRepository, Project, Skill
from app.models.user import User

builder = CareerProfileBuilder()


def _make_user() -> User:
    user = User(
        email="jordan@example.com",
        full_name="Jordan Smith",
        phone="555-0100",
        location="Remote",
        headline="Backend Engineer",
        summary="Backend engineer with 5 years of experience.",
        linkedin_url="https://linkedin.com/in/jordan",
        portfolio_url="https://jordan.dev",
        timezone="UTC",
    )
    user.id = uuid.uuid4()
    return user


def test_builder_maps_personal_info_and_sections() -> None:
    user = _make_user()
    education = Education(
        user_id=user.id,
        institution="MIT",
        degree="BSc Computer Science",
        start_date=date(2018, 9, 1),
        is_current=False,
    )
    experience = Experience(
        user_id=user.id,
        company_name="Acme Corp",
        title="Backend Engineer",
        start_date=date(2022, 1, 1),
        is_current=True,
        technologies=["Python", "FastAPI"],
    )
    project = Project(
        user_id=user.id,
        name="Market Data Platform",
        description="Real-time market data platform.",
        technologies=["FastAPI", "PostgreSQL"],
        priority=ProjectPriority.FEATURED,
    )
    skill = Skill(
        user_id=user.id, name="Python", category=SkillCategory.LANGUAGE, years_experience=5
    )
    certificate = Certificate(user_id=user.id, name="AWS Certified", issuing_organization="AWS")
    repo = GithubRepository(
        user_id=user.id,
        name="hello-world",
        full_name="jordan/hello-world",
        url="https://github.com/jordan/hello-world",
        stars=0,
        forks=0,
        is_featured=False,
    )

    raw = RawProfileData(
        user=user,
        educations=[education],
        experiences=[experience],
        projects=[project],
        skills=[skill],
        certificates=[certificate],
        github_repositories=[repo],
    )

    profile = builder.build(raw)

    assert profile.user_id == user.id
    assert isinstance(profile.generated_at, datetime)
    assert profile.personal_info.full_name == "Jordan Smith"
    assert profile.personal_info.email == "jordan@example.com"
    assert profile.education[0].institution == "MIT"
    assert profile.experience[0].title == "Backend Engineer"
    assert profile.projects[0].name == "Market Data Platform"
    assert profile.projects[0].priority is ProjectPriority.FEATURED
    assert profile.skills[0].name == "Python"
    assert profile.certificates[0].name == "AWS Certified"
    assert profile.github_repositories[0].full_name == "jordan/hello-world"


def test_builder_handles_empty_profile() -> None:
    user = _make_user()
    raw = RawProfileData(user=user)

    profile = builder.build(raw)

    assert profile.education == []
    assert profile.experience == []
    assert profile.projects == []
    assert profile.skills == []
    assert profile.certificates == []
    assert profile.github_repositories == []
    assert profile.preferences.application.total_applications == 0
    assert profile.preferences.interview.total_interviews == 0


def test_builder_derives_application_preferences_from_job_history() -> None:
    user = _make_user()
    company_id = uuid.uuid4()

    job_remote_full_time = Job(
        company_id=company_id,
        title="Backend Engineer",
        employment_type=EmploymentType.FULL_TIME,
        remote_type=RemoteType.REMOTE,
        location="Remote",
        salary_min=120_000,
        salary_max=150_000,
        source=JobSource.MANUAL,
    )
    job_remote_full_time.id = uuid.uuid4()

    job_contract = Job(
        company_id=company_id,
        title="Contract Backend Engineer",
        employment_type=EmploymentType.CONTRACT,
        remote_type=RemoteType.REMOTE,
        location="Remote",
        salary_min=90_000,
        salary_max=110_000,
        source=JobSource.MANUAL,
    )
    job_contract.id = uuid.uuid4()

    app1 = Application(user_id=user.id, job_id=job_remote_full_time.id, applied_at=datetime.now())
    app1.id = uuid.uuid4()
    app2 = Application(user_id=user.id, job_id=job_contract.id, applied_at=datetime.now())
    app2.id = uuid.uuid4()
    app3 = Application(user_id=user.id, job_id=job_remote_full_time.id, applied_at=datetime.now())
    app3.id = uuid.uuid4()

    raw = RawProfileData(
        user=user,
        applications=[app1, app2, app3],
        jobs_by_id={job_remote_full_time.id: job_remote_full_time, job_contract.id: job_contract},
    )

    profile = builder.build(raw)
    prefs = profile.preferences.application

    assert prefs.total_applications == 3
    # FULL_TIME appears twice (app1, app3), CONTRACT once -> FULL_TIME ranks first.
    assert prefs.preferred_employment_types[0] is EmploymentType.FULL_TIME
    assert prefs.preferred_remote_types[0] is RemoteType.REMOTE
    assert prefs.observed_salary_min == 90_000
    assert prefs.observed_salary_max == 150_000


def test_builder_derives_interview_preferences() -> None:
    user = _make_user()
    application_id = uuid.uuid4()

    interview1 = Interview(
        application_id=application_id, interview_type=InterviewType.TECHNICAL, duration_minutes=60
    )
    interview2 = Interview(
        application_id=application_id, interview_type=InterviewType.TECHNICAL, duration_minutes=30
    )
    interview3 = Interview(
        application_id=application_id, interview_type=InterviewType.BEHAVIORAL, duration_minutes=45
    )

    raw = RawProfileData(user=user, interviews=[interview1, interview2, interview3])

    profile = builder.build(raw)
    prefs = profile.preferences.interview

    assert prefs.total_interviews == 3
    assert prefs.preferred_interview_types[0] is InterviewType.TECHNICAL
    assert prefs.average_duration_minutes == 45.0
