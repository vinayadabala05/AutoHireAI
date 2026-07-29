import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import EmploymentType, ExperienceLevel, JobSource, RemoteType
from app.schemas.common import SoftDeletableResponse


class JobCreate(BaseModel):
    company_id: uuid.UUID
    title: str
    description: str | None = None
    location: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    employment_type: EmploymentType | None = None
    remote_type: RemoteType | None = None
    experience_level: ExperienceLevel | None = None
    skills: list[str] | None = None
    source: JobSource = JobSource.MANUAL
    external_id: str | None = None
    url: str | None = None
    posted_at: datetime | None = None


class JobUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    location: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    employment_type: EmploymentType | None = None
    remote_type: RemoteType | None = None
    experience_level: ExperienceLevel | None = None
    skills: list[str] | None = None
    url: str | None = None
    posted_at: datetime | None = None


class JobResponse(SoftDeletableResponse):
    company_id: uuid.UUID
    title: str
    description: str | None
    location: str | None
    salary_min: float | None
    salary_max: float | None
    salary_currency: str | None
    employment_type: EmploymentType | None
    remote_type: RemoteType | None
    experience_level: ExperienceLevel | None
    skills: list[str] | None
    source: JobSource
    external_id: str | None
    url: str | None
    posted_at: datetime | None
