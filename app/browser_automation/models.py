"""Data models for the Sprint 10 Browser Automation Engine."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, SecretStr


class PortalType(StrEnum):
    """The four portals this sprint ships adapters for."""

    LINKEDIN = "linkedin"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    ASHBY = "ashby"


class SubmissionStatus(StrEnum):
    SUBMITTED = "submitted"
    FAILED = "failed"
    PARTIAL = "partial"  # submitted, but one or more questions were left unanswered


class FormFieldType(StrEnum):
    """Known, first-class form fields `FormFiller` can populate deterministically."""

    FULL_NAME = "full_name"
    EMAIL = "email"
    PHONE = "phone"
    ADDRESS = "address"
    EDUCATION = "education"
    EXPERIENCE = "experience"
    SKILLS = "skills"
    WORK_AUTHORIZATION = "work_authorization"
    VISA_SPONSORSHIP = "visa_sponsorship"
    NOTICE_PERIOD = "notice_period"
    SALARY_EXPECTATION = "salary_expectation"
    RESUME_UPLOAD = "resume_upload"
    COVER_LETTER_UPLOAD = "cover_letter_upload"


class QuestionInputType(StrEnum):
    TEXT = "text"
    DROPDOWN = "dropdown"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    YES_NO = "yes_no"


class BrowserConfig(BaseModel):
    """Playwright/Chromium launch configuration."""

    headless: bool = True
    slow_mo_ms: int = Field(default=0, ge=0)
    viewport_width: int = Field(default=1280, gt=0)
    viewport_height: int = Field(default=800, gt=0)
    user_agent: str | None = None
    navigation_timeout_ms: float = Field(default=30_000.0, gt=0)


class LoginCredentials(BaseModel):
    """Portal login credentials, always supplied by the caller — never hardcoded."""

    username: str
    password: SecretStr


class SessionData(BaseModel):
    """A persisted browser session (cookies + local storage) for one portal/account."""

    portal: PortalType
    account_key: str
    storage_state_path: str
    saved_at: datetime
    expires_at: datetime | None = None


class FormFillOptions(BaseModel):
    """Applicant answers not present on `CareerProfile` — supplied per application.

    None of these belong on `CareerProfile` (Sprint 3.5) itself: work
    authorization, visa sponsorship, notice period, and salary expectation
    are per-application (or at least per-employer-policy) facts, not a
    stable part of a candidate's career history.
    """

    work_authorization: str | None = None
    visa_sponsorship_required: bool | None = None
    notice_period: str | None = None
    salary_expectation: str | None = None


class UnsupportedQuestion(BaseModel):
    """A form question `FormFiller` declined to guess an answer for."""

    label: str
    input_type: QuestionInputType
    selector: str
    reason: str


class FormFillResult(BaseModel):
    """Outcome of one `FormFiller.fill()` pass."""

    filled_fields: list[FormFieldType] = Field(default_factory=list)
    unsupported_questions: list[UnsupportedQuestion] = Field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return not self.unsupported_questions


class UploadResult(BaseModel):
    """Outcome of one document upload."""

    field_type: FormFieldType
    file_path: str
    uploaded: bool


class SubmissionResult(BaseModel):
    """The final outcome of one application submission attempt."""

    status: SubmissionStatus
    portal: PortalType
    company: str
    job_id: str
    application_url: str
    application_id: str | None = None
    submitted_at: datetime
    screenshot_path: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
