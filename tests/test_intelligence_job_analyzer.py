import pytest

from app.intelligence.job_analyzer import JobAnalyzer
from app.models.enums import EmploymentType, ExperienceLevel
from tests.intelligence_fixtures import SAMPLE_JOBS

analyzer = JobAnalyzer()


@pytest.mark.parametrize("job_key", list(SAMPLE_JOBS))
def test_analyze_produces_a_title_and_full_time_employment_type(job_key: str) -> None:
    analysis = analyzer.analyze(SAMPLE_JOBS[job_key])

    assert analysis.title == SAMPLE_JOBS[job_key].title
    assert analysis.employment_type is EmploymentType.FULL_TIME


def test_backend_engineer_required_skills_and_seniority() -> None:
    analysis = analyzer.analyze(SAMPLE_JOBS["backend_engineer"])

    for expected in ("Python", "FastAPI", "PostgreSQL", "Docker", "AWS"):
        assert expected in analysis.required_skills
    assert "Kubernetes" in analysis.preferred_skills
    assert any("bachelor" in req.lower() for req in analysis.education_requirements)


def test_ai_engineer_detects_senior_and_ml_keywords() -> None:
    analysis = analyzer.analyze(SAMPLE_JOBS["ai_engineer"])

    assert analysis.experience_level is ExperienceLevel.SENIOR
    for expected in ("Python", "PyTorch", "Machine Learning", "NLP"):
        assert expected in analysis.required_skills
    assert len(analysis.keywords.ai_ml) >= 3


def test_research_engineer_detects_phd_and_research_keywords() -> None:
    analysis = analyzer.analyze(SAMPLE_JOBS["research_engineer"])

    assert any("ph" in req.lower() for req in analysis.education_requirements)
    assert "Reinforcement Learning" in analysis.required_skills
    assert "Machine Learning" in analysis.required_skills


def test_ml_engineer_required_skills() -> None:
    analysis = analyzer.analyze(SAMPLE_JOBS["ml_engineer"])

    for expected in ("Python", "TensorFlow", "MLOps", "Docker", "Kubernetes"):
        assert expected in analysis.required_skills


def test_python_developer_required_skills() -> None:
    analysis = analyzer.analyze(SAMPLE_JOBS["python_developer"])

    for expected in ("Python", "Django", "PostgreSQL"):
        assert expected in analysis.required_skills
    assert "Docker" in analysis.preferred_skills
