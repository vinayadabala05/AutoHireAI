"""Declarative base class for all ORM models.

Every model in `app/models/` must inherit from `Base`. Keeping this in its
own module (rather than in `database.py`) avoids circular imports: models
need to import `Base`, and Alembic's `env.py` needs to import `Base.metadata`
plus every model module, without pulling in the engine/session machinery.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base with common audit columns."""

    pass


class UUIDPKMixin:
    """Adds a client-generated UUID primary key.

    Generated in Python (not `server_default=gen_random_uuid()`) so the ID
    is available on the instance immediately after construction, before any
    flush/commit — useful for wiring up related objects in the same
    transaction without a round-trip.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    """Adds `created_at` / `updated_at` columns to a model."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SoftDeleteMixin:
    """Adds a `deleted_at` column for soft deletion.

    Rows are never physically removed by the repository layer — they're
    marked deleted and filtered out of default queries — so referential
    history (applications, activity logs, interview notes) survives a user
    "deleting" a record.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
