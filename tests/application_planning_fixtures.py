"""Shared sample data for Sprint 9 Application Planning Engine tests."""

from app.cover_letter.service import CoverLetterGenerationService
from app.intelligence.models import ResumeBlueprint
from app.intelligence.resume_planner import ResumePlanner
from app.job_discovery.models import DiscoveredJob
from app.resume.service import ResumeGenerationService
from tests.intelligence_fixtures import SAMPLE_JOBS, sample_career_context
from tests.job_discovery_fixtures import sample_job
from tests.resume_fixtures import make_llm_service, sample_career_profile

__all__ = [
    "make_llm_service",
    "sample_blueprint",
    "sample_career_profile",
    "sample_discovered_job",
    "sample_resume_service",
    "sample_cover_letter_service",
]


def sample_blueprint(job_key: str = "backend_engineer") -> ResumeBlueprint:
    return ResumePlanner().plan(SAMPLE_JOBS[job_key], sample_career_context())


def sample_discovered_job(**overrides: object) -> DiscoveredJob:
    return sample_job(**overrides)


def sample_resume_service() -> ResumeGenerationService:
    return ResumeGenerationService(make_llm_service([]))


def sample_cover_letter_service() -> CoverLetterGenerationService:
    return CoverLetterGenerationService(make_llm_service([]))
