from app.intelligence.experience_ranker import ExperienceRanker
from app.intelligence.job_analyzer import JobAnalyzer
from app.intelligence.project_ranker import ProjectRanker
from app.intelligence.section_optimizer import SectionOptimizer
from app.intelligence.skill_matcher import SkillMatcher
from tests.intelligence_fixtures import SAMPLE_JOBS, sample_career_context

analyzer = JobAnalyzer()
matcher = SkillMatcher()
project_ranker = ProjectRanker()
experience_ranker = ExperienceRanker()
optimizer = SectionOptimizer()


def _plan_sections(job_key: str) -> list[str]:
    context = sample_career_context()
    analysis = analyzer.analyze(SAMPLE_JOBS[job_key])
    skill_match = matcher.match(context.skills, analysis.required_skills, analysis.preferred_skills)
    project_rankings = project_ranker.rank(context.projects, analysis)
    experience_rankings = experience_ranker.rank(context.experiences, analysis)
    plan = optimizer.optimize(analysis, skill_match, project_rankings, experience_rankings)
    return plan.order


def test_ai_engineer_leads_with_skills_and_projects() -> None:
    order = _plan_sections("ai_engineer")
    assert order == ["Summary", "Skills", "Projects", "Experience", "Education", "Certificates"]


def test_research_engineer_leads_with_skills_and_projects() -> None:
    order = _plan_sections("research_engineer")
    assert order == ["Summary", "Skills", "Projects", "Experience", "Education", "Certificates"]


def test_ml_engineer_leads_with_skills_and_projects() -> None:
    order = _plan_sections("ml_engineer")
    assert order == ["Summary", "Skills", "Projects", "Experience", "Education", "Certificates"]


def test_backend_engineer_leads_with_experience() -> None:
    order = _plan_sections("backend_engineer")
    assert order == ["Summary", "Experience", "Projects", "Skills", "Education", "Certificates"]


def test_python_developer_leads_with_experience() -> None:
    order = _plan_sections("python_developer")
    assert order == ["Summary", "Experience", "Projects", "Skills", "Education", "Certificates"]
