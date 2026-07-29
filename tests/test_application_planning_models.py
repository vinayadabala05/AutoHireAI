"""Unit tests for `app.application_planning.models`."""

from datetime import UTC, datetime

from app.application_planning.models import (
    ApplicationDecision,
    ApplicationPriority,
    MatchEvaluation,
)
from app.intelligence.models import MissingSkill


def test_match_evaluation_splits_required_and_preferred_missing_skills() -> None:
    evaluation = MatchEvaluation(
        match_score=70.0,
        matched_skills=["Python"],
        missing_skills=[
            MissingSkill(name="Kubernetes", importance="required"),
            MissingSkill(name="Go", importance="preferred"),
        ],
    )
    assert [skill.name for skill in evaluation.missing_required_skills] == ["Kubernetes"]
    assert [skill.name for skill in evaluation.missing_preferred_skills] == ["Go"]


def test_match_evaluation_defaults() -> None:
    evaluation = MatchEvaluation(match_score=0.0)
    assert evaluation.matched_skills == []
    assert evaluation.missing_skills == []
    assert evaluation.explanations == []
    assert evaluation.missing_required_skills == []


def test_application_decision_and_priority_enum_values() -> None:
    assert ApplicationDecision.APPLY.value == "apply"
    assert ApplicationDecision.SKIP.value == "skip"
    assert {p.value for p in ApplicationPriority} == {"high", "medium", "low"}


def test_application_plan_serializes_round_trip() -> None:
    from app.application_planning.models import ApplicationPlan

    plan = ApplicationPlan(
        job_id="abc",
        company="Acme",
        title="Engineer",
        match_score=80.0,
        decision=ApplicationDecision.APPLY,
        priority=ApplicationPriority.HIGH,
        reasons=["good match"],
        matched_skills=["Python"],
        missing_skills=[],
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )
    dumped = plan.model_dump_json()
    restored = type(plan).model_validate_json(dumped)
    assert restored.job_id == "abc"
    assert restored.decision is ApplicationDecision.APPLY
    assert restored.generated_resume is None
