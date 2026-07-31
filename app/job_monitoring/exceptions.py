"""Exception hierarchy for the Job Monitoring Engine.

Mirrors every prior sprint's convention: one base class, specific
subclasses so callers can catch broadly or narrowly.
"""


class JobMonitoringError(Exception):
    """Base class for every exception raised by `app.job_monitoring`."""


class MonitoringAlreadyRunningError(JobMonitoringError):
    """Raised by `start_monitoring()` if scheduled monitoring is already active."""


class MonitoringNotRunningError(JobMonitoringError):
    """Raised by `stop_monitoring()` if no monitoring is currently active."""


class ScanError(JobMonitoringError):
    """Raised when a portal scan cannot complete."""


class DispatchError(JobMonitoringError):
    """Raised when dispatching a matched job through the pipeline fails."""

    def __init__(self, job_id: str, original: BaseException) -> None:
        self.job_id = job_id
        self.original = original
        super().__init__(f"Failed to dispatch job '{job_id}': {original}")
