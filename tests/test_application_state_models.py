"""Unit tests for `app.application_state.models`."""

from datetime import UTC, datetime

from app.application_state.models import (
    ApplicationState,
    ApplicationStatus,
    RecoveryReport,
    StateTransition,
)
from tests.job_discovery_fixtures import sample_job


def _state(status: ApplicationStatus = ApplicationStatus.PENDING) -> ApplicationState:
    now = datetime.now(UTC)
    job = sample_job()
    return ApplicationState(
        job_id="abc123",
        job=job,
        company=job.company,
        title=job.title,
        status=status,
        created_at=now,
        updated_at=now,
    )


def test_is_terminal_true_only_for_submitted() -> None:
    assert _state(ApplicationStatus.SUBMITTED).is_terminal is True
    assert _state(ApplicationStatus.FAILED).is_terminal is False
    assert _state(ApplicationStatus.PENDING).is_terminal is False


def test_is_recoverable_excludes_terminal_and_failed() -> None:
    assert _state(ApplicationStatus.PENDING).is_recoverable is True
    assert _state(ApplicationStatus.PLANNING).is_recoverable is True
    assert _state(ApplicationStatus.SUBMITTING).is_recoverable is True
    assert _state(ApplicationStatus.SUBMITTED).is_recoverable is False
    assert _state(ApplicationStatus.FAILED).is_recoverable is False


def test_state_transition_roundtrip() -> None:
    now = datetime.now(UTC)
    transition = StateTransition(
        job_id="abc123",
        company="Acme",
        title="Engineer",
        from_status=ApplicationStatus.PENDING,
        to_status=ApplicationStatus.PLANNING,
        timestamp=now,
    )
    restored = StateTransition.model_validate_json(transition.model_dump_json())
    assert restored == transition


def test_recovery_report_total_examined() -> None:
    now = datetime.now(UTC)
    report = RecoveryReport(
        started_at=now, ended_at=now, recovered_job_ids=["a", "b"], failed_job_ids=["c"]
    )
    assert report.total_examined == 3
