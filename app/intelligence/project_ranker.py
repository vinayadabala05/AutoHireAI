"""Deterministic project ranking against a job's keyword profile.

No embeddings — ranks by keyword overlap between a project's tech stack
(its explicit `technologies` field plus keywords found in its description)
and the job's required/preferred skills + extracted technologies, with
priority and "still ongoing" as small tie-breaking bonuses. See
docs/resume_intelligence.md for the exact formula.
"""

from app.intelligence.keyword_extractor import KeywordExtractor
from app.intelligence.models import JobAnalysis, ProjectInput, ProjectRanking

_PRIORITY_MULTIPLIER = {"featured": 1.15, "high": 1.05, "medium": 1.0, "low": 0.9}
_ONGOING_BONUS = 5.0
_MAX_REASONS = 6


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


class ProjectRanker:
    def __init__(self, keyword_extractor: KeywordExtractor | None = None) -> None:
        self._keyword_extractor = keyword_extractor or KeywordExtractor()

    def rank(self, projects: list[ProjectInput], job_analysis: JobAnalysis) -> list[ProjectRanking]:
        job_keywords = self._job_keyword_set(job_analysis)
        if not job_keywords:
            return [
                ProjectRanking(
                    project_id=project.id,
                    name=project.name,
                    confidence=0.0,
                    reasons=["No comparable keywords found in the job description."],
                )
                for project in projects
            ]

        rankings = [self._rank_one(project, job_keywords) for project in projects]
        rankings.sort(key=lambda ranking: ranking.confidence, reverse=True)
        return rankings

    def _job_keyword_set(self, job_analysis: JobAnalysis) -> set[str]:
        return {
            _normalize(term)
            for term in [
                *job_analysis.technologies,
                *job_analysis.required_skills,
                *job_analysis.preferred_skills,
            ]
        }

    def _rank_one(self, project: ProjectInput, job_keywords: set[str]) -> ProjectRanking:
        extracted = self._keyword_extractor.extract(project.description).all_technical()
        project_keywords = {_normalize(t) for t in [*project.technologies, *extracted]}

        matched_norm = project_keywords & job_keywords
        ratio = len(matched_norm) / max(1, len(job_keywords))
        score = ratio * 100 * _PRIORITY_MULTIPLIER.get(project.priority, 1.0)
        if project.is_ongoing:
            score += _ONGOING_BONUS
        confidence = round(min(100.0, score), 1)

        # Prefer the project's own declared spelling for display, falling
        # back to the normalized match for keywords found only in the
        # description.
        display_matches = [t for t in project.technologies if _normalize(t) in matched_norm]
        display_matches += sorted(matched_norm - {_normalize(t) for t in display_matches})

        reasons = [f"Contains {keyword}" for keyword in display_matches[:_MAX_REASONS]]
        if not reasons:
            reasons = ["No direct keyword overlap with this job."]

        return ProjectRanking(
            project_id=project.id,
            name=project.name,
            confidence=confidence,
            matched_keywords=display_matches,
            reasons=reasons,
        )
