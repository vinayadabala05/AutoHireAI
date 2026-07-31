"""Structural interfaces for the Job Monitoring Engine."""

from typing import Protocol

from app.browser_automation.models import SubmissionStatus
from app.career_profile.models import CareerProfile
from app.intelligence.models import ResumeBlueprint
from app.job_discovery.models import DiscoveredJob, JobSearchPreferences
from app.job_monitoring.models import (
    DispatchOutcome,
    MonitoringFilterCriteria,
    ProcessedJob,
    ProcessingOutcome,
)

__all__ = ["DispatcherProtocol", "DuplicateDetectorProtocol", "JobFilterProtocol"]


class JobFilterProtocol(Protocol):
    def matches(
        self,
        job: DiscoveredJob,
        criteria: MonitoringFilterCriteria,
        profile: CareerProfile | None = None,
    ) -> bool: ...


class DuplicateDetectorProtocol(Protocol):
    def is_duplicate(self, job: DiscoveredJob) -> bool: ...

    def mark_processed(
        self,
        job: DiscoveredJob,
        outcome: ProcessingOutcome,
        *,
        submission_status: SubmissionStatus | None = None,
        detail: str | None = None,
    ) -> ProcessedJob: ...


class DispatcherProtocol(Protocol):
    async def dispatch(
        self,
        job: DiscoveredJob,
        profile: CareerProfile,
        blueprint: ResumeBlueprint | None = None,
        preferences: JobSearchPreferences | None = None,
    ) -> DispatchOutcome: ...
