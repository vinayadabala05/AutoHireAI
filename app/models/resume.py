"""Resume and its generated versions.

A `Resume` is a logical container (e.g. "Backend Engineer track"); every
tailored generation of it — for a specific role/company, at a specific
time, scored against an ATS — is a `ResumeVersion`. This split is what lets
"unlimited resume versions" exist without ever overwriting history: nothing
is mutated in place, a new `ResumeVersion` row is appended each time.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPKMixin
from app.models.enums import ResumeStatus

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.user import User


class Resume(Base, UUIDPKMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "resumes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    is_master: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    """The base/master resume other versions are tailored from."""

    user: Mapped["User"] = relationship(back_populates="resumes")
    versions: Mapped[list["ResumeVersion"]] = relationship(
        back_populates="resume",
        cascade="all, delete-orphan",
        order_by="ResumeVersion.version_number.desc()",
    )

    def __repr__(self) -> str:
        return f"<Resume id={self.id} title={self.title!r}>"


class ResumeVersion(Base, UUIDPKMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "resume_versions"
    __table_args__ = (
        UniqueConstraint("resume_id", "version_number", name="uq_resume_version_number"),
    )

    resume_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(nullable=False)
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str | None] = mapped_column(String(255))
    """Target company this version was tailored for, if any."""
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ats_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    pdf_path: Mapped[str | None] = mapped_column(String(1024))
    docx_path: Mapped[str | None] = mapped_column(String(1024))
    status: Mapped[ResumeStatus] = mapped_column(default=ResumeStatus.DRAFT, nullable=False)

    resume: Mapped["Resume"] = relationship(back_populates="versions")
    applications: Mapped[list["Application"]] = relationship(back_populates="resume_version")

    def __repr__(self) -> str:
        return f"<ResumeVersion id={self.id} resume_id={self.resume_id} v={self.version_number}>"
