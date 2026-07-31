"""Data models for the Sprint 11 Real-Time Job Monitoring Engine.

`JobFilterCriteria`/`JobSearchQuery` (Sprint 7) are reused directly rather
than duplicated — `MonitoringFilterCriteria` composes a `JobFilterCriteria`
plus the additional criteria this sprint adds (company blacklist/
whitelist, minimum skill overlap with the candidate's own profile).
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.browser_automation.models import SubmissionStatus
from app.job_discovery.models import (
    DiscoveredJob,
    JobFilterCriteria,
    JobProviderName,
    JobSearchQuery,
)


class JobEventType(StrEnum):
    SCAN_STARTED = "scan_started"
    SCAN_COMPLETED = "scan_completed"
    JOB_DISCOVERED = "job_discovered"
    JOB_FILTERED_OUT = "job_filtered_out"
    JOB_DUPLICATE = "job_duplicate"
    JOB_DISPATCHED = "job_dispatched"
    JOB_SUBMITTED = "job_submitted"
    JOB_SKIPPED = "job_skipped"
    JOB_FAILED = "job_failed"


class ProcessingOutcome(StrEnum):
    SUBMITTED = "submitted"
    SKIPPED = "skipped"  # Application Planning (Sprint 9) decided SKIP
    DUPLICATE = "duplicate"
    FILTERED = "filtered"
    FAILED = "failed"


class MonitoringJob(BaseModel):
    """One job as seen by the monitor: the raw job plus provenance."""

    job: DiscoveredJob
    provider_name: JobProviderName
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProcessedJob(BaseModel):
    """A durable ledger entry: one job's final processing outcome."""

    content_hash: str
    source_url: str
    company: str
    title: str
    outcome: ProcessingOutcome
    processed_at: datetime
    submission_status: SubmissionStatus | None = None
    detail: str | None = None


class JobEvent(BaseModel):
    """One occurrence emitted during monitoring, for structured logging/observers."""

    type: JobEventType
    scan_id: str
    provider_name: JobProviderName | None = None
    job_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    detail: dict[str, Any] = Field(default_factory=dict)


class MonitoringFilterCriteria(BaseModel):
    """Filter predicates for the monitor, beyond Sprint 7's `JobFilterCriteria`."""

    base: JobFilterCriteria = Field(default_factory=JobFilterCriteria)
    company_blacklist: list[str] = Field(default_factory=list)
    company_whitelist: list[str] = Field(default_factory=list)
    min_skill_overlap: int = Field(default=0, ge=0)


class MonitoringConfig(BaseModel):
    """Everything one monitoring run needs: what to poll, how often, how to filter."""

    provider_names: list[JobProviderName] = Field(default_factory=list)
    query: JobSearchQuery = Field(default_factory=JobSearchQuery)
    filter_criteria: MonitoringFilterCriteria = Field(default_factory=MonitoringFilterCriteria)
    polling_interval_seconds: float = Field(default=300.0, gt=0)
    max_concurrent_processing: int = Field(default=3, gt=0)
    auto_dispatch: bool = True


class ScanBatch(BaseModel):
    """The new, filtered, non-duplicate jobs from one scan, plus its raw counts."""

    matched_jobs: list[DiscoveredJob] = Field(default_factory=list)
    jobs_discovered: int = Field(default=0, ge=0)
    jobs_filtered_out: int = Field(default=0, ge=0)
    jobs_duplicate: int = Field(default=0, ge=0)


class DispatchOutcome(BaseModel):
    """The result of running one job through Application Planning -> Browser Automation."""

    outcome: ProcessingOutcome
    reasons: list[str] = Field(default_factory=list)
    submission_status: SubmissionStatus | None = None
    application_url: str | None = None
    error_message: str | None = None


class MonitoringResult(BaseModel):
    """Outcome of one `scan_once()` call."""

    scan_id: str
    started_at: datetime
    ended_at: datetime | None = None
    jobs_discovered: int = 0
    jobs_new: int = 0
    jobs_filtered_out: int = 0
    jobs_duplicate: int = 0
    jobs_submitted: int = 0
    jobs_skipped: int = 0
    jobs_failed: int = 0
    processed_jobs: list[ProcessedJob] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    @property
    def latency_ms(self) -> float | None:
        if self.ended_at is None:
            return None
        return (self.ended_at - self.started_at).total_seconds() * 1000


class MonitoringStatistics(BaseModel):
    """Cumulative counters across every scan since the service started."""

    total_scans: int = Field(default=0, ge=0)
    total_jobs_discovered: int = Field(default=0, ge=0)
    total_jobs_filtered_out: int = Field(default=0, ge=0)
    total_jobs_duplicate: int = Field(default=0, ge=0)
    total_jobs_submitted: int = Field(default=0, ge=0)
    total_jobs_skipped: int = Field(default=0, ge=0)
    total_jobs_failed: int = Field(default=0, ge=0)
    last_scan_at: datetime | None = None
    average_latency_ms: float | None = None

    def record_scan(self, result: MonitoringResult) -> None:
        self.total_scans += 1
        self.total_jobs_discovered += result.jobs_discovered
        self.total_jobs_filtered_out += result.jobs_filtered_out
        self.total_jobs_duplicate += result.jobs_duplicate
        self.total_jobs_submitted += result.jobs_submitted
        self.total_jobs_skipped += result.jobs_skipped
        self.total_jobs_failed += result.jobs_failed
        self.last_scan_at = result.ended_at
        if result.latency_ms is not None:
            if self.average_latency_ms is None:
                self.average_latency_ms = result.latency_ms
            else:
                self.average_latency_ms += (
                    result.latency_ms - self.average_latency_ms
                ) / self.total_scans
