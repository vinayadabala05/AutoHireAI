"""`PortalWatcher`: polls a single Sprint 7 job-board provider.

A thin wrapper, not a new fetch mechanism — `BaseJobProvider.fetch_jobs()`
(Sprint 7) already does the actual HTTP call; this only tags each result
with when/where it was seen, which `monitor.py` needs to aggregate across
several providers polled concurrently.
"""

from datetime import UTC, datetime

from app.job_discovery.models import JobSearchQuery
from app.job_discovery.providers.base import BaseJobProvider
from app.job_monitoring.models import MonitoringJob


class PortalWatcher:
    def __init__(self, provider: BaseJobProvider) -> None:
        self.provider = provider

    async def poll(self, query: JobSearchQuery) -> list[MonitoringJob]:
        jobs = await self.provider.fetch_jobs(query)
        discovered_at = datetime.now(UTC)
        return [
            MonitoringJob(
                job=job, provider_name=self.provider.provider_name, discovered_at=discovered_at
            )
            for job in jobs
        ]
