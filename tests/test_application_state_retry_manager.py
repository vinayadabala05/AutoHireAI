"""Unit tests for `app.application_state.retry_manager.RetryManager`."""

from datetime import UTC, datetime

from app.application_state.models import ApplicationState, ApplicationStatus
from app.application_state.retry_manager import RetryManager
from app.graph.retry import FixedDelayRetryPolicy, NoRetryPolicy
from tests.job_discovery_fixtures import sample_job


def _state(retry_count: int = 0, max_retries: int = 3) -> ApplicationState:
    now = datetime.now(UTC)
    job = sample_job()
    return ApplicationState(
        job_id="job-1",
        job=job,
        company=job.company,
        title=job.title,
        status=ApplicationStatus.FAILED,
        created_at=now,
        updated_at=now,
        retry_count=retry_count,
        max_retries=max_retries,
    )


def test_can_retry_true_within_budget() -> None:
    manager = RetryManager()
    assert manager.can_retry(_state(retry_count=0)) is True


def test_can_retry_false_when_state_max_retries_exhausted() -> None:
    manager = RetryManager()
    assert manager.can_retry(_state(retry_count=3, max_retries=3)) is False


def test_can_retry_false_when_policy_max_retries_exhausted() -> None:
    manager = RetryManager(policy=NoRetryPolicy())
    assert manager.can_retry(_state(retry_count=0, max_retries=10)) is False


def test_next_delay_seconds_uses_policy() -> None:
    manager = RetryManager(policy=FixedDelayRetryPolicy(5.0))
    assert manager.next_delay_seconds(_state(retry_count=0)) == 5.0
