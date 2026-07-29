"""Job postings.

`(source, external_id)` carries a unique constraint even though no scraper
exists yet in this iteration — it's the natural key a future ingestion
pipeline needs to upsert postings idempotently instead of creating
duplicates on every re-fetch.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPKMixin
from app.models.enums import EmploymentType, ExperienceLevel, JobSource, RemoteType

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.company import Company


class Job(Base, UUIDPKMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_job_source_external_id"),)

    company_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(255))
    salary_min: Mapped[float | None] = mapped_column(Numeric(12, 2))
    salary_max: Mapped[float | None] = mapped_column(Numeric(12, 2))
    salary_currency: Mapped[str | None] = mapped_column(String(8))
    employment_type: Mapped[EmploymentType | None] = mapped_column()
    remote_type: Mapped[RemoteType | None] = mapped_column()
    experience_level: Mapped[ExperienceLevel | None] = mapped_column()
    skills: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    source: Mapped[JobSource] = mapped_column(default=JobSource.MANUAL, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(255))
    """The posting's ID on its source platform; null for manually-entered jobs."""
    url: Mapped[str | None] = mapped_column(String(1024))
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    company: Mapped["Company"] = relationship(back_populates="jobs")
    applications: Mapped[list["Application"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Job id={self.id} title={self.title!r}>"
