"""Data models for the Sprint 7 Job Discovery Engine.

`DiscoveredJob` is deliberately named to avoid colliding with the
persistence-layer `app.models.job.Job` (a SQLAlchemy row) — this is a
provider-agnostic DTO for a job posting *before* it is ever persisted,
mirroring how `app.intelligence.models.JobPostingInput` is a plain input
model rather than an ORM row. Shared enums (`EmploymentType`, `RemoteType`,
`ExperienceLevel`, `JobSource`) are imported read-only from
`app.models.enums` — the same enums Sprint 3's `JobAnalysis` already reuses
— so a discovered job and an analyzed job speak the same vocabulary.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import EmploymentType, ExperienceLevel, JobSource, RemoteType


class JobProviderName(StrEnum):
    """Registry key identifying a concrete provider integration.

    Deliberately separate from `JobSource` (the categorical origin stamped
    onto every `DiscoveredJob`): Greenhouse, Lever, Ashby, and Workable are
    four distinct integrations that all fall under the same
    `JobSource.COMPANY_SITE` category — keying anything by `JobSource`
    would collide the moment a second provider shared a category. Lives
    here (not in `providers/base.py`) so `PollingRegistration` below can
    reference it without `providers/base.py` importing back from `models.py`.
    """

    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    ASHBY = "ashby"
    WORKABLE = "workable"


class DiscoveredJob(BaseModel):
    """A single job posting as fetched from a provider, before persistence."""

    title: str
    company: str
    location: str | None = None
    remote_type: RemoteType | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    currency: str | None = None
    employment_type: EmploymentType | None = None
    experience_level: ExperienceLevel | None = None
    description: str = ""
    requirements: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    source: JobSource
    source_url: str
    posted_date: datetime | None = None
    company_logo: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_remote(self) -> bool:
        return self.remote_type is RemoteType.REMOTE

    @property
    def is_hybrid(self) -> bool:
        return self.remote_type is RemoteType.HYBRID

    @property
    def is_onsite(self) -> bool:
        return self.remote_type is RemoteType.ONSITE

    @property
    def salary_display(self) -> str | None:
        if self.salary_min is None and self.salary_max is None:
            return None
        currency = self.currency or ""
        if self.salary_min is not None and self.salary_max is not None:
            return f"{currency} {self.salary_min:,.0f}-{self.salary_max:,.0f}".strip()
        value = self.salary_min if self.salary_min is not None else self.salary_max
        return f"{currency} {value:,.0f}".strip()


class JobSearchQuery(BaseModel):
    """Query parameters a provider uses to fetch candidate postings."""

    keywords: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    remote_only: bool = False
    limit: int = Field(default=50, gt=0)


class JobSearchPreferences(BaseModel):
    """Explicit ranking-preference overrides.

    Every field is optional and falls back to the corresponding
    `CareerProfile.preferences.application` value when unset — see
    `ranking.py`. `preferred_companies`/`excluded_companies` have no
    equivalent in `CareerProfile` (Sprint 3.5) today, so they are only ever
    sourced from an explicit `JobSearchPreferences` the caller supplies.
    """

    preferred_locations: list[str] = Field(default_factory=list)
    preferred_remote_types: list[RemoteType] = Field(default_factory=list)
    salary_floor: float | None = None
    preferred_companies: list[str] = Field(default_factory=list)
    excluded_companies: list[str] = Field(default_factory=list)


class JobRankingExplanation(BaseModel):
    """One scored factor contributing to a job's overall ranking score."""

    factor: str
    score: float = Field(ge=0.0, le=100.0)
    weight: float = Field(ge=0.0, le=1.0)
    detail: str


class JobRankingResult(BaseModel):
    """A ranked job: its overall 0-100 score plus a per-factor explanation."""

    job: DiscoveredJob
    score: float = Field(ge=0.0, le=100.0)
    explanations: list[JobRankingExplanation] = Field(default_factory=list)


class JobFilterCriteria(BaseModel):
    """Filter predicates applied to a list of `DiscoveredJob`.

    `work_arrangement` is a single optional `RemoteType` rather than three
    independent booleans (`remote_only`/`hybrid_only`/`onsite_only`) so a
    caller can never request a contradictory combination (e.g. both remote
    and onsite only) — set it to `RemoteType.REMOTE`/`HYBRID`/`ONSITE` for
    each of the three states the mission describes, or leave it `None` for
    no work-arrangement filtering.
    """

    work_arrangement: RemoteType | None = None
    experience_levels: list[ExperienceLevel] = Field(default_factory=list)
    salary_min: float | None = None
    countries: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class DeduplicationResult(BaseModel):
    """Outcome of deduplicating a batch of `DiscoveredJob`s."""

    unique_jobs: list[DiscoveredJob]
    duplicates_removed: int = Field(ge=0)


class PollingRegistration(BaseModel):
    """A provider registered with the scheduler for future periodic polling.

    No cron/interval execution exists yet in this sprint (see
    `scheduler.py`) — this model only records *intent*: which provider,
    what query, and how often a future scheduler backend should poll it.
    """

    provider_name: JobProviderName
    query: JobSearchQuery
    interval_seconds: int = Field(gt=0)
    last_run_at: datetime | None = None
