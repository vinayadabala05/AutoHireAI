"""Structural interfaces for the Resume Intelligence Engine.

Every concrete class in this package (`JobAnalyzer`, `SkillMatcher`, ...)
satisfies one of these `Protocol`s using deterministic Python logic — no
LLM calls anywhere in this sprint. When an LLM-backed implementation is
added later (e.g. an `LLMJobAnalyzer`), it only needs to satisfy the same
Protocol; `ResumePlanner` and every test that depends on the interface
rather than the concrete class won't need to change.
"""

from typing import Protocol

from app.intelligence.models import (
    CareerContext,
    ExperienceInput,
    ExperienceRanking,
    JobAnalysis,
    JobPostingInput,
    KeywordSet,
    ProjectInput,
    ProjectRanking,
    ResumeBlueprint,
    SectionPlan,
    SkillInput,
    SkillMatch,
)

__all__ = [
    "ExperienceRankerProtocol",
    "JobAnalyzerProtocol",
    "KeywordExtractorProtocol",
    "ProjectRankerProtocol",
    "ResumePlannerProtocol",
    "SectionOptimizerProtocol",
    "SkillMatcherProtocol",
]


class KeywordExtractorProtocol(Protocol):
    def extract(self, text: str) -> KeywordSet: ...


class JobAnalyzerProtocol(Protocol):
    def analyze(self, job: JobPostingInput) -> JobAnalysis: ...


class SkillMatcherProtocol(Protocol):
    def match(
        self,
        user_skills: list[SkillInput],
        required_skills: list[str],
        preferred_skills: list[str],
    ) -> SkillMatch: ...


class ProjectRankerProtocol(Protocol):
    def rank(
        self, projects: list[ProjectInput], job_analysis: JobAnalysis
    ) -> list[ProjectRanking]: ...


class ExperienceRankerProtocol(Protocol):
    def rank(
        self, experiences: list[ExperienceInput], job_analysis: JobAnalysis
    ) -> list[ExperienceRanking]: ...


class SectionOptimizerProtocol(Protocol):
    def optimize(
        self,
        job_analysis: JobAnalysis,
        skill_match: SkillMatch,
        project_rankings: list[ProjectRanking],
        experience_rankings: list[ExperienceRanking],
    ) -> SectionPlan: ...


class ResumePlannerProtocol(Protocol):
    def plan(self, job: JobPostingInput, context: CareerContext) -> ResumeBlueprint: ...
