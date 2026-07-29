"""Shared sample data for Sprint 6 cover letter generation tests.

Reuses Sprint 5's fixtures (`tests.resume_fixtures`) for the scripted LLM
provider and sample `CareerProfile`, and builds a real `ResumeDocument` via
Sprint 5's own `ResumeGenerator` so cover letter tests exercise genuine
Sprint 5 output rather than a hand-rolled stand-in.
"""

from app.intelligence.models import ResumeBlueprint
from app.intelligence.resume_planner import ResumePlanner
from app.resume.generator import ResumeGenerator
from app.resume.models import ResumeDocument, ResumeTemplate
from tests.intelligence_fixtures import SAMPLE_JOBS, sample_career_context
from tests.resume_fixtures import make_llm_service, sample_career_profile

__all__ = [
    "make_llm_service",
    "sample_career_profile",
    "sample_blueprint",
    "sample_resume_document",
]


def sample_blueprint(job_key: str = "backend_engineer") -> ResumeBlueprint:
    return ResumePlanner().plan(SAMPLE_JOBS[job_key], sample_career_context())


async def sample_resume_document(job_key: str = "backend_engineer") -> ResumeDocument:
    blueprint = sample_blueprint(job_key)
    generator = ResumeGenerator(make_llm_service([]))
    return await generator.generate(
        blueprint,
        sample_career_profile(),
        template=ResumeTemplate.BACKEND_ENGINEER,
        enhance_with_llm=False,
    )
