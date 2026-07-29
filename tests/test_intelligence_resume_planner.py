import pytest

from app.intelligence.resume_planner import ResumePlanner
from tests.intelligence_fixtures import SAMPLE_JOBS, sample_career_context

planner = ResumePlanner()


@pytest.mark.parametrize("job_key", list(SAMPLE_JOBS))
def test_blueprint_has_the_expected_shape(job_key: str) -> None:
    blueprint = planner.plan(SAMPLE_JOBS[job_key], sample_career_context())

    assert 0.0 <= blueprint.match_score <= 100.0
    assert isinstance(blueprint.recommended_projects, list)
    assert isinstance(blueprint.recommended_skills, list)
    assert isinstance(blueprint.missing_skills, list)
    assert blueprint.resume_sections  # never empty
    assert blueprint.reasoning  # never empty


def test_backend_engineer_blueprint() -> None:
    blueprint = planner.plan(SAMPLE_JOBS["backend_engineer"], sample_career_context())

    # Strong (but not perfect) fit: all required skills match, one
    # preferred skill (Redis) is missing, and only one other project
    # overlaps at all — match_score reflects that honestly rather than
    # rounding up to a number that looks better than the underlying signal.
    assert blueprint.match_score > 50
    assert blueprint.recommended_projects[0].name == "Market Data Platform"
    assert "Python" in blueprint.recommended_skills
    assert blueprint.resume_sections == [
        "Summary",
        "Experience",
        "Projects",
        "Skills",
        "Education",
        "Certificates",
    ]
    assert not any(m.importance == "required" for m in blueprint.missing_skills)


def test_ai_engineer_blueprint_flags_missing_skills() -> None:
    blueprint = planner.plan(SAMPLE_JOBS["ai_engineer"], sample_career_context())

    assert any(m.importance == "required" for m in blueprint.missing_skills)
    assert blueprint.resume_sections[:2] == ["Summary", "Skills"]


def test_recommended_projects_capped_at_five() -> None:
    blueprint = planner.plan(SAMPLE_JOBS["python_developer"], sample_career_context())

    assert len(blueprint.recommended_projects) <= 5
