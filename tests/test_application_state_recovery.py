"""Unit tests for `app.application_state.recovery.RecoveryService`."""

from datetime import UTC, datetime
from pathlib import Path

from app.application_state.history import ApplicationHistoryStore
from app.application_state.models import ApplicationState, ApplicationStatus
from app.application_state.recovery import RecoveryService
from app.application_state.state_store import ApplicationStateStore
from app.application_state.status_tracker import StatusTracker
from tests.application_state_fixtures import (
    blueprint,
    build_monitoring_service,
    planning_service,
    ready_page,
)
from tests.job_discovery_fixtures import sample_job
from tests.resume_fixtures import profile_with_no_skills, sample_career_profile


def _build(tmp_path: Path):
    store = ApplicationStateStore(path=tmp_path / "state.json")
    history = ApplicationHistoryStore(path=tmp_path / "history.jsonl")
    tracker = StatusTracker(store, history)
    return store, tracker


def _seed(store: ApplicationStateStore, job, job_id: str, status: ApplicationStatus) -> None:
    now = datetime.now(UTC)
    store.save(
        ApplicationState(
            job_id=job_id,
            job=job,
            company=job.company,
            title=job.title,
            status=status,
            created_at=now,
            updated_at=now,
        )
    )


async def test_run_one_marks_submitted_on_success(tmp_path: Path) -> None:
    job = sample_job(skills=["Python", "FastAPI", "PostgreSQL"])
    store, tracker = _build(tmp_path)
    _seed(store, job, "job-1", ApplicationStatus.PENDING)
    monitoring = build_monitoring_service(tmp_path, [job], planning_service())
    recovery = RecoveryService(store, tracker, monitoring)

    updated = await recovery.run_one(store.get("job-1"), sample_career_profile(), blueprint())

    assert updated.status is ApplicationStatus.SUBMITTED
    assert updated.submission_status is not None


async def test_run_one_marks_failed_when_dispatch_fails(tmp_path: Path) -> None:
    job = sample_job(skills=["Python", "FastAPI", "PostgreSQL"])
    store, tracker = _build(tmp_path)
    _seed(store, job, "job-1", ApplicationStatus.PENDING)
    monitoring = build_monitoring_service(
        tmp_path, [job], planning_service(apply_score_threshold=0.0)
    )
    recovery = RecoveryService(store, tracker, monitoring)

    updated = await recovery.run_one(store.get("job-1"), profile_with_no_skills(), blueprint())

    assert updated.status is ApplicationStatus.FAILED
    assert updated.last_error is not None


async def test_run_one_marks_failed_when_process_job_raises(tmp_path: Path) -> None:
    job = sample_job(skills=["Python", "FastAPI", "PostgreSQL"])
    store, tracker = _build(tmp_path)
    _seed(store, job, "job-1", ApplicationStatus.PENDING)
    monitoring = build_monitoring_service(tmp_path, [job], planning_service())

    async def _boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("pipeline exploded")

    monitoring.process_job = _boom  # type: ignore[method-assign]
    recovery = RecoveryService(store, tracker, monitoring)

    updated = await recovery.run_one(store.get("job-1"), sample_career_profile(), blueprint())

    assert updated.status is ApplicationStatus.FAILED
    assert "pipeline exploded" in (updated.last_error or "")


async def test_run_one_marks_failed_with_submission_status_when_submission_fails(
    tmp_path: Path,
) -> None:
    """`BrowserAutomationService` can return a FAILED `SubmissionResult` without
    raising (e.g. success couldn't be confirmed on the page) — `JobDispatcher`
    then reports `ProcessingOutcome.FAILED` with a non-`None` submission
    status, distinct from the `DispatchError` (exception-raised) path."""
    job = sample_job(skills=["Python", "FastAPI", "PostgreSQL"])
    store, tracker = _build(tmp_path)
    _seed(store, job, "job-1", ApplicationStatus.PENDING)
    page = ready_page()
    del page.selector_counts["text=Thank you for your interest"]
    monitoring = build_monitoring_service(tmp_path, [job], planning_service(), page=page)
    recovery = RecoveryService(store, tracker, monitoring)

    updated = await recovery.run_one(store.get("job-1"), sample_career_profile(), blueprint())

    assert updated.status is ApplicationStatus.FAILED
    assert updated.submission_status is not None


async def test_recover_pending_only_touches_recoverable_states(tmp_path: Path) -> None:
    submitted_job = sample_job(source_url="https://x/submitted")
    pending_job = sample_job(
        source_url="https://x/pending", skills=["Python", "FastAPI", "PostgreSQL"]
    )
    store, tracker = _build(tmp_path)
    _seed(store, submitted_job, "job-submitted", ApplicationStatus.SUBMITTED)
    _seed(store, pending_job, "job-pending", ApplicationStatus.PENDING)
    monitoring = build_monitoring_service(tmp_path, [pending_job], planning_service())
    recovery = RecoveryService(store, tracker, monitoring)

    report = await recovery.recover_pending(sample_career_profile(), blueprint())

    assert report.recovered_job_ids == ["job-pending"]
    assert report.total_examined == 1
    # Untouched: still SUBMITTED, no re-dispatch attempted.
    assert store.get("job-submitted").status is ApplicationStatus.SUBMITTED  # type: ignore[union-attr]
