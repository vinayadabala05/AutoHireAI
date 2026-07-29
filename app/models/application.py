"""Application: the join between a `User` and a `Job`, plus its audit trail.

`ApplicationEvent` is an append-only log of everything that happens to an
application (status transitions, notes, emails) — `Application.status`
holds the *current* state for fast filtering, while `ApplicationEvent` rows
answer "what happened, and when" without ever being mutated or deleted.

`ApplicationStatus` is used by both tables, so it's declared once as a
named Postgres ENUM type and shared, rather than re-inferred per column —
sharing the same `sqlalchemy.Enum` instance means Alembic emits exactly one
`CREATE TYPE application_status` instead of colliding on a duplicate name.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPKMixin
from app.models.enums import ApplicationEventType, ApplicationStatus

if TYPE_CHECKING:
    from app.models.cover_letter import CoverLetter
    from app.models.interview import BehaviorAnswer, Interview, TechnicalAnswer
    from app.models.job import Job
    from app.models.resume import ResumeVersion
    from app.models.user import User

application_status_enum = Enum(
    ApplicationStatus, name="application_status", native_enum=True, validate_strings=True
)


class Application(Base, UUIDPKMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_application_user_job"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    resume_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("resume_versions.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        application_status_enum, default=ApplicationStatus.APPLIED, nullable=False, index=True
    )
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    user: Mapped["User"] = relationship(back_populates="applications")
    job: Mapped["Job"] = relationship(back_populates="applications")
    resume_version: Mapped["ResumeVersion | None"] = relationship(back_populates="applications")
    cover_letter: Mapped["CoverLetter | None"] = relationship(
        back_populates="application", cascade="all, delete-orphan", uselist=False
    )
    events: Mapped[list["ApplicationEvent"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationEvent.occurred_at",
    )
    interviews: Mapped[list["Interview"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    behavior_answers: Mapped[list["BehaviorAnswer"]] = relationship(back_populates="application")
    technical_answers: Mapped[list["TechnicalAnswer"]] = relationship(back_populates="application")

    def __repr__(self) -> str:
        return (
            f"<Application id={self.id} user_id={self.user_id} "
            f"job_id={self.job_id} status={self.status}>"
        )


class ApplicationEvent(Base, UUIDPKMixin, TimestampMixin):
    """Append-only; intentionally has no `SoftDeleteMixin` — an audit trail
    that could itself be soft-deleted defeats the point of an audit trail.
    """

    __tablename__ = "application_events"

    application_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    event_type: Mapped[ApplicationEventType] = mapped_column(nullable=False)
    from_status: Mapped[ApplicationStatus | None] = mapped_column(application_status_enum)
    to_status: Mapped[ApplicationStatus | None] = mapped_column(application_status_enum)
    note: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    application: Mapped["Application"] = relationship(back_populates="events")

    def __repr__(self) -> str:
        return (
            f"<ApplicationEvent id={self.id} application_id={self.application_id} "
            f"type={self.event_type}>"
        )
