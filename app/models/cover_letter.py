"""Cover letters generated for a user, optionally tied to a specific job/application.

Kept as its own table (not a column on `Application`) because a cover
letter can be drafted before an application exists (e.g. speculative
outreach) — `application_id`/`job_id` are both nullable for that reason.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.user import User


class CoverLetter(Base, UUIDPKMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "cover_letters"
    __table_args__ = (UniqueConstraint("application_id", name="uq_cover_letter_application"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    pdf_path: Mapped[str | None] = mapped_column(String(1024))
    docx_path: Mapped[str | None] = mapped_column(String(1024))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version_number: Mapped[int] = mapped_column(default=1, nullable=False)

    user: Mapped["User"] = relationship(back_populates="cover_letters")
    application: Mapped["Application | None"] = relationship(back_populates="cover_letter")

    def __repr__(self) -> str:
        return f"<CoverLetter id={self.id} title={self.title!r}>"
