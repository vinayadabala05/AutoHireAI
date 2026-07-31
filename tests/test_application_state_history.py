"""Unit tests for `app.application_state.history.ApplicationHistoryStore`."""

from datetime import UTC, datetime
from pathlib import Path

from app.application_state.history import ApplicationHistoryStore
from app.application_state.models import ApplicationStatus, StateTransition


def _transition(job_id: str, to_status: ApplicationStatus) -> StateTransition:
    return StateTransition(
        job_id=job_id,
        company="Acme",
        title="Engineer",
        from_status=ApplicationStatus.PENDING,
        to_status=to_status,
        timestamp=datetime.now(UTC),
    )


def test_append_and_load_all(tmp_path: Path) -> None:
    store = ApplicationHistoryStore(path=tmp_path / "history.jsonl")
    store.append(_transition("job-1", ApplicationStatus.PLANNING))

    assert len(store.load_all()) == 1


def test_load_all_on_missing_file_returns_empty(tmp_path: Path) -> None:
    store = ApplicationHistoryStore(path=tmp_path / "missing.jsonl")
    assert store.load_all() == []


def test_query_filters_by_job_id(tmp_path: Path) -> None:
    store = ApplicationHistoryStore(path=tmp_path / "history.jsonl")
    store.append(_transition("job-1", ApplicationStatus.PLANNING))
    store.append(_transition("job-2", ApplicationStatus.PLANNING))

    results = store.query(job_id="job-1")
    assert len(results) == 1
    assert results[0].job_id == "job-1"


def test_query_filters_by_status(tmp_path: Path) -> None:
    store = ApplicationHistoryStore(path=tmp_path / "history.jsonl")
    store.append(_transition("job-1", ApplicationStatus.PLANNING))
    store.append(_transition("job-1", ApplicationStatus.FAILED))

    results = store.query(status=ApplicationStatus.FAILED)
    assert len(results) == 1
    assert results[0].to_status is ApplicationStatus.FAILED


def test_query_respects_limit(tmp_path: Path) -> None:
    store = ApplicationHistoryStore(path=tmp_path / "history.jsonl")
    for _ in range(5):
        store.append(_transition("job-1", ApplicationStatus.PLANNING))

    assert len(store.query(limit=2)) == 2
