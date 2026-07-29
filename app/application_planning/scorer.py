"""Job match scoring.

Reuses Sprint 7's `JobRankingEngine` for the overall 0-100 score (skill,
experience, location, remote, salary, and company-preference factors —
already weighted and explained) and Sprint 3's `SkillMatcher` directly for
an explicit required-vs-preferred skill breakdown — the same tool Sprint
7's ranking engine already uses internally for its own skill factor,
exposed here as a first-class result rather than folded into one number.
"""

from loguru import logger

from app.application_planning.models import MatchEvaluation
from app.career_profile.models import CareerProfile
from app.intelligence.models import ResumeBlueprint, SkillInput
from app.intelligence.skill_matcher import SkillMatcher
from app.job_discovery.models import DiscoveredJob, JobSearchPreferences
from app.job_discovery.ranking import JobRankingEngine


class JobMatchScorer:
    def __init__(
        self,
        ranking_engine: JobRankingEngine | None = None,
        skill_matcher: SkillMatcher | None = None,
    ) -> None:
        self._ranking_engine = ranking_engine or JobRankingEngine()
        self._skill_matcher = skill_matcher or SkillMatcher()

    def evaluate(
        self,
        job: DiscoveredJob,
        profile: CareerProfile,
        blueprint: ResumeBlueprint | None = None,
        *,
        preferences: JobSearchPreferences | None = None,
    ) -> MatchEvaluation:
        ranking = self._ranking_engine.rank(job, profile, blueprint, preferences=preferences)

        user_skills = [
            SkillInput(name=skill.name, years_experience=skill.years_experience)
            for skill in profile.skills
        ]
        preferred_skills = blueprint.recommended_skills if blueprint else []
        skill_match = self._skill_matcher.match(user_skills, job.skills, preferred_skills)

        matched_skills = list(
            dict.fromkeys([*skill_match.exact_matches, *skill_match.related_matches])
        )

        evaluation = MatchEvaluation(
            match_score=ranking.score,
            matched_skills=matched_skills,
            missing_skills=list(skill_match.missing_skills),
            explanations=[explanation.detail for explanation in ranking.explanations],
        )
        logger.bind(job_title=job.title, company=job.company).info(
            "Scored job '{}' at {}: {} matched, {} missing skill(s).",
            job.title,
            evaluation.match_score,
            len(evaluation.matched_skills),
            len(evaluation.missing_skills),
        )
        return evaluation
