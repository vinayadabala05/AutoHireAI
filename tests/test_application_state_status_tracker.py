"""Unit tests for `app.application_state.status_tracker.StatusTracker`."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.application_state.exceptions import ApplicationNotFoundError, InvalidTransitionError
from app.application_state.history import ApplicationHistoryStore
from app.application_state.models import ApplicationState, ApplicationStatus
from app.application_state.state_store import ApplicationStateStore
from app.application_state.status_tracker import StatusTracker
from tests.job_discovery_fixtures import sample_job


def _tracker(tmp_path: Path) -> tuple[StatusTracker, ApplicationStateStore]:
    store = ApplicationStateStore(path=tmp_path / "state.json")
    history = ApplicationHistoryStore(path=tmp_path / "history.jsonl")
    return StatusTracker(store, history), store


def _seed(store: ApplicationStateStore, job_id: str = "job-1") -> None:
    now = datetime.now(UTC)
    job = sample_job()
    store.save(
        ApplicationState(
            job_id=job_id,
            job=job,
            company=job.company,
            title=job.title,
            status=ApplicationStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
    )


def test_transition_updates_status_and_persists(tmp_path: Path) -> None:
    tracker, store = _tracker(tmp_path)
    _seed(store)

    updated = tracker.transition("job-1", ApplicationStatus.PLANNING)
    assert updated.status is ApplicationStatus.PLANNING
    assert store.get("job-1").status is ApplicationStatus.PLANNING  # type: ignore[union-attr]


def test_transition_records_history(tmp_path: Path) -> None:
    tracker, store = _tracker(tmp_path)
    _seed(store)

    tracker.transition("job-1", ApplicationStatus.PLANNING, detail="starting")
    history = ApplicationHistoryStore(path=tmp_path / "history.jsonl").load_all()

    assert len(history) == 1
    assert history[0].from_status is ApplicationStatus.PENDING
    assert history[0].to_status is ApplicationStatus.PLANNING
    assert history[0].detail == "starting"


def test_transition_missing_application_raises(tmp_path: Path) -> None:
    tracker, _ = _tracker(tmp_path)
    with pytest.raises(ApplicationNotFoundError):
        tracker.transition("ghost", ApplicationStatus.PLANNING)


def test_transition_invalid_raises(tmp_path: Path) -> None:
    tracker, store = _tracker(tmp_path)
    _seed(store)
    with pytest.raises(InvalidTransitionError):
        tracker.transition("job-1", ApplicationStatus.SUBMITTED)


def test_fast_path_planning_to_submitting_allowed(tmp_path: Path) -> None:
    tracker, store = _tracker(tmp_path)
    _seed(store)

    tracker.transition("job-1", ApplicationStatus.PLANNING)
    updated = tracker.transition("job-1", ApplicationStatus.SUBMITTING)
    assert updated.status is ApplicationStatus.SUBMITTING


def test_submitted_is_terminal_no_outgoing_transitions(tmp_path: Path) -> None:
    tracker, store = _tracker(tmp_path)
    _seed(store)
    tracker.transition("job-1", ApplicationStatus.PLANNING)
    tracker.transition("job-1", ApplicationStatus.SUBMITTING)
    tracker.transition("job-1", ApplicationStatus.SUBMITTED)

    with pytest.raises(InvalidTransitionError):
        tracker.transition("job-1", ApplicationStatus.PENDING)


def test_failed_can_transition_back_to_pending_for_retry(tmp_path: Path) -> None:
    tracker, store = _tracker(tmp_path)
    _seed(store)
    tracker.transition("job-1", ApplicationStatus.PLANNING)
    tracker.transition("job-1", ApplicationStatus.FAILED)

    updated = tracker.transition("job-1", ApplicationStatus.PENDING)
    assert updated.status is ApplicationStatus.PENDING
