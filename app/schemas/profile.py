"""Create/Update/Response schemas for the user-profile building blocks."""

import uuid
from datetime import date

from pydantic import BaseModel, Field

from app.models.enums import ProjectPriority, SkillCategory
from app.schemas.common import SoftDeletableResponse

# --- Education ---


class EducationCreate(BaseModel):
    user_id: uuid.UUID
    institution: str
    degree: str
    field_of_study: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    gpa: float | None = None
    description: str | None = None


class EducationUpdate(BaseModel):
    institution: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool | None = None
    gpa: float | None = None
    description: str | None = None


class EducationResponse(SoftDeletableResponse):
    user_id: uuid.UUID
    institution: str
    degree: str
    field_of_study: str | None
    start_date: date | None
    end_date: date | None
    is_current: bool
    gpa: float | None
    description: str | None


# --- Experience ---


class ExperienceCreate(BaseModel):
    user_id: uuid.UUID
    company_name: str
    title: str
    location: str | None = None
    start_date: date
    end_date: date | None = None
    is_current: bool = False
    description: str | None = None
    achievements: list[str] | None = None
    technologies: list[str] | None = None


class ExperienceUpdate(BaseModel):
    company_name: str | None = None
    title: str | None = None
    location: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool | None = None
    description: str | None = None
    achievements: list[str] | None = None
    technologies: list[str] | None = None


class ExperienceResponse(SoftDeletableResponse):
    user_id: uuid.UUID
    company_name: str
    title: str
    location: str | None
    start_date: date
    end_date: date | None
    is_current: bool
    description: str | None
    achievements: list[str] | None
    technologies: list[str] | None


# --- Project ---


class ProjectCreate(BaseModel):
    user_id: uuid.UUID
    name: str
    description: str | None = None
    technologies: list[str] | None = None
    achievements: list[str] | None = None
    github_url: str | None = None
    demo_url: str | None = None
    priority: ProjectPriority = ProjectPriority.MEDIUM
    start_date: date | None = None
    end_date: date | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    technologies: list[str] | None = None
    achievements: list[str] | None = None
    github_url: str | None = None
    demo_url: str | None = None
    priority: ProjectPriority | None = None
    start_date: date | None = None
    end_date: date | None = None


class ProjectResponse(SoftDeletableResponse):
    user_id: uuid.UUID
    name: str
    description: str | None
    technologies: list[str] | None
    achievements: list[str] | None
    github_url: str | None
    demo_url: str | None
    priority: ProjectPriority
    start_date: date | None
    end_date: date | None


# --- Skill ---


class SkillCreate(BaseModel):
    user_id: uuid.UUID
    name: str
    category: SkillCategory = SkillCategory.OTHER
    years_experience: float | None = None
    confidence_level: int | None = Field(default=None, ge=1, le=5)


class SkillUpdate(BaseModel):
    name: str | None = None
    category: SkillCategory | None = None
    years_experience: float | None = None
    confidence_level: int | None = Field(default=None, ge=1, le=5)


class SkillResponse(SoftDeletableResponse):
    user_id: uuid.UUID
    name: str
    category: SkillCategory
    years_experience: float | None
    confidence_level: int | None


# --- Certificate ---


class CertificateCreate(BaseModel):
    user_id: uuid.UUID
    name: str
    issuing_organization: str
    issue_date: date | None = None
    expiration_date: date | None = None
    credential_id: str | None = None
    credential_url: str | None = None


class CertificateUpdate(BaseModel):
    name: str | None = None
    issuing_organization: str | None = None
    issue_date: date | None = None
    expiration_date: date | None = None
    credential_id: str | None = None
    credential_url: str | None = None


class CertificateResponse(SoftDeletableResponse):
    user_id: uuid.UUID
    name: str
    issuing_organization: str
    issue_date: date | None
    expiration_date: date | None
    credential_id: str | None
    credential_url: str | None


# --- GithubRepository ---


class GithubRepositoryCreate(BaseModel):
    user_id: uuid.UUID
    name: str
    full_name: str
    description: str | None = None
    url: str
    stars: int = 0
    forks: int = 0
    primary_language: str | None = None
    topics: list[str] | None = None
    is_featured: bool = False
    last_synced_at: date | None = None


class GithubRepositoryUpdate(BaseModel):
    description: str | None = None
    stars: int | None = None
    forks: int | None = None
    primary_language: str | None = None
    topics: list[str] | None = None
    is_featured: bool | None = None
    last_synced_at: date | None = None


class GithubRepositoryResponse(SoftDeletableResponse):
    user_id: uuid.UUID
    name: str
    full_name: str
    description: str | None
    url: str
    stars: int
    forks: int
    primary_language: str | None
    topics: list[str] | None
    is_featured: bool
    last_synced_at: date | None
