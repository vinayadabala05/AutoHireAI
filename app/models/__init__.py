"""SQLAlchemy ORM models: the Career Intelligence data layer.

Every model module is imported here so `Base.metadata` sees all tables —
Alembic's `env.py` imports this package (not individual modules) so
`--autogenerate` diffs against the complete schema.
"""

from app.models.activity_log import ActivityLog
from app.models.application import Application, ApplicationEvent
from app.models.company import Company
from app.models.cover_letter import CoverLetter
from app.models.interview import BehaviorAnswer, Interview, TechnicalAnswer
from app.models.job import Job
from app.models.notification import Notification
from app.models.profile import Certificate, Education, Experience, GithubRepository, Project, Skill
from app.models.resume import Resume, ResumeVersion
from app.models.user import User

__all__ = [
    "ActivityLog",
    "Application",
    "ApplicationEvent",
    "Certificate",
    "Company",
    "CoverLetter",
    "Education",
    "Experience",
    "GithubRepository",
    "Interview",
    "BehaviorAnswer",
    "Job",
    "Notification",
    "Project",
    "Resume",
    "ResumeVersion",
    "Skill",
    "TechnicalAnswer",
    "User",
]
