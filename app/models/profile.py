"""Career-profile building blocks owned by a `User`.

Grouped in one module because they share the same shape (a simple
`user_id`-scoped child table with no further children of their own) — the
resume-generation layer will read across all of these to assemble a
candidate's full profile.
"""

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    ARRAY,
    Date,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPKMixin
from app.models.enums import ProjectPriority, SkillCategory

if TYPE_CHECKING:
    from app.models.user import User


class Education(Base, UUIDPKMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "educations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    institution: Mapped[str] = mapped_column(String(255), nullable=False)
    degree: Mapped[str] = mapped_column(String(255), nullable=False)
    field_of_study: Mapped[str | None] = mapped_column(String(255))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(default=False, nullable=False)
    gpa: Mapped[float | None] = mapped_column(Numeric(3, 2))
    description: Mapped[str | None] = mapped_column(Text)

    user: Mapped["User"] = relationship(back_populates="educations")

    def __repr__(self) -> str:
        return f"<Education id={self.id} institution={self.institution!r}>"


class Experience(Base, UUIDPKMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "experiences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255))
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(default=False, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    achievements: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    technologies: Mapped[list[str] | None] = mapped_column(ARRAY(String))

    user: Mapped["User"] = relationship(back_populates="experiences")

    def __repr__(self) -> str:
        return f"<Experience id={self.id} title={self.title!r} company={self.company_name!r}>"


class Project(Base, UUIDPKMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "projects"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    technologies: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    achievements: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    github_url: Mapped[str | None] = mapped_column(String(512))
    demo_url: Mapped[str | None] = mapped_column(String(512))
    priority: Mapped[ProjectPriority] = mapped_column(
        default=ProjectPriority.MEDIUM, nullable=False
    )
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)

    user: Mapped["User"] = relationship(back_populates="projects")

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name!r}>"


class Skill(Base, UUIDPKMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "skills"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_skill_user_name"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[SkillCategory] = mapped_column(default=SkillCategory.OTHER, nullable=False)
    years_experience: Mapped[float | None] = mapped_column(Numeric(4, 1))
    confidence_level: Mapped[int | None] = mapped_column(SmallInteger)
    """1-5 self-rated confidence; validated at the schema layer, not the DB."""

    user: Mapped["User"] = relationship(back_populates="skills")

    def __repr__(self) -> str:
        return f"<Skill id={self.id} name={self.name!r}>"


class Certificate(Base, UUIDPKMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "certificates"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    issuing_organization: Mapped[str] = mapped_column(String(255), nullable=False)
    issue_date: Mapped[date | None] = mapped_column(Date)
    expiration_date: Mapped[date | None] = mapped_column(Date)
    credential_id: Mapped[str | None] = mapped_column(String(255))
    credential_url: Mapped[str | None] = mapped_column(String(512))

    user: Mapped["User"] = relationship(back_populates="certificates")

    def __repr__(self) -> str:
        return f"<Certificate id={self.id} name={self.name!r}>"


class GithubRepository(Base, UUIDPKMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "github_repositories"
    __table_args__ = (
        UniqueConstraint("user_id", "full_name", name="uq_github_repository_user_full_name"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    """e.g. `octocat/hello-world` — unique per user, used for dedup on re-sync."""
    description: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    stars: Mapped[int] = mapped_column(default=0, nullable=False)
    forks: Mapped[int] = mapped_column(default=0, nullable=False)
    primary_language: Mapped[str | None] = mapped_column(String(64))
    topics: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    is_featured: Mapped[bool] = mapped_column(default=False, nullable=False)
    last_synced_at: Mapped[date | None] = mapped_column(Date)

    user: Mapped["User"] = relationship(back_populates="github_repositories")

    def __repr__(self) -> str:
        return f"<GithubRepository id={self.id} full_name={self.full_name!r}>"
