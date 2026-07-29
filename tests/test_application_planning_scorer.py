"""Unit tests for `app.application_planning.scorer.JobMatchScorer`."""

from app.application_planning.scorer import JobMatchScorer
from tests.application_planning_fixtures import (
    sample_blueprint,
    sample_career_profile,
    sample_discovered_job,
)


def test_evaluate_returns_score_between_zero_and_hundred() -> None:
    evaluation = JobMatchScorer().evaluate(sample_discovered_job(), sample_career_profile())
    assert 0.0 <= evaluation.match_score <= 100.0


def test_evaluate_matches_skills_the_candidate_has() -> None:
    job = sample_discovered_job(skills=["Python", "FastAPI"])
    evaluation = JobMatchScorer().evaluate(job, sample_career_profile())
    assert "Python" in evaluation.matched_skills
    assert "FastAPI" in evaluation.matched_skills
    assert evaluation.missing_skills == []


def test_evaluate_identifies_missing_required_skills() -> None:
    job = sample_discovered_job(skills=["Python", "Rust", "Kubernetes"])
    evaluation = JobMatchScorer().evaluate(job, sample_career_profile())
    missing_names = {skill.name for skill in evaluation.missing_required_skills}
    assert "Rust" in missing_names or "Kubernetes" in missing_names


def test_evaluate_uses_blueprint_recommended_skills_as_preferred() -> None:
    job = sample_discovered_job(skills=["Python"])
    blueprint = sample_blueprint()
    evaluation = JobMatchScorer().evaluate(job, sample_career_profile(), blueprint)
    # Anything in blueprint.recommended_skills not already covered should
    # surface as a "preferred" gap, never "required" (since it isn't from job.skills).
    preferred_names = {skill.name for skill in evaluation.missing_preferred_skills}
    assert preferred_names.issubset(set(blueprint.recommended_skills))


def test_evaluate_without_blueprint_still_works() -> None:
    evaluation = JobMatchScorer().evaluate(sample_discovered_job(), sample_career_profile(), None)
    assert evaluation.match_score >= 0.0


def test_evaluate_returns_explanations() -> None:
    evaluation = JobMatchScorer().evaluate(sample_discovered_job(), sample_career_profile())
    assert len(evaluation.explanations) == 6  # one per JobRankingEngine factor


def test_evaluate_matched_skills_are_deduplicated() -> None:
    job = sample_discovered_job(skills=["Python", "Python"])
    evaluation = JobMatchScorer().evaluate(job, sample_career_profile())
    assert evaluation.matched_skills.count("Python") == 1
