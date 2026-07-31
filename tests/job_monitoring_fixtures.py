"""Shared test fixtures for Sprint 11 Job Monitoring Engine tests."""

from app.job_discovery.models import JobProviderName, JobSearchQuery, JobSource
from app.job_discovery.providers.base import BaseJobProvider
from tests.job_discovery_fixtures import sample_job


class FakeJobProvider(BaseJobProvider):
    """Returns a fixed list of jobs, or raises, for `JobMonitor`/`PortalWatcher` tests."""

    def __init__(
        self,
        provider_name: JobProviderName = JobProviderName.GREENHOUSE,
        jobs: list | None = None,
        fail: bool = False,
    ) -> None:
        super().__init__(board_token="fake")
        self._provider_name = provider_name
        self._jobs = jobs if jobs is not None else [sample_job()]
        self.fail = fail
        self.calls = 0

    @property
    def provider_name(self) -> JobProviderName:
        return self._provider_name

    @property
    def source(self) -> JobSource:
        return JobSource.COMPANY_SITE

    async def fetch_jobs(self, query: JobSearchQuery) -> list:
        self.calls += 1
        if self.fail:
            raise RuntimeError("provider fetch failed")
        return list(self._jobs)
