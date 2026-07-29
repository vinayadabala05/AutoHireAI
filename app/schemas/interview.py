import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import InterviewStatus, InterviewType
from app.schemas.common import SoftDeletableResponse

# --- Interview ---


class InterviewCreate(BaseModel):
    application_id: uuid.UUID
    interview_type: InterviewType
    status: InterviewStatus = InterviewStatus.SCHEDULED
    scheduled_at: datetime | None = None
    duration_minutes: int | None = None
    interviewer_name: str | None = None
    location_or_link: str | None = None
    notes: str | None = None


class InterviewUpdate(BaseModel):
    status: InterviewStatus | None = None
    scheduled_at: datetime | None = None
    duration_minutes: int | None = None
    interviewer_name: str | None = None
    location_or_link: str | None = None
    notes: str | None = None
    feedback: str | None = None


class InterviewResponse(SoftDeletableResponse):
    application_id: uuid.UUID
    interview_type: InterviewType
    status: InterviewStatus
    scheduled_at: datetime | None
    duration_minutes: int | None
    interviewer_name: str | None
    location_or_link: str | None
    notes: str | None
    feedback: str | None


# --- BehaviorAnswer ---


class BehaviorAnswerCreate(BaseModel):
    user_id: uuid.UUID
    interview_id: uuid.UUID | None = None
    application_id: uuid.UUID | None = None
    question: str
    answer_text: str
    uses_star_method: bool = False
    rating: int | None = Field(default=None, ge=1, le=5)
    tags: list[str] | None = None


class BehaviorAnswerUpdate(BaseModel):
    answer_text: str | None = None
    uses_star_method: bool | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    tags: list[str] | None = None


class BehaviorAnswerResponse(SoftDeletableResponse):
    user_id: uuid.UUID
    interview_id: uuid.UUID | None
    application_id: uuid.UUID | None
    question: str
    answer_text: str
    uses_star_method: bool
    rating: int | None
    tags: list[str] | None


# --- TechnicalAnswer ---


class TechnicalAnswerCreate(BaseModel):
    user_id: uuid.UUID
    interview_id: uuid.UUID | None = None
    application_id: uuid.UUID | None = None
    question: str
    answer_text: str
    language: str | None = None
    difficulty: str | None = None
    correctness_score: float | None = None
    tags: list[str] | None = None


class TechnicalAnswerUpdate(BaseModel):
    answer_text: str | None = None
    language: str | None = None
    difficulty: str | None = None
    correctness_score: float | None = None
    tags: list[str] | None = None


class TechnicalAnswerResponse(SoftDeletableResponse):
    user_id: uuid.UUID
    interview_id: uuid.UUID | None
    application_id: uuid.UUID | None
    question: str
    answer_text: str
    language: str | None
    difficulty: str | None
    correctness_score: float | None
    tags: list[str] | None
