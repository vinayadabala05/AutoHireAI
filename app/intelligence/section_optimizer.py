"""Deterministic resume section ordering.

Classifies the job into a broad category from its keyword profile, then
applies a fixed section order per category. See docs/resume_intelligence.md
for the full rule table and rationale.
"""

from app.intelligence.models import (
    ExperienceRanking,
    JobAnalysis,
    ProjectRanking,
    SectionPlan,
    SkillMatch,
)

_AI_ML_ORDER = ["Summary", "Skills", "Projects", "Experience", "Education", "Certificates"]
_BACKEND_ORDER = ["Summary", "Experience", "Projects", "Skills", "Education", "Certificates"]
_EARLY_CAREER_ORDER = ["Summary", "Projects", "Skills", "Experience", "Education", "Certificates"]

_AI_ML_RATIO_THRESHOLD = 0.3
_STRONG_EXPERIENCE_SCORE = 60.0


class SectionOptimizer:
    def optimize(
        self,
        job_analysis: JobAnalysis,
        skill_match: SkillMatch,
        project_rankings: list[ProjectRanking],
        experience_rankings: list[ExperienceRanking],
    ) -> SectionPlan:
        ai_ml_count = len(job_analysis.keywords.ai_ml)
        technical_count = len(job_analysis.keywords.all_technical()) or 1
        ai_ml_ratio = ai_ml_count / technical_count

        if ai_ml_ratio >= _AI_ML_RATIO_THRESHOLD:
            return SectionPlan(
                order=_AI_ML_ORDER,
                reasoning=(
                    f"{ai_ml_count} of {technical_count} technical keywords in this job are "
                    f"AI/ML-related (>= {_AI_ML_RATIO_THRESHOLD:.0%}), so Skills and Projects are "
                    "surfaced before Experience to lead with technical depth."
                ),
            )

        has_strong_experience = any(
            ranking.score >= _STRONG_EXPERIENCE_SCORE for ranking in experience_rankings
        )
        if not has_strong_experience:
            return SectionPlan(
                order=_EARLY_CAREER_ORDER,
                reasoning=(
                    "No prior experience scored strongly relevant to this role, so Projects are "
                    "surfaced ahead of Experience to lead with the strongest evidence available."
                ),
            )

        return SectionPlan(
            order=_BACKEND_ORDER,
            reasoning=(
                "This reads as a standard engineering role with relevant prior experience, so "
                "Experience leads immediately after the Summary — the conventional order for this "
                "role type."
            ),
        )
