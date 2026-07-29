"""Pydantic v2 request/response DTOs, decoupled from the ORM models in `app/models/`.

Each entity has three schemas: `*Create` (request body for POST), `*Update`
(request body for PATCH — every field optional), and `*Response` (what's
returned to the client, includes `id`/`created_at`/`updated_at`/`deleted_at`).
Append-only audit tables (`ApplicationEvent`, `ActivityLog`) have no
`*Update` schema since they're never edited after creation.
"""

from app.schemas.activity_log import ActivityLogCreate, ActivityLogResponse
from app.schemas.application import (
    ApplicationCreate,
    ApplicationEventCreate,
    ApplicationEventResponse,
    ApplicationResponse,
    ApplicationUpdate,
)
from app.schemas.company import CompanyCreate, CompanyResponse, CompanyUpdate
from app.schemas.cover_letter import CoverLetterCreate, CoverLetterResponse, CoverLetterUpdate
from app.schemas.interview import (
    BehaviorAnswerCreate,
    BehaviorAnswerResponse,
    BehaviorAnswerUpdate,
    InterviewCreate,
    InterviewResponse,
    InterviewUpdate,
    TechnicalAnswerCreate,
    TechnicalAnswerResponse,
    TechnicalAnswerUpdate,
)
from app.schemas.job import JobCreate, JobResponse, JobUpdate
from app.schemas.notification import NotificationCreate, NotificationResponse, NotificationUpdate
from app.schemas.profile import (
    CertificateCreate,
    CertificateResponse,
    CertificateUpdate,
    EducationCreate,
    EducationResponse,
    EducationUpdate,
    ExperienceCreate,
    ExperienceResponse,
    ExperienceUpdate,
    GithubRepositoryCreate,
    GithubRepositoryResponse,
    GithubRepositoryUpdate,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    SkillCreate,
    SkillResponse,
    SkillUpdate,
)
from app.schemas.resume import (
    ResumeCreate,
    ResumeResponse,
    ResumeUpdate,
    ResumeVersionCreate,
    ResumeVersionResponse,
    ResumeVersionUpdate,
)
from app.schemas.user import UserCreate, UserResponse, UserUpdate

__all__ = [
    "ActivityLogCreate",
    "ActivityLogResponse",
    "ApplicationCreate",
    "ApplicationEventCreate",
    "ApplicationEventResponse",
    "ApplicationResponse",
    "ApplicationUpdate",
    "BehaviorAnswerCreate",
    "BehaviorAnswerResponse",
    "BehaviorAnswerUpdate",
    "CertificateCreate",
    "CertificateResponse",
    "CertificateUpdate",
    "CompanyCreate",
    "CompanyResponse",
    "CompanyUpdate",
    "CoverLetterCreate",
    "CoverLetterResponse",
    "CoverLetterUpdate",
    "EducationCreate",
    "EducationResponse",
    "EducationUpdate",
    "ExperienceCreate",
    "ExperienceResponse",
    "ExperienceUpdate",
    "GithubRepositoryCreate",
    "GithubRepositoryResponse",
    "GithubRepositoryUpdate",
    "InterviewCreate",
    "InterviewResponse",
    "InterviewUpdate",
    "JobCreate",
    "JobResponse",
    "JobUpdate",
    "NotificationCreate",
    "NotificationResponse",
    "NotificationUpdate",
    "ProjectCreate",
    "ProjectResponse",
    "ProjectUpdate",
    "ResumeCreate",
    "ResumeResponse",
    "ResumeUpdate",
    "ResumeVersionCreate",
    "ResumeVersionResponse",
    "ResumeVersionUpdate",
    "SkillCreate",
    "SkillResponse",
    "SkillUpdate",
    "TechnicalAnswerCreate",
    "TechnicalAnswerResponse",
    "TechnicalAnswerUpdate",
    "UserCreate",
    "UserResponse",
    "UserUpdate",
]
