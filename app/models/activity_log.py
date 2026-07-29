"""Append-only audit trail of everything a user (or the system) does.

`user_id` is nullable to allow system-generated entries with no acting
user (e.g. a scheduled job). No `SoftDeleteMixin` for the same reason as
`ApplicationEvent` — an audit log that can be soft-deleted isn't an audit
log.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import ActivityAction

if TYPE_CHECKING:
    from app.models.user import User


class ActivityLog(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "activity_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[ActivityAction] = mapped_column(nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    extra_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User | None"] = relationship(back_populates="activity_logs")

    def __repr__(self) -> str:
        return f"<ActivityLog id={self.id} action={self.action} entity_type={self.entity_type!r}>"
