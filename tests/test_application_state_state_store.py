"""Unit tests for `app.application_state.state_store.ApplicationStateStore`."""

from datetime import UTC, datetime
from pathlib import Path

from app.application_state.models import ApplicationState, ApplicationStatus
from app.application_state.state_store import ApplicationStateStore
from tests.job_discovery_fixtures import sample_job


def _state(job_id: str = "job-1", status: ApplicationStatus = ApplicationStatus.PENDING):
    now = datetime.now(UTC)
    job = sample_job()
    return ApplicationState(
        job_id=job_id,
        job=job,
        company=job.company,
        title=job.title,
        status=status,
        created_at=now,
        updated_at=now,
    )


def test_save_and_get_roundtrip(tmp_path: Path) -> None:
    store = ApplicationStateStore(path=tmp_path / "state.json")
    store.save(_state())

    fetched = store.get("job-1")
    assert fetched is not None
    assert fetched.job_id == "job-1"


def test_get_missing_returns_none(tmp_path: Path) -> None:
    store = ApplicationStateStore(path=tmp_path / "state.json")
    assert store.get("nope") is None


def test_list_all_and_list_by_status(tmp_path: Path) -> None:
    store = ApplicationStateStore(path=tmp_path / "state.json")
    store.save(_state("job-1", ApplicationStatus.PENDING))
    store.save(_state("job-2", ApplicationStatus.FAILED))

    assert len(store.list_all()) == 2
    assert [s.job_id for s in store.list_by_status(ApplicationStatus.FAILED)] == ["job-2"]


def test_delete_removes_entry(tmp_path: Path) -> None:
    store = ApplicationStateStore(path=tmp_path / "state.json")
    store.save(_state())
    store.delete("job-1")
    assert store.get("job-1") is None


def test_delete_missing_is_noop(tmp_path: Path) -> None:
    store = ApplicationStateStore(path=tmp_path / "state.json")
    store.delete("does-not-exist")  # must not raise


def test_persists_across_store_instances(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    ApplicationStateStore(path=path).save(_state())

    reloaded = ApplicationStateStore(path=path)
    assert reloaded.get("job-1") is not None


def test_load_ignores_blank_file(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text("   ", encoding="utf-8")
    store = ApplicationStateStore(path=path)
    assert store.list_all() == []
