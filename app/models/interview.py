"""Interviews and the behavioral/technical answers prepared or given for them.

`BehaviorAnswer` and `TechnicalAnswer` double as both a prep bank (answers
drafted ahead of time, `interview_id` null) and interview-specific records
(`interview_id`/`application_id` set once actually used) — that's why both
FKs are nullable rather than requiring an interview to exist first.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, DateTime, ForeignKey, Numeric, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPKMixin
from app.models.enums import InterviewStatus, InterviewType

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.user import User


class Interview(Base, UUIDPKMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "interviews"

    application_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    interview_type: Mapped[InterviewType] = mapped_column(nullable=False)
    status: Mapped[InterviewStatus] = mapped_column(
        default=InterviewStatus.SCHEDULED, nullable=False
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int | None] = mapped_column(SmallInteger)
    interviewer_name: Mapped[str | None] = mapped_column(String(255))
    location_or_link: Mapped[str | None] = mapped_column(String(512))
    notes: Mapped[str | None] = mapped_column(Text)
    feedback: Mapped[str | None] = mapped_column(Text)

    application: Mapped["Application"] = relationship(back_populates="interviews")
    behavior_answers: Mapped[list["BehaviorAnswer"]] = relationship(back_populates="interview")
    technical_answers: Mapped[list["TechnicalAnswer"]] = relationship(back_populates="interview")

    def __repr__(self) -> str:
        return (
            f"<Interview id={self.id} application_id={self.application_id} "
            f"type={self.interview_type}>"
        )


class BehaviorAnswer(Base, UUIDPKMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "behavior_answers"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    interview_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("interviews.id", ondelete="SET NULL"), index=True
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("applications.id", ondelete="SET NULL"), index=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    uses_star_method: Mapped[bool] = mapped_column(default=False, nullable=False)
    rating: Mapped[int | None] = mapped_column(SmallInteger)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))

    user: Mapped["User"] = relationship(back_populates="behavior_answers")
    interview: Mapped["Interview | None"] = relationship(back_populates="behavior_answers")
    application: Mapped["Application | None"] = relationship(back_populates="behavior_answers")

    def __repr__(self) -> str:
        return f"<BehaviorAnswer id={self.id} user_id={self.user_id}>"


class TechnicalAnswer(Base, UUIDPKMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "technical_answers"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    interview_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("interviews.id", ondelete="SET NULL"), index=True
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("applications.id", ondelete="SET NULL"), index=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str | None] = mapped_column(String(64))
    difficulty: Mapped[str | None] = mapped_column(String(32))
    correctness_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))

    user: Mapped["User"] = relationship(back_populates="technical_answers")
    interview: Mapped["Interview | None"] = relationship(back_populates="technical_answers")
    application: Mapped["Application | None"] = relationship(back_populates="technical_answers")

    def __repr__(self) -> str:
        return f"<TechnicalAnswer id={self.id} user_id={self.user_id}>"
