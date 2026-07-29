"""Job Discovery Service: the single entrypoint every caller should use.

Orchestrates provider fan-out -> `deduplication.py` -> `filters.py` ->
`ranking.py`, mirroring the "one facade per subsystem, no reaching for
internals" convention every prior sprint established
(`CareerProfileService`, `LLMService`, `ResumeGenerationService`,
`CoverLetterGenerationService`).
"""

import asyncio

from app.career_profile.models import CareerProfile
from app.intelligence.models import ResumeBlueprint
from app.job_discovery.deduplication import JobDeduplicator
from app.job_discovery.filters import JobFilter
from app.job_discovery.models import (
    DiscoveredJob,
    JobFilterCriteria,
    JobRankingResult,
    JobSearchPreferences,
    JobSearchQuery,
)
from app.job_discovery.providers.base import BaseJobProvider
from app.job_discovery.ranking import JobRankingEngine


class JobDiscoveryService:
    def __init__(self, providers: list[BaseJobProvider] | None = None) -> None:
        self._providers = providers or []
        self._deduplicator = JobDeduplicator()
        self._filter = JobFilter()
        self._ranking_engine = JobRankingEngine()

    @property
    def providers(self) -> list[BaseJobProvider]:
        return list(self._providers)

    async def discover(self, query: JobSearchQuery) -> list[DiscoveredJob]:
        """Fetch from every configured provider concurrently and deduplicate.

        A single provider's failure (network error, malformed response)
        does not fail the whole discovery run — its results are simply
        omitted, since the remaining providers' postings are still useful.
        """
        if not self._providers:
            return []
        results = await asyncio.gather(
            *(provider.fetch_jobs(query) for provider in self._providers),
            return_exceptions=True,
        )
        jobs: list[DiscoveredJob] = []
        for result in results:
            if isinstance(result, BaseException):
                continue
            jobs.extend(result)
        return self._deduplicator.deduplicate(jobs).unique_jobs

    def filter_jobs(
        self, jobs: list[DiscoveredJob], criteria: JobFilterCriteria
    ) -> list[DiscoveredJob]:
        return self._filter.apply(jobs, criteria)

    def rank_jobs(
        self,
        jobs: list[DiscoveredJob],
        profile: CareerProfile,
        blueprint: ResumeBlueprint | None = None,
        *,
        preferences: JobSearchPreferences | None = None,
    ) -> list[JobRankingResult]:
        return self._ranking_engine.rank_all(jobs, profile, blueprint, preferences=preferences)

    async def discover_ranked(
        self,
        query: JobSearchQuery,
        profile: CareerProfile,
        blueprint: ResumeBlueprint | None = None,
        *,
        criteria: JobFilterCriteria | None = None,
        preferences: JobSearchPreferences | None = None,
    ) -> list[JobRankingResult]:
        """The full pipeline: discover -> filter -> rank, in one call."""
        jobs = await self.discover(query)
        if criteria is not None:
            jobs = self.filter_jobs(jobs, criteria)
        return self.rank_jobs(jobs, profile, blueprint, preferences=preferences)
