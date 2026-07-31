"""Real-Time Job Monitoring Engine.

Continuously monitors supported job portals (Sprint 7), detects newly
posted jobs, filters them against user preferences, prevents duplicate
processing, and triggers the existing pipeline (Sprint 9 Application
Planning -> Sprint 10 Browser Automation, wired through Sprint 8's Graph
Engine). `JobMonitoringService` is the single entrypoint callers should
use.
"""

from app.job_monitoring.cache import JobCache
from app.job_monitoring.deduplication import DuplicateDetector
from app.job_monitoring.dispatcher import JobDispatcher
from app.job_monitoring.exceptions import (
    DispatchError,
    JobMonitoringError,
    MonitoringAlreadyRunningError,
    MonitoringNotRunningError,
    ScanError,
)
from app.job_monitoring.filters import MonitoringJobFilter
from app.job_monitoring.history import MonitoringHistoryStore
from app.job_monitoring.models import (
    DispatchOutcome,
    JobEvent,
    JobEventType,
    MonitoringConfig,
    MonitoringFilterCriteria,
    MonitoringJob,
    MonitoringResult,
    MonitoringStatistics,
    ProcessedJob,
    ProcessingOutcome,
    ScanBatch,
)
from app.job_monitoring.monitor import JobMonitor
from app.job_monitoring.scheduler import MonitoringScheduler
from app.job_monitoring.service import JobMonitoringService
from app.job_monitoring.watcher import PortalWatcher

__all__ = [
    "DispatchError",
    "DispatchOutcome",
    "DuplicateDetector",
    "JobCache",
    "JobDispatcher",
    "JobEvent",
    "JobEventType",
    "JobMonitor",
    "JobMonitoringError",
    "JobMonitoringService",
    "MonitoringAlreadyRunningError",
    "MonitoringConfig",
    "MonitoringFilterCriteria",
    "MonitoringHistoryStore",
    "MonitoringJob",
    "MonitoringJobFilter",
    "MonitoringNotRunningError",
    "MonitoringResult",
    "MonitoringScheduler",
    "MonitoringStatistics",
    "PortalWatcher",
    "ProcessedJob",
    "ProcessingOutcome",
    "ScanBatch",
    "ScanError",
]
