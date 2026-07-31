"""Unit tests for `app.job_monitoring.watcher.PortalWatcher`."""

from app.job_discovery.models import JobProviderName, JobSearchQuery
from app.job_monitoring.watcher import PortalWatcher
from tests.job_discovery_fixtures import sample_job
from tests.job_monitoring_fixtures import FakeJobProvider


async def test_poll_tags_each_job_with_provider_and_timestamp() -> None:
    jobs = [sample_job(source_url="https://a/1"), sample_job(source_url="https://a/2")]
    watcher = PortalWatcher(FakeJobProvider(JobProviderName.LEVER, jobs=jobs))

    monitoring_jobs = await watcher.poll(JobSearchQuery())

    assert len(monitoring_jobs) == 2
    assert all(mj.provider_name is JobProviderName.LEVER for mj in monitoring_jobs)
    assert all(mj.discovered_at is not None for mj in monitoring_jobs)


async def test_poll_propagates_provider_failures() -> None:
    import pytest

    watcher = PortalWatcher(FakeJobProvider(fail=True))
    with pytest.raises(RuntimeError, match="provider fetch failed"):
        await watcher.poll(JobSearchQuery())
