"""Unit tests for `app.resume.generator.ResumeGenerator`.

Uses a scripted fake LLM provider (see `tests.resume_fixtures`), never a real
network call, and a real `ResumeBlueprint` produced by Sprint 3's
`ResumePlanner` so section ordering/ranking is exercised end-to-end.
"""

from app.intelligence.resume_planner import ResumePlanner
from app.resume.generator import ResumeGenerator
from app.resume.models import ResumeSectionType, ResumeTemplate
from tests.intelligence_fixtures import SAMPLE_JOBS, sample_career_context
from tests.resume_fixtures import make_llm_service, sample_career_profile


def _blueprint(job_key: str = "backend_engineer") -> object:
    return ResumePlanner().plan(SAMPLE_JOBS[job_key], sample_career_context())


async def test_generate_produces_a_section_per_blueprint_entry() -> None:
    blueprint = _blueprint()
    generator = ResumeGenerator(make_llm_service(["Rewritten summary."]))
    document = await generator.generate(
        blueprint, sample_career_profile(), template=ResumeTemplate.BACKEND_ENGINEER
    )
    assert [s.section_type.value for s in document.sections] == blueprint.resume_sections


async def test_generate_without_job_title_skips_llm_summary_rewrite() -> None:
    blueprint = _blueprint()
    profile = sample_career_profile()
    total_achievements = sum(len(exp.achievements) for exp in profile.experience)
    service = make_llm_service([f"Rewritten #{i}" for i in range(total_achievements)])
    document = await ResumeGenerator(service).generate(
        blueprint, profile, enhance_with_llm=True, job_title=None
    )
    summary = document.section(ResumeSectionType.SUMMARY)
    assert summary is not None
    assert summary.content == profile.personal_info.summary
    assert service.provider.calls == total_achievements  # type: ignore[attr-defined]


async def test_generate_calls_llm_for_summary_when_job_title_given() -> None:
    blueprint = _blueprint()
    service = make_llm_service(["A tailored summary for the role."])
    document = await ResumeGenerator(service).generate(
        blueprint,
        sample_career_profile(),
        job_title="Backend Engineer",
        job_description="Build APIs.",
        enhance_with_llm=True,
    )
    summary = document.section(ResumeSectionType.SUMMARY)
    assert summary is not None
    assert summary.content == "A tailored summary for the role."


async def test_generate_rewrites_each_experience_achievement() -> None:
    blueprint = _blueprint()
    profile = sample_career_profile()
    total_achievements = sum(len(exp.achievements) for exp in profile.experience)
    service = make_llm_service(
        ["Tailored summary"] + [f"Rewritten #{i}" for i in range(total_achievements)]
    )
    document = await ResumeGenerator(service).generate(
        blueprint, profile, job_title="Backend Engineer", enhance_with_llm=True
    )
    experience = document.section(ResumeSectionType.EXPERIENCE)
    assert experience is not None
    assert "Rewritten #0" in experience.content


async def test_generate_without_llm_enhancement_uses_raw_achievements() -> None:
    blueprint = _blueprint()
    profile = sample_career_profile()
    service = make_llm_service([])
    document = await ResumeGenerator(service).generate(
        blueprint, profile, job_title="Backend Engineer", enhance_with_llm=False
    )
    experience = document.section(ResumeSectionType.EXPERIENCE)
    assert experience is not None
    assert profile.experience[0].achievements[0] in experience.content
    assert service.provider.calls == 0  # type: ignore[attr-defined]


async def test_generate_projects_section_prioritizes_blueprint_ranking() -> None:
    blueprint = _blueprint("ai_engineer")
    profile = sample_career_profile()
    document = await ResumeGenerator(make_llm_service([])).generate(
        blueprint, profile, enhance_with_llm=False
    )
    projects = document.section(ResumeSectionType.PROJECTS)
    assert projects is not None
    assert (
        "Market Data Platform" in projects.content or "ML Recommendation Engine" in projects.content
    )


async def test_generate_skills_section_lists_every_profile_skill() -> None:
    blueprint = _blueprint()
    profile = sample_career_profile()
    document = await ResumeGenerator(make_llm_service([])).generate(
        blueprint, profile, enhance_with_llm=False
    )
    skills = document.section(ResumeSectionType.SKILLS)
    assert skills is not None
    for skill in profile.skills:
        assert skill.name in skills.content


async def test_generate_is_deterministic_given_the_same_script() -> None:
    blueprint = _blueprint()
    profile = sample_career_profile()
    doc_a = await ResumeGenerator(make_llm_service([])).generate(
        blueprint, profile, enhance_with_llm=False
    )
    doc_b = await ResumeGenerator(make_llm_service([])).generate(
        blueprint, profile, enhance_with_llm=False
    )
    assert [s.content for s in doc_a.sections] == [s.content for s in doc_b.sections]


async def test_generate_across_multiple_job_descriptions_changes_section_order() -> None:
    backend_blueprint = _blueprint("backend_engineer")
    research_blueprint = _blueprint("research_engineer")
    profile = sample_career_profile()
    backend_doc = await ResumeGenerator(make_llm_service([])).generate(
        backend_blueprint, profile, enhance_with_llm=False
    )
    research_doc = await ResumeGenerator(make_llm_service([])).generate(
        research_blueprint, profile, enhance_with_llm=False
    )
    assert backend_doc.metadata["reasoning"] != research_doc.metadata["reasoning"]
