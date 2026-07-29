"""Unit tests for `app.application_planning.decision.DecisionEngine`."""

from app.application_planning.decision import DecisionEngine, DecisionThresholds
from app.application_planning.models import (
    ApplicationDecision,
    ApplicationPriority,
    MatchEvaluation,
)
from app.intelligence.models import MissingSkill


def _evaluation(score: float, missing_required: int = 0) -> MatchEvaluation:
    return MatchEvaluation(
        match_score=score,
        matched_skills=["Python"],
        missing_skills=[
            MissingSkill(name=f"skill_{i}", importance="required") for i in range(missing_required)
        ],
    )


def test_low_score_results_in_skip() -> None:
    decision, priority, reasons = DecisionEngine().decide(_evaluation(30.0))
    assert decision is ApplicationDecision.SKIP
    assert priority is ApplicationPriority.LOW
    assert any("below the apply threshold" in reason for reason in reasons)


def test_too_many_missing_required_skills_results_in_skip() -> None:
    decision, priority, reasons = DecisionEngine().decide(_evaluation(90.0, missing_required=10))
    assert decision is ApplicationDecision.SKIP
    assert any("exceeds the maximum" in reason for reason in reasons)


def test_high_score_and_no_missing_skills_is_apply_high_priority() -> None:
    decision, priority, reasons = DecisionEngine().decide(_evaluation(90.0))
    assert decision is ApplicationDecision.APPLY
    assert priority is ApplicationPriority.HIGH
    assert any("No required skills are missing" in reason for reason in reasons)


def test_medium_score_is_apply_medium_priority() -> None:
    decision, priority, _ = DecisionEngine().decide(_evaluation(65.0))
    assert decision is ApplicationDecision.APPLY
    assert priority is ApplicationPriority.MEDIUM


def test_score_just_above_apply_threshold_is_low_priority() -> None:
    decision, priority, _ = DecisionEngine().decide(_evaluation(55.0))
    assert decision is ApplicationDecision.APPLY
    assert priority is ApplicationPriority.LOW


def test_apply_with_acceptable_missing_required_skills_notes_it() -> None:
    decision, _, reasons = DecisionEngine().decide(_evaluation(90.0, missing_required=1))
    assert decision is ApplicationDecision.APPLY
    assert any("within the acceptable" in reason for reason in reasons)


def test_score_exactly_at_apply_threshold_applies() -> None:
    thresholds = DecisionThresholds(apply_score_threshold=50.0)
    decision, _, _ = DecisionEngine(thresholds).decide(_evaluation(50.0))
    assert decision is ApplicationDecision.APPLY


def test_score_exactly_at_high_priority_threshold_is_high() -> None:
    thresholds = DecisionThresholds(high_priority_threshold=80.0)
    _, priority, _ = DecisionEngine(thresholds).decide(_evaluation(80.0))
    assert priority is ApplicationPriority.HIGH


def test_custom_thresholds_are_respected() -> None:
    thresholds = DecisionThresholds(
        apply_score_threshold=90.0, high_priority_threshold=95.0, medium_priority_threshold=92.0
    )
    decision, priority, _ = DecisionEngine(thresholds).decide(_evaluation(91.0))
    assert decision is ApplicationDecision.APPLY
    assert priority is ApplicationPriority.LOW


def test_missing_required_skills_at_exact_max_still_applies() -> None:
    thresholds = DecisionThresholds(max_missing_required_skills=2)
    decision, _, _ = DecisionEngine(thresholds).decide(_evaluation(90.0, missing_required=2))
    assert decision is ApplicationDecision.APPLY


def test_default_thresholds_values() -> None:
    thresholds = DecisionThresholds()
    assert thresholds.apply_score_threshold == 50.0
    assert thresholds.high_priority_threshold == 80.0
    assert thresholds.medium_priority_threshold == 60.0
    assert thresholds.max_missing_required_skills == 3
