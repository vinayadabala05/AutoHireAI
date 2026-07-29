"""Deterministic experience ranking against a job's keyword and title profile.

Combines three signals into a single 0-100 score: keyword overlap (worth up
to 70 points), job-title similarity (up to 20), and recency (up to 10) — see
docs/resume_intelligence.md for the exact weighting.
"""

import difflib

from app.intelligence.keyword_extractor import KeywordExtractor
from app.intelligence.models import ExperienceInput, ExperienceRanking, JobAnalysis

_KEYWORD_WEIGHT = 70.0
_TITLE_WEIGHT = 20.0
_RECENCY_WEIGHT = 10.0
_TITLE_SIMILARITY_REASON_THRESHOLD = 0.5
_RECENT_YEARS_THRESHOLD = 2.0
_MAX_MATCHED_IN_REASON = 5


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


class ExperienceRanker:
    def __init__(self, keyword_extractor: KeywordExtractor | None = None) -> None:
        self._keyword_extractor = keyword_extractor or KeywordExtractor()

    def rank(
        self, experiences: list[ExperienceInput], job_analysis: JobAnalysis
    ) -> list[ExperienceRanking]:
        job_keywords = self._job_keyword_set(job_analysis)
        rankings = [
            self._rank_one(experience, job_keywords, job_analysis.title)
            for experience in experiences
        ]
        rankings.sort(key=lambda ranking: ranking.score, reverse=True)
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

    def _rank_one(
        self, experience: ExperienceInput, job_keywords: set[str], job_title: str
    ) -> ExperienceRanking:
        extracted = self._keyword_extractor.extract(experience.description).all_technical()
        exp_keywords = {_normalize(t) for t in [*experience.technologies, *extracted]}

        matched = sorted(exp_keywords & job_keywords)
        keyword_ratio = len(matched) / max(1, len(job_keywords)) if job_keywords else 0.0
        keyword_score = keyword_ratio * _KEYWORD_WEIGHT

        title_similarity = difflib.SequenceMatcher(
            None, _normalize(experience.title), _normalize(job_title)
        ).ratio()
        title_score = title_similarity * _TITLE_WEIGHT

        if experience.is_current:
            recency_score = _RECENCY_WEIGHT
        else:
            recency_score = max(0.0, _RECENCY_WEIGHT - experience.years_ago_ended)

        score = round(min(100.0, keyword_score + title_score + recency_score), 1)

        reasons: list[str] = []
        if matched:
            reasons.append(f"Uses {', '.join(matched[:_MAX_MATCHED_IN_REASON])}")
        if title_similarity >= _TITLE_SIMILARITY_REASON_THRESHOLD:
            reasons.append(f"Title closely matches the target role ('{experience.title}')")
        if experience.is_current:
            reasons.append("Current role")
        elif experience.years_ago_ended <= _RECENT_YEARS_THRESHOLD:
            reasons.append("Recent role")
        if not reasons:
            reasons.append("Limited overlap with this job's requirements")

        return ExperienceRanking(
            experience_id=experience.id,
            title=experience.title,
            company_name=experience.company_name,
            score=score,
            reasons=reasons,
        )
