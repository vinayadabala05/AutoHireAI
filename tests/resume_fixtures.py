"""Shared sample data for Sprint 5 resume generation tests.

`sample_career_profile()` deliberately mirrors the names/technologies in
`tests.intelligence_fixtures.sample_career_context()` (same project and
experience names) so a `ResumeBlueprint` built from that `CareerContext` can
be paired with this `CareerProfile` in generator tests that exercise
project/skill ranking end-to-end.
"""

import uuid
from datetime import UTC, date, datetime

from app.career_profile.models import (
    CareerProfile,
    EducationProfile,
    ExperienceProfile,
    PersonalInfo,
    ProjectProfile,
    SkillProfile,
)
from app.llm.base import BaseLLMProvider
from app.llm.config import LLMSettings
from app.llm.models import (
    GenerationMetadata,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderConfiguration,
    TokenUsage,
)
from app.llm.service import LLMService
from app.llm.validator import ResponseValidator
from app.models.enums import ProjectPriority, SkillCategory


class ScriptedResumeProvider(BaseLLMProvider):
    """Fake LLM provider that echoes a scripted response for each `generate()` call.

    If the script runs out, it falls back to echoing the prompt back
    verbatim rather than raising, so tests that don't care about exact LLM
    call counts (e.g. "does the whole document assemble") don't need to
    over-specify the script.
    """

    def __init__(self, config: ProviderConfiguration, outcomes: list[str]) -> None:
        super().__init__(config)
        self._outcomes = list(outcomes)
        self.calls = 0
        self.prompts: list[str] = []

    @property
    def provider_name(self) -> str:
        return "scripted-resume"

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.calls += 1
        self.prompts.append(request.prompt)
        content = self._outcomes.pop(0) if self._outcomes else request.prompt
        return LLMResponse(
            content=content,
            usage=TokenUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            metadata=GenerationMetadata(
                provider=LLMProvider.CLAUDE, model="test-model", latency_ms=1.0
            ),
        )

    async def health_check(self) -> bool:
        return True


def make_llm_service(outcomes: list[str]) -> LLMService:
    config = ProviderConfiguration(provider=LLMProvider.CLAUDE, model="test-model")
    provider = ScriptedResumeProvider(config, outcomes)
    settings = LLMSettings(_env_file=None)
    return LLMService(provider=provider, settings=settings, validator=ResponseValidator())


def sample_career_profile() -> CareerProfile:
    return CareerProfile(
        user_id=uuid.uuid4(),
        generated_at=datetime.now(UTC),
        personal_info=PersonalInfo(
            full_name="Jordan Smith",
            email="jordan.smith@example.com",
            phone="+1-555-0100",
            location="Remote",
            headline="Backend Engineer",
            summary="Backend engineer with 5 years building Python web services.",
            linkedin_url="https://linkedin.com/in/jordansmith",
        ),
        education=[
            EducationProfile(
                institution="State University",
                degree="B.S.",
                field_of_study="Computer Science",
                start_date=date(2015, 9, 1),
                end_date=date(2019, 5, 1),
                gpa=3.7,
            )
        ],
        experience=[
            ExperienceProfile(
                title="Backend Engineer",
                company_name="Acme Corp",
                location="Remote",
                start_date=date(2021, 1, 1),
                is_current=True,
                description="Building backend services with FastAPI and PostgreSQL.",
                achievements=[
                    "Reduced API latency by 40% through query optimization.",
                    "Led migration of monolith to microservices.",
                ],
                technologies=["Python", "FastAPI", "PostgreSQL", "Docker"],
            ),
            ExperienceProfile(
                title="Data Analyst Intern",
                company_name="Globex",
                start_date=date(2018, 6, 1),
                end_date=date(2018, 9, 1),
                description="Analyzed datasets with Python and SQL.",
                achievements=["Automated a weekly reporting pipeline."],
                technologies=["Python", "SQL"],
            ),
        ],
        projects=[
            ProjectProfile(
                name="Market Data Platform",
                description=(
                    "Built a real-time market data platform using FastAPI and PostgreSQL, "
                    "deployed with Docker on AWS."
                ),
                technologies=["FastAPI", "PostgreSQL", "Docker", "AWS"],
                achievements=["Processed 1M+ events/day with sub-second latency."],
                priority=ProjectPriority.FEATURED,
            ),
            ProjectProfile(
                name="ML Recommendation Engine",
                description=(
                    "Built a recommendation engine using TensorFlow and Pandas for feature "
                    "engineering."
                ),
                technologies=["Python", "TensorFlow", "Pandas"],
                priority=ProjectPriority.MEDIUM,
            ),
            ProjectProfile(
                name="Personal Blog",
                description="A simple personal blog built with React and JavaScript.",
                technologies=["React", "JavaScript"],
                priority=ProjectPriority.LOW,
            ),
        ],
        skills=[
            SkillProfile(name="Python", category=SkillCategory.LANGUAGE, years_experience=5),
            SkillProfile(name="FastAPI", category=SkillCategory.FRAMEWORK, years_experience=3),
            SkillProfile(name="PostgreSQL", category=SkillCategory.DATABASE, years_experience=4),
            SkillProfile(name="Docker", category=SkillCategory.DEVOPS_TOOL, years_experience=3),
            SkillProfile(name="AWS", category=SkillCategory.CLOUD, years_experience=2),
            SkillProfile(name="Git", category=SkillCategory.OTHER, years_experience=5),
        ],
        certificates=[],
    )


def profile_with_duplicate_projects() -> CareerProfile:
    profile = sample_career_profile()
    duplicate = profile.projects[0].model_copy()
    return profile.model_copy(update={"projects": [*profile.projects, duplicate]})


def profile_with_no_skills() -> CareerProfile:
    profile = sample_career_profile()
    return profile.model_copy(update={"skills": []})
