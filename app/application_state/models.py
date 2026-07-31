"""Data models for the Sprint 12 Application State & Recovery Engine.

`ApplicationState` embeds the originating `DiscoveredJob` (Sprint 7)
directly rather than storing a thin reference to it — a restart-safe
recovery/retry engine must be able to re-drive the whole pipeline
(`JobMonitoringService.process_job()`, Sprint 11) without re-fetching
anything from a provider, so the full job payload has to be part of the
persisted record.

`ApplicationStatus` models the entire seven-stage lifecycle the sprint
specifies. In practice this service only ever observes the subset that
`JobMonitoringService.process_job()` exposes as boundaries (it evaluates,
then internally builds a resume + cover letter, then submits, as one
atomic call — Sprint 9/10 aren't modified to emit progress from inside
that call). `PLANNING` and `SUBMITTING` are set immediately before each
observable boundary; `RESUME` and `COVER_LETTER` remain valid, orderable
states for a future caller with finer-grained hooks, and `StatusTracker`
enforces the full transition graph regardless of which subset any one
caller drives through.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.browser_automation.models import SubmissionStatus
from app.job_discovery.models import DiscoveredJob


class ApplicationStatus(StrEnum):
    PENDING = "pending"
    PLANNING = "planning"
    RESUME = "resume"
    COVER_LETTER = "cover_letter"
    SUBMITTING = "submitting"
    SUBMITTED = "submitted"
    FAILED = "failed"


TERMINAL_STATUSES = frozenset({ApplicationStatus.SUBMITTED})
"""Statuses `recover_pending()` and `retry_failed()` never touch again."""


class ApplicationState(BaseModel):
    """The persisted, restart-safe record of one job's progress through the pipeline."""

    job_id: str
    job: DiscoveredJob
    company: str
    title: str
    status: ApplicationStatus = ApplicationStatus.PENDING
    created_at: datetime
    updated_at: datetime
    retry_count: int = Field(default=0, ge=0)
    max_retries: int = Field(default=3, ge=0)
    last_error: str | None = None
    submission_status: SubmissionStatus | None = None
    application_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES

    @property
    def is_recoverable(self) -> bool:
        """Interrupted mid-pipeline: neither submitted nor (yet) failed."""
        return self.status not in TERMINAL_STATUSES and self.status is not ApplicationStatus.FAILED


class StateTransition(BaseModel):
    """One entry in the searchable, append-only application history."""

    job_id: str
    company: str
    title: str
    from_status: ApplicationStatus | None
    to_status: ApplicationStatus
    timestamp: datetime
    detail: str | None = None


class RecoveryReport(BaseModel):
    """Summary of one `recover_pending()` run."""

    started_at: datetime
    ended_at: datetime
    recovered_job_ids: list[str] = Field(default_factory=list)
    failed_job_ids: list[str] = Field(default_factory=list)

    @property
    def total_examined(self) -> int:
        return len(self.recovered_job_ids) + len(self.failed_job_ids)
