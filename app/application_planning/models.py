"""Data models for the Sprint 9 Application Planning Engine.

Reuses `MissingSkill` from Sprint 3 (`app.intelligence.models`) rather than
inventing a parallel shape — its `importance` field ("required"/
"preferred") is exactly the required-vs-preferred distinction this sprint
needs to evaluate. `ResumeDocument` (Sprint 5) and `CoverLetterDocument`
(Sprint 6) are embedded directly for the same reason.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.cover_letter.models import CoverLetterDocument
from app.intelligence.models import MissingSkill
from app.job_discovery.models import DiscoveredJob
from app.resume.models import ResumeDocument


class ApplicationDecision(StrEnum):
    APPLY = "apply"
    SKIP = "skip"


class ApplicationPriority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MatchEvaluation(BaseModel):
    """The scored outcome of comparing a job against a candidate."""

    match_score: float = Field(ge=0.0, le=100.0)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[MissingSkill] = Field(default_factory=list)
    explanations: list[str] = Field(default_factory=list)

    @property
    def missing_required_skills(self) -> list[MissingSkill]:
        return [skill for skill in self.missing_skills if skill.importance == "required"]

    @property
    def missing_preferred_skills(self) -> list[MissingSkill]:
        return [skill for skill in self.missing_skills if skill.importance == "preferred"]


class EvaluatedJob(BaseModel):
    """The intermediate result of `ApplicationPlanner.evaluate_job()`."""

    job: DiscoveredJob
    evaluation: MatchEvaluation
    decision: ApplicationDecision
    priority: ApplicationPriority
    reasons: list[str] = Field(default_factory=list)


class ApplicationPlan(BaseModel):
    """The final decision record for one job: apply or skip, and why."""

    job_id: str
    company: str
    title: str
    match_score: float = Field(ge=0.0, le=100.0)
    decision: ApplicationDecision
    priority: ApplicationPriority
    reasons: list[str] = Field(default_factory=list)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[MissingSkill] = Field(default_factory=list)
    generated_resume: ResumeDocument | None = None
    generated_cover_letter: CoverLetterDocument | None = None
    timestamp: datetime


class ApplicationPackage(BaseModel):
    """The execution-ready bundle handed off to (future) browser automation."""

    job_id: str
    company: str
    title: str
    resume_document: ResumeDocument
    resume_markdown: str
    cover_letter_document: CoverLetterDocument
    cover_letter_markdown: str
    application_url: str
    generated_at: datetime
