"""Unit tests for `app.application_planning.planner.ApplicationPlanner`."""

from app.application_planning.decision import DecisionEngine, DecisionThresholds
from app.application_planning.models import ApplicationDecision
from app.application_planning.planner import ApplicationPlanner
from tests.application_planning_fixtures import (
    sample_blueprint,
    sample_career_profile,
    sample_discovered_job,
)


def test_evaluate_job_returns_evaluated_job_with_matching_job() -> None:
    job = sample_discovered_job()
    result = ApplicationPlanner().evaluate_job(job, sample_career_profile())
    assert result.job is job
    assert result.decision in (ApplicationDecision.APPLY, ApplicationDecision.SKIP)


def test_evaluate_job_uses_blueprint_when_given() -> None:
    job = sample_discovered_job(skills=["Python", "FastAPI", "PostgreSQL"])
    blueprint = sample_blueprint()
    result = ApplicationPlanner().evaluate_job(job, sample_career_profile(), blueprint)
    assert result.evaluation.match_score >= 0.0


def test_evaluate_job_respects_custom_decision_engine() -> None:
    strict_engine = DecisionEngine(DecisionThresholds(apply_score_threshold=99.9))
    planner = ApplicationPlanner(decision_engine=strict_engine)
    result = planner.evaluate_job(sample_discovered_job(), sample_career_profile())
    assert result.decision is ApplicationDecision.SKIP


def test_evaluate_job_reasons_are_non_empty() -> None:
    result = ApplicationPlanner().evaluate_job(sample_discovered_job(), sample_career_profile())
    assert len(result.reasons) > 0
