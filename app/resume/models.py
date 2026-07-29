"""Data models for the Sprint 5 resume generation engine.

These models describe the generated artifact itself (`ResumeDocument` and its
sections) and the inputs/outputs of validation. They are deliberately
independent of `ResumeBlueprint` (Sprint 3) and `CareerProfile` (Sprint 3.5) —
this module only defines what the *generator* produces, never what it
consumes, so those upstream sprints can evolve without this module changing.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ResumeTemplate(StrEnum):
    """The four resume templates Sprint 5 ships with."""

    SOFTWARE_ENGINEER = "software_engineer"
    AI_ENGINEER = "ai_engineer"
    BACKEND_ENGINEER = "backend_engineer"
    RESEARCH_ENGINEER = "research_engineer"


class ResumeSectionType(StrEnum):
    """Closed set of section kinds a generated resume can contain.

    Values match the literal strings `ResumeBlueprint.resume_sections`
    (Sprint 3's `SectionOptimizer`) already produces, so blueprint section
    names can be parsed directly into this enum with no translation table.
    """

    SUMMARY = "Summary"
    SKILLS = "Skills"
    PROJECTS = "Projects"
    EXPERIENCE = "Experience"
    EDUCATION = "Education"
    CERTIFICATES = "Certificates"


class ResumeSection(BaseModel):
    """One rendered section of a resume: a heading plus Markdown body."""

    section_type: ResumeSectionType
    title: str
    content: str
    order: int = Field(ge=0)


class ResumeDocument(BaseModel):
    """The structured output of the resume generation pipeline.

    `formatter.py` turns this into Markdown and `renderer.py` turns that
    Markdown into HTML — this model is the single source of truth both
    exporters read from, so Markdown and HTML output can never drift apart.
    """

    full_name: str
    headline: str | None = None
    contact_line: str
    template: ResumeTemplate
    job_title: str | None = None
    match_score: float = Field(ge=0.0, le=100.0)
    sections: list[ResumeSection] = Field(default_factory=list)
    generated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)

    def section(self, section_type: ResumeSectionType) -> ResumeSection | None:
        for section in self.sections:
            if section.section_type is section_type:
                return section
        return None


class ResumeValidationIssue(BaseModel):
    """A single validation finding, at either error or warning severity."""

    code: str
    field: str
    message: str
    severity: str = "error"


class ResumeValidationResult(BaseModel):
    """Aggregate validation outcome for a `ResumeDocument`."""

    is_valid: bool
    issues: list[ResumeValidationIssue] = Field(default_factory=list)

    @property
    def errors(self) -> list[ResumeValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[ResumeValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]


class ResumeValidationError(Exception):
    """Raised when `ResumeGenerationService` refuses to generate from invalid inputs."""

    def __init__(self, result: ResumeValidationResult) -> None:
        self.result = result
        messages = "; ".join(issue.message for issue in result.errors)
        super().__init__(f"Resume input validation failed: {messages}")
