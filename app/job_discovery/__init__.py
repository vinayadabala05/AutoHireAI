"""Job Discovery Engine.

Fetches job postings from Greenhouse, Lever, Ashby, and Workable job
boards, deduplicates and filters them, and ranks them 0-100 against a
`CareerProfile` (Sprint 3.5) and `ResumeBlueprint` (Sprint 3).
`JobDiscoveryService` is the single entrypoint callers should use.

No browser automation, no LinkedIn/Indeed scraping, no Selenium/Playwright
— every provider talks to a documented, public job-board JSON API over
plain HTTP. See `docs/job_discovery.md` for the extension path to
LinkedIn/Indeed once (and if) an authorized API integration exists.
"""

from app.job_discovery.exceptions import (
    InvalidJobPayloadError,
    JobDiscoveryError,
    ProviderFetchError,
    ProviderNotFoundError,
)
from app.job_discovery.models import (
    DeduplicationResult,
    DiscoveredJob,
    JobFilterCriteria,
    JobProviderName,
    JobRankingExplanation,
    JobRankingResult,
    JobSearchPreferences,
    JobSearchQuery,
    PollingRegistration,
)
from app.job_discovery.service import JobDiscoveryService

__all__ = [
    "DeduplicationResult",
    "DiscoveredJob",
    "InvalidJobPayloadError",
    "JobDiscoveryError",
    "JobDiscoveryService",
    "JobFilterCriteria",
    "JobProviderName",
    "JobRankingExplanation",
    "JobRankingResult",
    "JobSearchPreferences",
    "JobSearchQuery",
    "PollingRegistration",
    "ProviderFetchError",
    "ProviderNotFoundError",
]
