"""Data-access layer: one repository class per model, all sharing `BaseRepository`'s
generic CRUD. See `app/repositories/base.py` for the shared implementation.
"""

from app.repositories.activity_log import ActivityLogRepository
from app.repositories.application import ApplicationEventRepository, ApplicationRepository
from app.repositories.base import BaseRepository
from app.repositories.company import CompanyRepository
from app.repositories.cover_letter import CoverLetterRepository
from app.repositories.interview import (
    BehaviorAnswerRepository,
    InterviewRepository,
    TechnicalAnswerRepository,
)
from app.repositories.job import JobRepository
from app.repositories.notification import NotificationRepository
from app.repositories.profile import (
    CertificateRepository,
    EducationRepository,
    ExperienceRepository,
    GithubRepositoryRepository,
    ProjectRepository,
    SkillRepository,
)
from app.repositories.resume import ResumeRepository, ResumeVersionRepository
from app.repositories.user import UserRepository

__all__ = [
    "ActivityLogRepository",
    "ApplicationEventRepository",
    "ApplicationRepository",
    "BaseRepository",
    "BehaviorAnswerRepository",
    "CertificateRepository",
    "CompanyRepository",
    "CoverLetterRepository",
    "EducationRepository",
    "ExperienceRepository",
    "GithubRepositoryRepository",
    "InterviewRepository",
    "JobRepository",
    "NotificationRepository",
    "ProjectRepository",
    "ResumeRepository",
    "ResumeVersionRepository",
    "SkillRepository",
    "TechnicalAnswerRepository",
    "UserRepository",
]
