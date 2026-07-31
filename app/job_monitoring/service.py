"""Job Monitoring Service: the single entrypoint every caller should use.

Orchestrates `JobMonitor` (discover + filter + dedup), `MonitoringScheduler`
(the interval loop), and `JobDispatcher` (trigger the pipeline), mirroring
the "one facade per subsystem" convention every prior sprint established.
"""

import asyncio
from datetime import UTC, datetime

from loguru import logger

from app.application_planning.models import ApplicationDecision
from app.application_planning.service import ApplicationPlanningService
from app.career_profile.models import CareerProfile
from app.intelligence.models import ResumeBlueprint
from app.job_discovery.models import DiscoveredJob, JobSearchPreferences
from app.job_monitoring.deduplication import DuplicateDetector
from app.job_monitoring.dispatcher import JobDispatcher
from app.job_monitoring.exceptions import DispatchError
from app.job_monitoring.models import (
    MonitoringConfig,
    MonitoringResult,
    MonitoringStatistics,
    ProcessedJob,
    ProcessingOutcome,
)
from app.job_monitoring.monitor import JobMonitor
from app.job_monitoring.scheduler import MonitoringScheduler


class JobMonitoringService:
    def __init__(
        self,
        monitor: JobMonitor,
        planning_service: ApplicationPlanningService,
        config: MonitoringConfig,
        dispatcher: JobDispatcher | None = None,
        deduplicator: DuplicateDetector | None = None,
    ) -> None:
        self._monitor = monitor
        self._planning_service = planning_service
        self.config = config
        self._dispatcher = dispatcher
        self._deduplicator = deduplicator or DuplicateDetector()
        self._statistics = MonitoringStatistics()
        self._scheduler = MonitoringScheduler(self._scheduled_scan, config.polling_interval_seconds)
        self._scan_counter = 0
        self._scan_context: dict[str, object] = {}

    @property
    def is_running(self) -> bool:
        return self._scheduler.is_running

    async def start_monitoring(
        self,
        profile: CareerProfile,
        blueprint: ResumeBlueprint | None = None,
        preferences: JobSearchPreferences | None = None,
    ) -> None:
        """Begin scheduled polling at `config.polling_interval_seconds`.

        The same call also supports "continuous monitoring" — simply never
        call `stop_monitoring()`. For a single manual poll instead, call
        `scan_once()` directly without starting the scheduler at all.
        """
        self._scan_context = {
            "profile": profile,
            "blueprint": blueprint,
            "preferences": preferences,
        }
        await self._scheduler.start()

    async def stop_monitoring(self) -> None:
        await self._scheduler.stop()

    async def scan_once(
        self,
        profile: CareerProfile | None = None,
        blueprint: ResumeBlueprint | None = None,
        preferences: JobSearchPreferences | None = None,
    ) -> MonitoringResult:
        """Run exactly one scan across every configured portal (manual polling)."""
        self._scan_counter += 1
        scan_id = f"scan-{self._scan_counter}"
        result = MonitoringResult(scan_id=scan_id, started_at=datetime.now(UTC))
        try:
            batch = await self._monitor.scan(self.config, profile)
            result.jobs_discovered = batch.jobs_discovered
            result.jobs_filtered_out = batch.jobs_filtered_out
            result.jobs_duplicate = batch.jobs_duplicate
            result.jobs_new = len(batch.matched_jobs)

            if self.config.auto_dispatch and profile is not None and batch.matched_jobs:
                processed = await self.process_jobs(
                    batch.matched_jobs, profile, blueprint, preferences
                )
                result.processed_jobs = processed
                result.jobs_submitted = sum(
                    1 for p in processed if p.outcome is ProcessingOutcome.SUBMITTED
                )
                result.jobs_skipped = sum(
                    1 for p in processed if p.outcome is ProcessingOutcome.SKIPPED
                )
                result.jobs_failed = sum(
                    1 for p in processed if p.outcome is ProcessingOutcome.FAILED
                )
        except Exception as exc:
            result.errors.append(str(exc))
            logger.bind(scan_id=scan_id).error("Scan failed: {}", exc)
        result.ended_at = datetime.now(UTC)
        self._statistics.record_scan(result)
        logger.bind(scan_id=scan_id).info(
            "Scan finished in {:.1f}ms: {} new, {} submitted, {} skipped, {} failed.",
            result.latency_ms or 0.0,
            result.jobs_new,
            result.jobs_submitted,
            result.jobs_skipped,
            result.jobs_failed,
        )
        return result

    async def process_job(
        self,
        job: DiscoveredJob,
        profile: CareerProfile,
        blueprint: ResumeBlueprint | None = None,
        preferences: JobSearchPreferences | None = None,
    ) -> ProcessedJob:
        """Run one already-matched job through planning and (if APPLY) dispatch."""
        evaluated = self._planning_service.evaluate_job(
            job, profile, blueprint, preferences=preferences
        )
        if evaluated.decision is ApplicationDecision.SKIP:
            return self._deduplicator.mark_processed(
                job, ProcessingOutcome.SKIPPED, detail="; ".join(evaluated.reasons) or None
            )

        if self._dispatcher is None:
            return self._deduplicator.mark_processed(
                job,
                ProcessingOutcome.SKIPPED,
                detail="Matched and approved, but no dispatcher is configured to submit it.",
            )

        try:
            outcome = await self._dispatcher.dispatch(job, profile, blueprint)
        except DispatchError as exc:
            return self._deduplicator.mark_processed(job, ProcessingOutcome.FAILED, detail=str(exc))

        detail = outcome.error_message or ("; ".join(outcome.reasons) or None)
        return self._deduplicator.mark_processed(
            job, outcome.outcome, submission_status=outcome.submission_status, detail=detail
        )

    async def process_jobs(
        self,
        jobs: list[DiscoveredJob],
        profile: CareerProfile,
        blueprint: ResumeBlueprint | None = None,
        preferences: JobSearchPreferences | None = None,
    ) -> list[ProcessedJob]:
        """Process several matched jobs concurrently, bounded by `max_concurrent_processing`."""
        semaphore = asyncio.Semaphore(self.config.max_concurrent_processing)

        async def _bounded(job: DiscoveredJob) -> ProcessedJob:
            async with semaphore:
                return await self.process_job(job, profile, blueprint, preferences)

        return list(await asyncio.gather(*(_bounded(job) for job in jobs)))

    def get_statistics(self) -> MonitoringStatistics:
        return self._statistics.model_copy()

    async def _scheduled_scan(self) -> None:
        await self.scan_once(**self._scan_context)  # type: ignore[arg-type]
