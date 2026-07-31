"""Cross-scan duplicate detection: has this job already been processed?

Reuses Sprint 7's `content_hash()` (`app.job_discovery.deduplication`)
directly rather than a second hashing scheme — the same normalized
`(title, company, location)` hash Sprint 7 uses to dedup *within* one
fetch is exactly what's needed to recognize the same posting *across*
scans, days apart. `JobCache` (fast path) and `MonitoringHistoryStore`
(durable source of truth) back this: on first use in a process, the cache
and in-memory index are warmed from the full history once, then every
subsequent check is O(1).
"""

from datetime import UTC, datetime

from loguru import logger

from app.browser_automation.models import SubmissionStatus
from app.job_discovery.deduplication import content_hash
from app.job_discovery.models import DiscoveredJob
from app.job_monitoring.cache import JobCache
from app.job_monitoring.history import MonitoringHistoryStore
from app.job_monitoring.models import ProcessedJob, ProcessingOutcome


def _company_title_key(company: str, title: str) -> str:
    return f"{company.strip().lower()}|{title.strip().lower()}"


class DuplicateDetector:
    def __init__(
        self,
        cache: JobCache | None = None,
        history: MonitoringHistoryStore | None = None,
    ) -> None:
        self._cache = cache or JobCache()
        self._history = history or MonitoringHistoryStore()
        self._seen_urls: set[str] = set()
        self._seen_company_titles: set[str] = set()
        self._loaded = False

    def is_duplicate(self, job: DiscoveredJob) -> bool:
        self._ensure_loaded()
        if job.source_url.strip().lower() in self._seen_urls:
            return True
        if content_hash(job) in self._cache:
            return True
        return _company_title_key(job.company, job.title) in self._seen_company_titles

    def mark_processed(
        self,
        job: DiscoveredJob,
        outcome: ProcessingOutcome,
        *,
        submission_status: SubmissionStatus | None = None,
        detail: str | None = None,
    ) -> ProcessedJob:
        self._ensure_loaded()
        processed = ProcessedJob(
            content_hash=content_hash(job),
            source_url=job.source_url,
            company=job.company,
            title=job.title,
            outcome=outcome,
            processed_at=datetime.now(UTC),
            submission_status=submission_status,
            detail=detail,
        )
        self._record(processed)
        self._history.append(processed)
        logger.bind(company=job.company, title=job.title, outcome=outcome.value).info(
            "Recorded processed job."
        )
        return processed

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        for processed in self._history.load_all():
            self._record(processed)
        self._loaded = True

    def _record(self, processed: ProcessedJob) -> None:
        self._cache.add(processed.content_hash)
        self._seen_urls.add(processed.source_url.strip().lower())
        self._seen_company_titles.add(_company_title_key(processed.company, processed.title))
