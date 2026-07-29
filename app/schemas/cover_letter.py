import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import SoftDeletableResponse


class CoverLetterCreate(BaseModel):
    user_id: uuid.UUID
    application_id: uuid.UUID | None = None
    job_id: uuid.UUID | None = None
    title: str
    content: str
    pdf_path: str | None = None
    docx_path: str | None = None
    generated_at: datetime
    version_number: int = 1


class CoverLetterUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    pdf_path: str | None = None
    docx_path: str | None = None


class CoverLetterResponse(SoftDeletableResponse):
    user_id: uuid.UUID
    application_id: uuid.UUID | None
    job_id: uuid.UUID | None
    title: str
    content: str
    pdf_path: str | None
    docx_path: str | None
    generated_at: datetime
    version_number: int
