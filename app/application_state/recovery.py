"""`RecoveryService`: re-drives one tracked application through the pipeline.

`run_one()` is the single place that actually calls Sprint 11's
`JobMonitoringService.process_job()` (which itself wires Sprint 9's
`ApplicationPlanningService` and, via `JobDispatcher`, Sprint 10's
`BrowserAutomationService`) — shared by both `recover_pending()` (restart
recovery, this module) and `ApplicationStateService.retry_failed()`
(`service.py`), so the two required APIs can never drift apart on how a
job actually gets (re)submitted.
"""

from datetime import UTC, datetime

from loguru import logger

from app.application_state.models import ApplicationState, ApplicationStatus, RecoveryReport
from app.application_state.state_store import ApplicationStateStore
from app.application_state.status_tracker import StatusTracker
from app.browser_automation.models import SubmissionStatus
from app.career_profile.models import CareerProfile
from app.intelligence.models import ResumeBlueprint
from app.job_discovery.models import JobSearchPreferences
from app.job_monitoring.models import ProcessingOutcome
from app.job_monitoring.service import JobMonitoringService


class RecoveryService:
    def __init__(
        self,
        store: ApplicationStateStore,
        tracker: StatusTracker,
        monitoring_service: JobMonitoringService,
    ) -> None:
        self._store = store
        self._tracker = tracker
        self._monitoring_service = monitoring_service

    async def recover_pending(
        self,
        profile: CareerProfile,
        blueprint: ResumeBlueprint | None = None,
        preferences: JobSearchPreferences | None = None,
    ) -> RecoveryReport:
        """Re-drive every application left mid-pipeline (interrupted by a restart)."""
        started_at = datetime.now(UTC)
        recovered: list[str] = []
        failed: list[str] = []
        for state in self._store.list_all():
            if not state.is_recoverable:
                continue
            logger.bind(job_id=state.job_id, status=state.status.value).info(
                "Recovering interrupted application."
            )
            result = await self.run_one(state, profile, blueprint, preferences)
            (recovered if result.status is ApplicationStatus.SUBMITTED else failed).append(
                result.job_id
            )
        return RecoveryReport(
            started_at=started_at,
            ended_at=datetime.now(UTC),
            recovered_job_ids=recovered,
            failed_job_ids=failed,
        )

    async def run_one(
        self,
        state: ApplicationState,
        profile: CareerProfile,
        blueprint: ResumeBlueprint | None = None,
        preferences: JobSearchPreferences | None = None,
    ) -> ApplicationState:
        """Drive one `PENDING`/interrupted state through planning and submission."""
        job_id = state.job_id
        try:
            self._tracker.transition(job_id, ApplicationStatus.PLANNING)
            self._tracker.transition(job_id, ApplicationStatus.SUBMITTING)
            processed = await self._monitoring_service.process_job(
                state.job, profile, blueprint, preferences
            )
        except (
            Exception
        ) as exc:  # noqa: BLE001 - any pipeline failure marks this FAILED, never crashes recovery
            return self._mark_failed(job_id, str(exc))

        if processed.outcome is not ProcessingOutcome.SUBMITTED:
            detail = processed.detail or f"Pipeline outcome: {processed.outcome.value}"
            return self._mark_failed(job_id, detail, submission_status=processed.submission_status)

        current = self._store.get(job_id)
        assert current is not None
        current.submission_status = processed.submission_status
        current.last_error = None
        self._store.save(current)
        return self._tracker.transition(
            job_id, ApplicationStatus.SUBMITTED, detail=processed.detail
        )

    def _mark_failed(
        self, job_id: str, detail: str, submission_status: SubmissionStatus | None = None
    ) -> ApplicationState:
        current = self._store.get(job_id)
        assert current is not None
        current.last_error = detail
        if submission_status is not None:
            current.submission_status = submission_status
        self._store.save(current)
        return self._tracker.transition(job_id, ApplicationStatus.FAILED, detail=detail)
