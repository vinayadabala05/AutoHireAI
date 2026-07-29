"""Data models for the Sprint 6 cover letter generation engine.

These models describe the generated artifact itself (`CoverLetterDocument`
and its sections) and the inputs/outputs of validation — mirroring the
`app/resume/models.py` convention from Sprint 5. This module only defines
what the *generator* produces, never what it consumes (`CareerProfile`,
`ResumeBlueprint`, `ResumeDocument`), so those upstream sprints can evolve
without this module changing.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class CoverLetterTemplate(StrEnum):
    """The four cover letter templates Sprint 6 ships with.

    Mirrors `app.resume.models.ResumeTemplate` — the same four roles, so a
    caller who generated a resume with one template can request a matching
    cover letter with the same value.
    """

    SOFTWARE_ENGINEER = "software_engineer"
    AI_ENGINEER = "ai_engineer"
    BACKEND_ENGINEER = "backend_engineer"
    RESEARCH_ENGINEER = "research_engineer"


class CoverLetterSectionType(StrEnum):
    """Closed set of section kinds a generated cover letter can contain."""

    GREETING = "Greeting"
    BODY = "Body"
    CLOSING = "Closing"
    SIGNATURE = "Signature"


class CoverLetterSection(BaseModel):
    """One rendered section of a cover letter: a kind plus Markdown body."""

    section_type: CoverLetterSectionType
    title: str
    content: str
    order: int = Field(ge=0)


class CoverLetterDocument(BaseModel):
    """The structured output of the cover letter generation pipeline.

    `formatter.py` turns this into Markdown and `renderer.py` turns that
    Markdown into HTML — this model is the single source of truth both
    exporters read from, so Markdown and HTML output can never drift apart.
    """

    full_name: str
    contact_line: str
    date_line: str
    company_name: str
    hiring_manager: str | None = None
    job_title: str
    template: CoverLetterTemplate
    sections: list[CoverLetterSection] = Field(default_factory=list)
    generated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)

    def section(self, section_type: CoverLetterSectionType) -> CoverLetterSection | None:
        for section in self.sections:
            if section.section_type is section_type:
                return section
        return None


class CoverLetterValidationIssue(BaseModel):
    """A single validation finding, at either error or warning severity."""

    code: str
    field: str
    message: str
    severity: str = "error"


class CoverLetterValidationResult(BaseModel):
    """Aggregate validation outcome for a `CoverLetterDocument`."""

    is_valid: bool
    issues: list[CoverLetterValidationIssue] = Field(default_factory=list)

    @property
    def errors(self) -> list[CoverLetterValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[CoverLetterValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]


class CoverLetterValidationError(Exception):
    """Raised when `CoverLetterGenerationService` refuses to generate from invalid inputs."""

    def __init__(self, result: CoverLetterValidationResult) -> None:
        self.result = result
        messages = "; ".join(issue.message for issue in result.errors)
        super().__init__(f"Cover letter input validation failed: {messages}")
