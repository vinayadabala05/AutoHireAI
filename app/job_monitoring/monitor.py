"""`JobMonitor`: one scan across every configured portal.

Polls all `PortalWatcher`s concurrently, then applies duplicate detection
and filtering to produce the `ScanBatch` of genuinely new, matching jobs.
A single watcher's failure doesn't fail the whole scan — its jobs are
simply absent from this round, exactly like Sprint 7's `JobDiscoveryService`
tolerates one provider's failure.
"""

import asyncio

from loguru import logger

from app.career_profile.models import CareerProfile
from app.job_discovery.models import DiscoveredJob
from app.job_monitoring.deduplication import DuplicateDetector
from app.job_monitoring.filters import MonitoringJobFilter
from app.job_monitoring.models import MonitoringConfig, MonitoringJob, ScanBatch
from app.job_monitoring.watcher import PortalWatcher


class JobMonitor:
    def __init__(
        self,
        watchers: list[PortalWatcher],
        deduplicator: DuplicateDetector,
        job_filter: MonitoringJobFilter,
    ) -> None:
        self._watchers = watchers
        self._deduplicator = deduplicator
        self._job_filter = job_filter

    async def scan(
        self, config: MonitoringConfig, profile: CareerProfile | None = None
    ) -> ScanBatch:
        monitoring_jobs = await self._poll_all(config)

        matched: list[DiscoveredJob] = []
        jobs_filtered_out = 0
        jobs_duplicate = 0

        for monitoring_job in monitoring_jobs:
            job = monitoring_job.job
            if self._deduplicator.is_duplicate(job):
                jobs_duplicate += 1
                continue
            if not self._job_filter.matches(job, config.filter_criteria, profile):
                jobs_filtered_out += 1
                continue
            matched.append(job)

        logger.info(
            "Scan complete: {} discovered, {} matched, {} filtered out, {} duplicate.",
            len(monitoring_jobs),
            len(matched),
            jobs_filtered_out,
            jobs_duplicate,
        )
        return ScanBatch(
            matched_jobs=matched,
            jobs_discovered=len(monitoring_jobs),
            jobs_filtered_out=jobs_filtered_out,
            jobs_duplicate=jobs_duplicate,
        )

    async def _poll_all(self, config: MonitoringConfig) -> list[MonitoringJob]:
        results = await asyncio.gather(
            *(watcher.poll(config.query) for watcher in self._watchers), return_exceptions=True
        )
        monitoring_jobs: list[MonitoringJob] = []
        for watcher, result in zip(self._watchers, results, strict=True):
            if isinstance(result, BaseException):
                logger.warning(
                    "Portal watcher '{}' failed: {}", watcher.provider.provider_name.value, result
                )
                continue
            monitoring_jobs.extend(result)
        return monitoring_jobs
