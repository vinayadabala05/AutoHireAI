"""Unit tests for `app.job_monitoring.monitor.JobMonitor`."""

from pathlib import Path

from app.job_discovery.models import JobProviderName
from app.job_monitoring.deduplication import DuplicateDetector
from app.job_monitoring.filters import MonitoringJobFilter
from app.job_monitoring.history import MonitoringHistoryStore
from app.job_monitoring.models import MonitoringConfig, MonitoringFilterCriteria, ProcessingOutcome
from app.job_monitoring.monitor import JobMonitor
from app.job_monitoring.watcher import PortalWatcher
from tests.job_discovery_fixtures import sample_job
from tests.job_monitoring_fixtures import FakeJobProvider


def _monitor(tmp_path: Path, watchers: list[PortalWatcher]) -> tuple[JobMonitor, DuplicateDetector]:
    detector = DuplicateDetector(history=MonitoringHistoryStore(path=tmp_path / "history.jsonl"))
    return JobMonitor(watchers, detector, MonitoringJobFilter()), detector


async def test_scan_aggregates_jobs_from_multiple_providers(tmp_path: Path) -> None:
    watcher_a = PortalWatcher(
        FakeJobProvider(JobProviderName.GREENHOUSE, jobs=[sample_job(source_url="https://a/1")])
    )
    watcher_b = PortalWatcher(
        FakeJobProvider(JobProviderName.LEVER, jobs=[sample_job(source_url="https://b/1")])
    )
    monitor, _ = _monitor(tmp_path, [watcher_a, watcher_b])

    batch = await monitor.scan(MonitoringConfig())

    assert batch.jobs_discovered == 2
    assert len(batch.matched_jobs) == 2


async def test_scan_tolerates_a_failing_watcher(tmp_path: Path) -> None:
    healthy = PortalWatcher(
        FakeJobProvider(JobProviderName.GREENHOUSE, jobs=[sample_job(source_url="https://a/1")])
    )
    failing = PortalWatcher(FakeJobProvider(JobProviderName.LEVER, fail=True))
    monitor, _ = _monitor(tmp_path, [healthy, failing])

    batch = await monitor.scan(MonitoringConfig())

    assert batch.jobs_discovered == 1
    assert len(batch.matched_jobs) == 1


async def test_scan_excludes_duplicates(tmp_path: Path) -> None:
    job = sample_job(source_url="https://a/1")
    watcher = PortalWatcher(FakeJobProvider(jobs=[job]))
    monitor, detector = _monitor(tmp_path, [watcher])

    detector.mark_processed(job, ProcessingOutcome.SUBMITTED)
    batch = await monitor.scan(MonitoringConfig())

    assert batch.jobs_discovered == 1
    assert batch.jobs_duplicate == 1
    assert batch.matched_jobs == []


async def test_scan_excludes_filtered_out_jobs(tmp_path: Path) -> None:
    job = sample_job(company="Acme Corp")
    watcher = PortalWatcher(FakeJobProvider(jobs=[job]))
    monitor, _ = _monitor(tmp_path, [watcher])

    config = MonitoringConfig(
        filter_criteria=MonitoringFilterCriteria(company_blacklist=["Acme Corp"])
    )
    batch = await monitor.scan(config)

    assert batch.jobs_discovered == 1
    assert batch.jobs_filtered_out == 1
    assert batch.matched_jobs == []


async def test_scan_with_no_watchers_returns_empty_batch(tmp_path: Path) -> None:
    monitor, _ = _monitor(tmp_path, [])
    batch = await monitor.scan(MonitoringConfig())
    assert batch.jobs_discovered == 0
    assert batch.matched_jobs == []
