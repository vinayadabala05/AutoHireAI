import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import ApplicationEventType, ApplicationStatus
from app.schemas.common import SoftDeletableResponse, TimestampedResponse

# --- Application ---


class ApplicationCreate(BaseModel):
    user_id: uuid.UUID
    job_id: uuid.UUID
    resume_version_id: uuid.UUID | None = None
    status: ApplicationStatus = ApplicationStatus.APPLIED
    applied_at: datetime
    notes: str | None = None


class ApplicationUpdate(BaseModel):
    resume_version_id: uuid.UUID | None = None
    status: ApplicationStatus | None = None
    notes: str | None = None


class ApplicationResponse(SoftDeletableResponse):
    user_id: uuid.UUID
    job_id: uuid.UUID
    resume_version_id: uuid.UUID | None
    status: ApplicationStatus
    applied_at: datetime
    notes: str | None


# --- ApplicationEvent ---
# No soft-delete: an append-only audit trail is never marked deleted.


class ApplicationEventCreate(BaseModel):
    application_id: uuid.UUID
    event_type: ApplicationEventType
    from_status: ApplicationStatus | None = None
    to_status: ApplicationStatus | None = None
    note: str | None = None
    occurred_at: datetime


class ApplicationEventResponse(TimestampedResponse):
    application_id: uuid.UUID
    event_type: ApplicationEventType
    from_status: ApplicationStatus | None
    to_status: ApplicationStatus | None
    note: str | None
    occurred_at: datetime
