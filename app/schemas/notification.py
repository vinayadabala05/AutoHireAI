import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import NotificationChannel, NotificationType
from app.schemas.common import SoftDeletableResponse


class NotificationCreate(BaseModel):
    user_id: uuid.UUID
    type: NotificationType
    channel: NotificationChannel = NotificationChannel.IN_APP
    title: str
    message: str
    related_entity_type: str | None = None
    related_entity_id: uuid.UUID | None = None
    sent_at: datetime | None = None


class NotificationUpdate(BaseModel):
    is_read: bool | None = None
    read_at: datetime | None = None


class NotificationResponse(SoftDeletableResponse):
    user_id: uuid.UUID
    type: NotificationType
    channel: NotificationChannel
    title: str
    message: str
    is_read: bool
    read_at: datetime | None
    related_entity_type: str | None
    related_entity_id: uuid.UUID | None
    sent_at: datetime | None
