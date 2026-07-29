import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import ResumeStatus
from app.schemas.common import SoftDeletableResponse

# --- Resume ---


class ResumeCreate(BaseModel):
    user_id: uuid.UUID
    title: str
    is_master: bool = False


class ResumeUpdate(BaseModel):
    title: str | None = None
    is_master: bool | None = None


class ResumeResponse(SoftDeletableResponse):
    user_id: uuid.UUID
    title: str
    is_master: bool


# --- ResumeVersion ---


class ResumeVersionCreate(BaseModel):
    resume_id: uuid.UUID
    role: str
    company: str | None = None
    generated_at: datetime
    ats_score: float | None = None
    pdf_path: str | None = None
    docx_path: str | None = None
    status: ResumeStatus = ResumeStatus.DRAFT


class ResumeVersionUpdate(BaseModel):
    ats_score: float | None = None
    pdf_path: str | None = None
    docx_path: str | None = None
    status: ResumeStatus | None = None


class ResumeVersionResponse(SoftDeletableResponse):
    resume_id: uuid.UUID
    version_number: int
    role: str
    company: str | None
    generated_at: datetime
    ats_score: float | None
    pdf_path: str | None
    docx_path: str | None
    status: ResumeStatus
