"""Pydantic models for the Master Career Profile.

Every `*Profile` model here mirrors a Sprint 2 ORM model's fields directly
(`EducationProfile` ↔ `Education`, `ProjectProfile` ↔ `Project`, ...) —
`builder.py` performs a faithful, no-hardcoded-data transformation from the
database rows loaded by `loader.py`. `EmploymentType`/`RemoteType`/
`ExperienceLevel`/`InterviewType`/`SkillCategory`/`ProjectPriority` are
reused directly from `app.models.enums` (a read-only import; Sprint 2 is
untouched) so the profile and the database never drift on vocabulary.
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.enums import (
    EmploymentType,
    InterviewType,
    ProjectPriority,
    RemoteType,
    SkillCategory,
)

__all__ = [
    "ApplicationPreference",
    "CareerProfile",
    "CertificateProfile",
    "CompletenessReport",
    "EducationProfile",
    "ExperienceProfile",
    "GithubProfile",
    "InterviewPreference",
    "PersonalInfo",
    "PreferenceProfile",
    "ProjectProfile",
    "SectionScore",
    "SkillProfile",
    "ValidationIssue",
    "ValidationReport",
]


# --- Profile sections (each mirrors one Sprint 2 ORM model) ---


class PersonalInfo(BaseModel):
    full_name: str
    email: str
    phone: str | None = None
    location: str | None = None
    headline: str | None = None
    summary: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    timezone: str | None = None


class EducationProfile(BaseModel):
    institution: str
    degree: str
    field_of_study: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    gpa: float | None = None
    description: str | None = None


class ExperienceProfile(BaseModel):
    title: str
    company_name: str
    location: str | None = None
    start_date: date
    end_date: date | None = None
    is_current: bool = False
    description: str | None = None
    achievements: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)


class ProjectProfile(BaseModel):
    name: str
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    github_url: str | None = None
    demo_url: str | None = None
    priority: ProjectPriority = ProjectPriority.MEDIUM
    start_date: date | None = None
    end_date: date | None = None


class SkillProfile(BaseModel):
    name: str
    category: SkillCategory = SkillCategory.OTHER
    years_experience: float | None = None
    confidence_level: int | None = None


class CertificateProfile(BaseModel):
    name: str
    issuing_organization: str
    issue_date: date | None = None
    expiration_date: date | None = None
    credential_id: str | None = None
    credential_url: str | None = None


class GithubProfile(BaseModel):
    name: str
    full_name: str
    description: str | None = None
    url: str
    stars: int = 0
    forks: int = 0
    primary_language: str | None = None
    topics: list[str] = Field(default_factory=list)
    is_featured: bool = False
    last_synced_at: date | None = None


# --- Preferences (derived from Application/Job/Interview/Resume history,
#     not a dedicated settings table — Sprint 2 has none. Every field is
#     computed from what actually happened, never fabricated; fields are
#     empty/None when there's no history to derive them from.) ---


class ApplicationPreference(BaseModel):
    total_applications: int = 0
    total_resume_versions: int = 0
    preferred_employment_types: list[EmploymentType] = Field(default_factory=list)
    preferred_remote_types: list[RemoteType] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)
    observed_salary_min: float | None = None
    observed_salary_max: float | None = None


class InterviewPreference(BaseModel):
    total_interviews: int = 0
    preferred_interview_types: list[InterviewType] = Field(default_factory=list)
    average_duration_minutes: float | None = None


class PreferenceProfile(BaseModel):
    application: ApplicationPreference = Field(default_factory=ApplicationPreference)
    interview: InterviewPreference = Field(default_factory=InterviewPreference)


# --- The aggregate profile ---


class CareerProfile(BaseModel):
    """The single source of truth for a user, assembled by `CareerProfileBuilder`.

    Every future AI feature (resume generation, cover letters, interview
    prep, chat, browser automation) reads from this object instead of
    querying the database or hardcoding assumptions about the user.
    """

    user_id: uuid.UUID
    generated_at: datetime
    personal_info: PersonalInfo
    education: list[EducationProfile] = Field(default_factory=list)
    experience: list[ExperienceProfile] = Field(default_factory=list)
    projects: list[ProjectProfile] = Field(default_factory=list)
    skills: list[SkillProfile] = Field(default_factory=list)
    certificates: list[CertificateProfile] = Field(default_factory=list)
    github_repositories: list[GithubProfile] = Field(default_factory=list)
    preferences: PreferenceProfile = Field(default_factory=PreferenceProfile)


# --- Validation & data quality ---


class ValidationIssue(BaseModel):
    field: str
    message: str
    severity: str
    """`"error"` or `"warning"` — nothing about profile completeness is
    fatal to the profile itself, so only a structurally broken field
    (e.g. an empty email) would ever be `"error"`."""


class SectionScore(BaseModel):
    name: str
    score: float
    """0-100, see docs/career_profile.md for the per-section formula."""
    item_count: int


class CompletenessReport(BaseModel):
    sections: list[SectionScore]
    overall_score: float


class ValidationReport(BaseModel):
    is_valid: bool
    issues: list[ValidationIssue]
    completeness: CompletenessReport
