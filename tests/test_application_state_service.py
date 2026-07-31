"""Unit tests for `app.application_state.service.ApplicationStateService`."""

from pathlib import Path

import pytest

from app.application_state.exceptions import ApplicationNotFoundError, DuplicateSubmissionError
from app.application_state.history import ApplicationHistoryStore
from app.application_state.models import ApplicationStatus
from app.application_state.retry_manager import RetryManager
from app.application_state.service import ApplicationStateService
from app.application_state.state_store import ApplicationStateStore
from app.graph.retry import FixedDelayRetryPolicy
from app.job_discovery.deduplication import content_hash
from tests.application_state_fixtures import blueprint, build_monitoring_service, planning_service
from tests.job_discovery_fixtures import sample_job
from tests.resume_fixtures import profile_with_no_skills, sample_career_profile


def _build_service(
    tmp_path: Path, jobs: list, planning=None, retry_manager: RetryManager | None = None
) -> ApplicationStateService:
    monitoring = build_monitoring_service(tmp_path, jobs, planning or planning_service())
    store = ApplicationStateStore(path=tmp_path / "state.json")
    history = ApplicationHistoryStore(path=tmp_path / "history.jsonl")
    return ApplicationStateService(
        monitoring, store=store, history=history, retry_manager=retry_manager
    )


def test_save_state_creates_pending_record(tmp_path: Path) -> None:
    job = sample_job()
    service = _build_service(tmp_path, [job])

    state = service.save_state(job)
    assert state.status is ApplicationStatus.PENDING
    assert state.job_id == content_hash(job)


def test_save_state_is_idempotent(tmp_path: Path) -> None:
    job = sample_job()
    service = _build_service(tmp_path, [job])

    first = service.save_state(job)
    second = service.save_state(job)
    assert first.job_id == second.job_id


def test_save_state_raises_when_already_submitted(tmp_path: Path) -> None:
    job = sample_job()
    service = _build_service(tmp_path, [job])
    state = service.save_state(job)
    service.update_status(state.job_id, ApplicationStatus.PLANNING)
    service.update_status(state.job_id, ApplicationStatus.SUBMITTING)
    service.update_status(state.job_id, ApplicationStatus.SUBMITTED)

    with pytest.raises(DuplicateSubmissionError):
        service.save_state(job)


def test_update_status_delegates_to_tracker(tmp_path: Path) -> None:
    job = sample_job()
    service = _build_service(tmp_path, [job])
    state = service.save_state(job)

    updated = service.update_status(state.job_id, ApplicationStatus.PLANNING)
    assert updated.status is ApplicationStatus.PLANNING


def test_get_application_returns_state(tmp_path: Path) -> None:
    job = sample_job()
    service = _build_service(tmp_path, [job])
    state = service.save_state(job)

    assert service.get_application(state.job_id).job_id == state.job_id


def test_get_application_raises_when_missing(tmp_path: Path) -> None:
    service = _build_service(tmp_path, [sample_job()])
    with pytest.raises(ApplicationNotFoundError):
        service.get_application("does-not-exist")


async def test_recover_pending_resumes_interrupted_application(tmp_path: Path) -> None:
    job = sample_job(skills=["Python", "FastAPI", "PostgreSQL"])
    service = _build_service(tmp_path, [job])
    state = service.save_state(job)

    report = await service.recover_pending(sample_career_profile(), blueprint())

    assert report.recovered_job_ids == [state.job_id]
    assert service.get_application(state.job_id).status is ApplicationStatus.SUBMITTED


async def test_retry_failed_reprocesses_and_increments_retry_count(tmp_path: Path) -> None:
    job = sample_job(skills=["Python", "FastAPI", "PostgreSQL"])
    service = _build_service(tmp_path, [job])
    state = service.save_state(job)
    service.update_status(state.job_id, ApplicationStatus.PLANNING)
    service.update_status(state.job_id, ApplicationStatus.SUBMITTING)
    service.update_status(state.job_id, ApplicationStatus.FAILED)

    results = await service.retry_failed(sample_career_profile(), blueprint())

    assert len(results) == 1
    assert results[0].status is ApplicationStatus.SUBMITTED
    assert results[0].retry_count == 1


async def test_retry_failed_skips_when_retry_budget_exhausted(tmp_path: Path) -> None:
    job = sample_job(skills=["Python", "FastAPI", "PostgreSQL"])
    service = _build_service(
        tmp_path,
        [job],
        retry_manager=RetryManager(policy=FixedDelayRetryPolicy(0.0, max_retries=0)),
    )
    state = service.save_state(job)
    service.update_status(state.job_id, ApplicationStatus.PLANNING)
    service.update_status(state.job_id, ApplicationStatus.SUBMITTING)
    service.update_status(state.job_id, ApplicationStatus.FAILED)

    results = await service.retry_failed(sample_career_profile(), blueprint())

    assert results == []
    assert service.get_application(state.job_id).status is ApplicationStatus.FAILED


async def test_retry_failed_marks_failed_again_on_second_dispatch_failure(tmp_path: Path) -> None:
    job = sample_job(skills=["Python", "FastAPI", "PostgreSQL"])
    service = _build_service(tmp_path, [job], planning=planning_service(apply_score_threshold=0.0))
    state = service.save_state(job)
    service.update_status(state.job_id, ApplicationStatus.PLANNING)
    service.update_status(state.job_id, ApplicationStatus.SUBMITTING)
    service.update_status(state.job_id, ApplicationStatus.FAILED)

    results = await service.retry_failed(profile_with_no_skills(), blueprint())

    assert len(results) == 1
    assert results[0].status is ApplicationStatus.FAILED
    assert results[0].retry_count == 1


def test_get_history_returns_transitions(tmp_path: Path) -> None:
    job = sample_job()
    service = _build_service(tmp_path, [job])
    state = service.save_state(job)
    service.update_status(state.job_id, ApplicationStatus.PLANNING)

    history = service.get_history(job_id=state.job_id)
    assert len(history) == 2
    assert history[-1].to_status is ApplicationStatus.PLANNING


def test_get_history_filters_by_status(tmp_path: Path) -> None:
    job = sample_job()
    service = _build_service(tmp_path, [job])
    state = service.save_state(job)
    service.update_status(state.job_id, ApplicationStatus.PLANNING)

    history = service.get_history(status=ApplicationStatus.PLANNING)
    assert len(history) == 1
