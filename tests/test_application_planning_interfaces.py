"""Structural tests for `app.application_planning.interfaces`."""

from app.application_planning.decision import DecisionEngine
from app.application_planning.interfaces import (
    ApplicationPackageBuilderProtocol,
    DecisionEngineProtocol,
    JobMatchScorerProtocol,
)
from app.application_planning.package_builder import ApplicationPackageBuilder
from app.application_planning.scorer import JobMatchScorer
from tests.application_planning_fixtures import sample_cover_letter_service, sample_resume_service

_PROTOCOL_MEMBERS: dict[type, tuple[str, ...]] = {
    JobMatchScorerProtocol: ("evaluate",),
    DecisionEngineProtocol: ("decide",),
    ApplicationPackageBuilderProtocol: ("build",),
}


def _satisfies(instance: object, protocol: type) -> bool:
    return all(hasattr(instance, member) for member in _PROTOCOL_MEMBERS[protocol])


def test_job_match_scorer_satisfies_protocol() -> None:
    assert _satisfies(JobMatchScorer(), JobMatchScorerProtocol)


def test_decision_engine_satisfies_protocol() -> None:
    assert _satisfies(DecisionEngine(), DecisionEngineProtocol)


def test_application_package_builder_satisfies_protocol() -> None:
    builder = ApplicationPackageBuilder(sample_resume_service(), sample_cover_letter_service())
    assert _satisfies(builder, ApplicationPackageBuilderProtocol)
