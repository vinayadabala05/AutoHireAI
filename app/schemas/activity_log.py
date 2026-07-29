import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.enums import ActivityAction
from app.schemas.common import TimestampedResponse

# No Update schema: an audit trail is append-only, never edited.


class ActivityLogCreate(BaseModel):
    user_id: uuid.UUID | None = None
    action: ActivityAction
    entity_type: str
    entity_id: uuid.UUID | None = None
    description: str | None = None
    extra_data: dict[str, Any] | None = None
    ip_address: str | None = None
    occurred_at: datetime


class ActivityLogResponse(TimestampedResponse):
    user_id: uuid.UUID | None
    action: ActivityAction
    entity_type: str
    entity_id: uuid.UUID | None
    description: str | None
    extra_data: dict[str, Any] | None
    ip_address: str | None
    occurred_at: datetime
