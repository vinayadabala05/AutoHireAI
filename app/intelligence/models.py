"""Pydantic value objects for the Resume Intelligence Engine.

Deliberately decoupled from `app.models` (the SQLAlchemy ORM) and
`app.schemas` (the API DTOs) — every component in this package reasons over
plain data, so it's testable with in-memory Python objects and never needs
a database. `career_context.py` is the only module that bridges the two,
translating ORM rows into the `*Input`/`CareerContext` objects defined here.

`ExperienceLevel`/`EmploymentType` are reused directly from `app.models.enums`
(read-only import, Sprint 2 is untouched) since a job analysis produced here
is meant to line up with the same vocabulary a `Job` row would eventually use.
"""

import uuid

from pydantic import BaseModel, Field

from app.models.enums import EmploymentType, ExperienceLevel

__all__ = [
    "CareerContext",
    "CertificateInput",
    "ExperienceInput",
    "ExperienceRanking",
    "JobAnalysis",
    "JobPostingInput",
    "KeywordSet",
    "MissingSkill",
    "ProjectInput",
    "ProjectRanking",
    "ResumeBlueprint",
    "SectionPlan",
    "SkillInput",
    "SkillMatch",
]


# --- Job analysis input/output ---


class JobPostingInput(BaseModel):
    """Raw job posting, already split into its natural sections.

    `requirements`/`responsibilities`/`preferred_skills` are lists of bullet
    strings rather than one free-text blob — this is how job postings are
    naturally structured, and it keeps the analyzer's logic simple and
    deterministic instead of needing sentence-boundary NLP.
    """

    title: str
    description: str = ""
    requirements: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)


class KeywordSet(BaseModel):
    """Categorized keywords found in some piece of text."""

    programming_languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    cloud: list[str] = Field(default_factory=list)
    devops: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    operating_systems: list[str] = Field(default_factory=list)
    ai_ml: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)

    def all_technical(self) -> list[str]:
        """Every non-soft-skill keyword, deduplicated, first-seen order."""
        seen: set[str] = set()
        out: list[str] = []
        for bucket in (
            self.programming_languages,
            self.frameworks,
            self.cloud,
            self.devops,
            self.databases,
            self.tools,
            self.operating_systems,
            self.ai_ml,
        ):
            for keyword in bucket:
                if keyword not in seen:
                    seen.add(keyword)
                    out.append(keyword)
        return out

    def all(self) -> list[str]:
        technical = self.all_technical()
        seen = set(technical)
        return technical + [s for s in self.soft_skills if s not in seen]


class JobAnalysis(BaseModel):
    """Structured extraction of a `JobPostingInput`."""

    title: str
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    experience_level: ExperienceLevel | None = None
    employment_type: EmploymentType | None = None
    keywords: KeywordSet = Field(default_factory=KeywordSet)
    technologies: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    education_requirements: list[str] = Field(default_factory=list)
    certificates: list[str] = Field(default_factory=list)


# --- Skill matching ---


class MissingSkill(BaseModel):
    name: str
    importance: str
    """`"required"` or `"preferred"` — which side of the job posting asked for it."""


class SkillMatch(BaseModel):
    exact_matches: list[str] = Field(default_factory=list)
    related_matches: list[str] = Field(default_factory=list)
    missing_skills: list[MissingSkill] = Field(default_factory=list)
    coverage_percentage: float
    weighted_score: float


# --- Project / experience ranking ---


class ProjectRanking(BaseModel):
    project_id: uuid.UUID | None = None
    name: str
    confidence: float
    matched_keywords: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class ExperienceRanking(BaseModel):
    experience_id: uuid.UUID | None = None
    title: str
    company_name: str
    score: float
    reasons: list[str] = Field(default_factory=list)


# --- Section planning ---


class SectionPlan(BaseModel):
    order: list[str]
    reasoning: str


# --- Final output ---


class ResumeBlueprint(BaseModel):
    match_score: float
    recommended_projects: list[ProjectRanking]
    recommended_skills: list[str]
    missing_skills: list[MissingSkill]
    resume_sections: list[str]
    reasoning: list[str]


# --- Career context: plain value objects mirroring the user's DB profile ---


class SkillInput(BaseModel):
    name: str
    years_experience: float | None = None


class ProjectInput(BaseModel):
    id: uuid.UUID | None = None
    name: str
    description: str = ""
    technologies: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    priority: str = "medium"
    is_ongoing: bool = False


class ExperienceInput(BaseModel):
    id: uuid.UUID | None = None
    title: str
    company_name: str
    description: str = ""
    technologies: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    is_current: bool = False
    years_ago_ended: float = 0.0
    """0 for a current role; otherwise elapsed years since `end_date`."""


class CertificateInput(BaseModel):
    name: str


class CareerContext(BaseModel):
    """Everything the planner needs about one user, sourced from the DB."""

    user_id: uuid.UUID | None = None
    full_name: str = ""
    skills: list[SkillInput] = Field(default_factory=list)
    projects: list[ProjectInput] = Field(default_factory=list)
    experiences: list[ExperienceInput] = Field(default_factory=list)
    certificates: list[CertificateInput] = Field(default_factory=list)
