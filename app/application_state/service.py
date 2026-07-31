"""Application State Service: the single entrypoint every caller should use.

Orchestrates `ApplicationStateStore` (persistence), `StatusTracker`
(validated lifecycle transitions + history), `RetryManager` (backoff
policy), and `RecoveryService` (re-driving the pipeline), mirroring the
"one facade per subsystem" convention every prior sprint established.
"""

from datetime import UTC, datetime

from loguru import logger

from app.application_state.exceptions import ApplicationNotFoundError, DuplicateSubmissionError
from app.application_state.history import ApplicationHistoryStore
from app.application_state.models import (
    ApplicationState,
    ApplicationStatus,
    RecoveryReport,
    StateTransition,
)
from app.application_state.recovery import RecoveryService
from app.application_state.retry_manager import RetryManager
from app.application_state.state_store import ApplicationStateStore
from app.application_state.status_tracker import StatusTracker
from app.career_profile.models import CareerProfile
from app.intelligence.models import ResumeBlueprint
from app.job_discovery.deduplication import content_hash
from app.job_discovery.models import DiscoveredJob, JobSearchPreferences
from app.job_monitoring.service import JobMonitoringService


class ApplicationStateService:
    def __init__(
        self,
        monitoring_service: JobMonitoringService,
        store: ApplicationStateStore | None = None,
        history: ApplicationHistoryStore | None = None,
        retry_manager: RetryManager | None = None,
    ) -> None:
        self._store = store or ApplicationStateStore()
        self._history = history or ApplicationHistoryStore()
        self._tracker = StatusTracker(self._store, self._history)
        self._retry_manager = retry_manager or RetryManager()
        self._recovery = RecoveryService(self._store, self._tracker, monitoring_service)

    def save_state(
        self,
        job: DiscoveredJob,
        max_retries: int = 3,
    ) -> ApplicationState:
        """Register a job for tracking (idempotent — returns the existing record if present).

        Raises `DuplicateSubmissionError` if this job was already submitted,
        so a restarted caller can never resubmit an already-successful
        application by accident.
        """
        job_id = content_hash(job)
        existing = self._store.get(job_id)
        if existing is not None:
            if existing.status is ApplicationStatus.SUBMITTED:
                raise DuplicateSubmissionError(job_id)
            return existing

        now = datetime.now(UTC)
        state = ApplicationState(
            job_id=job_id,
            job=job,
            company=job.company,
            title=job.title,
            status=ApplicationStatus.PENDING,
            created_at=now,
            updated_at=now,
            max_retries=max_retries,
        )
        self._store.save(state)
        self._history.append(
            StateTransition(
                job_id=job_id,
                company=job.company,
                title=job.title,
                from_status=None,
                to_status=ApplicationStatus.PENDING,
                timestamp=now,
            )
        )
        logger.bind(job_id=job_id, company=job.company).info("Application state created.")
        return state

    def update_status(
        self, job_id: str, status: ApplicationStatus, detail: str | None = None
    ) -> ApplicationState:
        return self._tracker.transition(job_id, status, detail)

    def get_application(self, job_id: str) -> ApplicationState:
        state = self._store.get(job_id)
        if state is None:
            raise ApplicationNotFoundError(job_id)
        return state

    async def retry_failed(
        self,
        profile: CareerProfile,
        blueprint: ResumeBlueprint | None = None,
        preferences: JobSearchPreferences | None = None,
    ) -> list[ApplicationState]:
        """Re-attempt every FAILED application still eligible under the retry policy."""
        results: list[ApplicationState] = []
        for state in self._store.list_by_status(ApplicationStatus.FAILED):
            if not self._retry_manager.can_retry(state):
                logger.bind(job_id=state.job_id, retry_count=state.retry_count).info(
                    "Retry budget exhausted; leaving FAILED."
                )
                continue
            state.retry_count += 1
            self._store.save(state)
            self._tracker.transition(
                state.job_id, ApplicationStatus.PENDING, detail="Retrying after transient failure."
            )
            results.append(await self._recovery.run_one(state, profile, blueprint, preferences))
        return results

    async def recover_pending(
        self,
        profile: CareerProfile,
        blueprint: ResumeBlueprint | None = None,
        preferences: JobSearchPreferences | None = None,
    ) -> RecoveryReport:
        """Resume every application interrupted mid-pipeline (e.g. by a restart)."""
        return await self._recovery.recover_pending(profile, blueprint, preferences)

    def get_history(
        self,
        job_id: str | None = None,
        status: ApplicationStatus | None = None,
        limit: int | None = None,
    ) -> list[StateTransition]:
        return self._history.query(job_id=job_id, status=status, limit=limit)
