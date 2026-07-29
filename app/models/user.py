"""The User model: the root entity every other table hangs off of.

A user's entire career profile (education, experience, projects, skills,
resumes, applications, ...) is scoped to their `user_id`. This is the
"single source of truth" the AI layers (not built in this iteration) will
read from and write conclusions back into.
"""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.activity_log import ActivityLog
    from app.models.application import Application
    from app.models.cover_letter import CoverLetter
    from app.models.interview import BehaviorAnswer, TechnicalAnswer
    from app.models.notification import Notification
    from app.models.profile import (
        Certificate,
        Education,
        Experience,
        GithubRepository,
        Project,
        Skill,
    )
    from app.models.resume import Resume


class User(Base, UUIDPKMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    location: Mapped[str | None] = mapped_column(String(255))
    headline: Mapped[str | None] = mapped_column(String(255))
    summary: Mapped[str | None] = mapped_column(String(2000))
    linkedin_url: Mapped[str | None] = mapped_column(String(512))
    portfolio_url: Mapped[str | None] = mapped_column(String(512))
    timezone: Mapped[str | None] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    educations: Mapped[list["Education"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    experiences: Mapped[list["Experience"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    projects: Mapped[list["Project"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    skills: Mapped[list["Skill"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    certificates: Mapped[list["Certificate"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    github_repositories: Mapped[list["GithubRepository"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    resumes: Mapped[list["Resume"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    applications: Mapped[list["Application"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    cover_letters: Mapped[list["CoverLetter"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    behavior_answers: Mapped[list["BehaviorAnswer"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    technical_answers: Mapped[list["TechnicalAnswer"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    activity_logs: Mapped[list["ActivityLog"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
