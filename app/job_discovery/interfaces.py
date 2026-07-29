"""Structural interfaces for the Job Discovery Engine.

Every concrete class in this package satisfies one of these `Protocol`s.
`JobProviderProtocol` in particular is the extension point: LinkedIn or
Indeed integrations only need a class satisfying this shape (plus
self-registration — see `providers/base.py`) to plug into
`JobDiscoveryService` with no change to the service, ranking, filtering, or
deduplication code.
"""

from typing import Protocol

from app.career_profile.models import CareerProfile
from app.intelligence.models import ResumeBlueprint
from app.job_discovery.models import (
    DeduplicationResult,
    DiscoveredJob,
    JobFilterCriteria,
    JobProviderName,
    JobRankingResult,
    JobSearchPreferences,
    JobSearchQuery,
)
from app.models.enums import JobSource

__all__ = [
    "JobDeduplicatorProtocol",
    "JobFilterProtocol",
    "JobProviderProtocol",
    "JobRankingEngineProtocol",
]


class JobProviderProtocol(Protocol):
    @property
    def provider_name(self) -> JobProviderName: ...

    @property
    def source(self) -> JobSource: ...

    async def fetch_jobs(self, query: JobSearchQuery) -> list[DiscoveredJob]: ...

    async def health_check(self) -> bool: ...


class JobRankingEngineProtocol(Protocol):
    def rank(
        self,
        job: DiscoveredJob,
        profile: CareerProfile,
        blueprint: ResumeBlueprint | None = None,
        *,
        preferences: JobSearchPreferences | None = None,
    ) -> JobRankingResult: ...


class JobDeduplicatorProtocol(Protocol):
    def deduplicate(self, jobs: list[DiscoveredJob]) -> DeduplicationResult: ...


class JobFilterProtocol(Protocol):
    def apply(
        self, jobs: list[DiscoveredJob], criteria: JobFilterCriteria
    ) -> list[DiscoveredJob]: ...
