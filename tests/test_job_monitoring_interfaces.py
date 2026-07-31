"""Structural tests for `app.job_monitoring.interfaces`."""

from app.job_monitoring.deduplication import DuplicateDetector
from app.job_monitoring.filters import MonitoringJobFilter
from app.job_monitoring.history import MonitoringHistoryStore

_PROTOCOL_MEMBERS = {
    "JobFilterProtocol": ("matches",),
    "DuplicateDetectorProtocol": ("is_duplicate", "mark_processed"),
    "DispatcherProtocol": ("dispatch",),
}


def _satisfies(instance: object, members: tuple[str, ...]) -> bool:
    return all(hasattr(instance, member) for member in members)


def test_monitoring_job_filter_satisfies_protocol() -> None:
    assert _satisfies(MonitoringJobFilter(), _PROTOCOL_MEMBERS["JobFilterProtocol"])


def test_duplicate_detector_satisfies_protocol(tmp_path) -> None:  # noqa: ANN001
    detector = DuplicateDetector(history=MonitoringHistoryStore(path=tmp_path / "h.jsonl"))
    assert _satisfies(detector, _PROTOCOL_MEMBERS["DuplicateDetectorProtocol"])


def test_job_dispatcher_satisfies_protocol() -> None:
    from app.job_monitoring.dispatcher import JobDispatcher

    assert "dispatch" in _PROTOCOL_MEMBERS["DispatcherProtocol"]
    assert hasattr(JobDispatcher, "dispatch")
