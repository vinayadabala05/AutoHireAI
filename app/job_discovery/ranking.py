"""Job ranking: scores a `DiscoveredJob` 0-100 against a candidate's profile.

Six weighted factors make up the score — skill match, experience match,
location preference, remote-work preference, salary preference, and
company preference — each returned as its own `JobRankingExplanation` so a
caller (or a future UI) can show *why* a job scored the way it did, not
just the number.

Skill matching reuses Sprint 3's `SkillMatcher` directly (converting
`CareerProfile.skills` into the `SkillInput` shape it expects) rather than
reimplementing exact/related/missing skill logic a second time. Location,
remote, and salary preferences read from
`CareerProfile.preferences.application` (Sprint 3.5) unless the caller
supplies an explicit `JobSearchPreferences` override — see `models.py` for
why company preference has no `CareerProfile` equivalent and is only ever
sourced from that explicit override.
"""

from datetime import date

from app.career_profile.models import CareerProfile
from app.intelligence.models import ResumeBlueprint, SkillInput
from app.intelligence.skill_matcher import SkillMatcher
from app.job_discovery.models import (
    DiscoveredJob,
    JobRankingExplanation,
    JobRankingResult,
    JobSearchPreferences,
)
from app.models.enums import ExperienceLevel

_SKILL_WEIGHT = 0.40
_EXPERIENCE_WEIGHT = 0.15
_LOCATION_WEIGHT = 0.15
_REMOTE_WEIGHT = 0.10
_SALARY_WEIGHT = 0.10
_COMPANY_WEIGHT = 0.10

_EXPERIENCE_ORDER = [
    ExperienceLevel.INTERN,
    ExperienceLevel.ENTRY,
    ExperienceLevel.JUNIOR,
    ExperienceLevel.MID,
    ExperienceLevel.SENIOR,
    ExperienceLevel.LEAD,
    ExperienceLevel.PRINCIPAL,
    ExperienceLevel.EXECUTIVE,
]
_DISTANCE_PENALTY_PER_LEVEL = 20.0
_DAYS_PER_YEAR = 365.25


def _total_years_experience(profile: CareerProfile, *, today: date | None = None) -> float:
    reference_date = today or date.today()
    total_days = 0.0
    for experience in profile.experience:
        end = (
            reference_date
            if experience.is_current or experience.end_date is None
            else (experience.end_date)
        )
        total_days += max(0.0, (end - experience.start_date).days)
    return total_days / _DAYS_PER_YEAR


def _level_from_years(years: float) -> ExperienceLevel:
    if years < 1:
        return ExperienceLevel.INTERN
    if years < 2:
        return ExperienceLevel.ENTRY
    if years < 4:
        return ExperienceLevel.JUNIOR
    if years < 7:
        return ExperienceLevel.MID
    if years < 10:
        return ExperienceLevel.SENIOR
    if years < 15:
        return ExperienceLevel.LEAD
    return ExperienceLevel.PRINCIPAL


class JobRankingEngine:
    def __init__(self, skill_matcher: SkillMatcher | None = None) -> None:
        self._skill_matcher = skill_matcher or SkillMatcher()

    def rank(
        self,
        job: DiscoveredJob,
        profile: CareerProfile,
        blueprint: ResumeBlueprint | None = None,
        *,
        preferences: JobSearchPreferences | None = None,
    ) -> JobRankingResult:
        preferences = preferences or JobSearchPreferences()

        factors = [
            ("skills", _SKILL_WEIGHT, self._score_skills(job, profile, blueprint)),
            ("experience", _EXPERIENCE_WEIGHT, self._score_experience(job, profile)),
            ("location", _LOCATION_WEIGHT, self._score_location(job, profile, preferences)),
            ("remote_preference", _REMOTE_WEIGHT, self._score_remote(job, profile, preferences)),
            ("salary", _SALARY_WEIGHT, self._score_salary(job, profile, preferences)),
            ("company_preference", _COMPANY_WEIGHT, self._score_company(job, preferences)),
        ]
        explanations = [
            JobRankingExplanation(factor=factor, score=score, weight=weight, detail=detail)
            for factor, weight, (score, detail) in factors
        ]
        total = sum(explanation.score * explanation.weight for explanation in explanations)
        return JobRankingResult(
            job=job, score=round(min(100.0, max(0.0, total)), 1), explanations=explanations
        )

    def rank_all(
        self,
        jobs: list[DiscoveredJob],
        profile: CareerProfile,
        blueprint: ResumeBlueprint | None = None,
        *,
        preferences: JobSearchPreferences | None = None,
    ) -> list[JobRankingResult]:
        results = [self.rank(job, profile, blueprint, preferences=preferences) for job in jobs]
        return sorted(results, key=lambda result: result.score, reverse=True)

    def _score_skills(
        self, job: DiscoveredJob, profile: CareerProfile, blueprint: ResumeBlueprint | None
    ) -> tuple[float, str]:
        if not job.skills:
            return 60.0, "Job listing specifies no skills; neutral score assigned."

        user_skills = [
            SkillInput(name=skill.name, years_experience=skill.years_experience)
            for skill in profile.skills
        ]
        match = self._skill_matcher.match(user_skills, job.skills, [])
        score = match.weighted_score
        detail = (
            f"{len(match.exact_matches)} exact and {len(match.related_matches)} related skill "
            f"match(es) out of {len(job.skills)} listed skill(s)."
        )

        if blueprint and blueprint.recommended_skills:
            job_skills_norm = {skill.lower() for skill in job.skills}
            recommended_norm = {skill.lower() for skill in blueprint.recommended_skills}
            overlap = job_skills_norm & recommended_norm
            if overlap:
                bonus = min(10.0, len(overlap) * 2.0)
                score = min(100.0, score + bonus)
                detail += (
                    f" +{bonus:.0f} bonus for {len(overlap)} skill(s) your resume blueprint "
                    "already recommends emphasizing."
                )
        return round(score, 1), detail

    def _score_experience(self, job: DiscoveredJob, profile: CareerProfile) -> tuple[float, str]:
        if job.experience_level is None:
            return 65.0, "Job listing states no experience level; neutral score assigned."

        years = _total_years_experience(profile)
        candidate_level = _level_from_years(years)
        distance = abs(
            _EXPERIENCE_ORDER.index(candidate_level) - _EXPERIENCE_ORDER.index(job.experience_level)
        )
        score = max(0.0, 100.0 - distance * _DISTANCE_PENALTY_PER_LEVEL)
        detail = (
            f"Estimated {years:.1f} year(s) of experience (~{candidate_level.value}) vs. the "
            f"job's stated '{job.experience_level.value}' level."
        )
        return round(score, 1), detail

    def _score_location(
        self, job: DiscoveredJob, profile: CareerProfile, preferences: JobSearchPreferences
    ) -> tuple[float, str]:
        preferred = (
            preferences.preferred_locations or profile.preferences.application.preferred_locations
        )
        if not preferred:
            return 70.0, "No location preference on file; neutral score assigned."
        if not job.location:
            return 60.0, "Job listing has no location specified."

        job_location_norm = job.location.lower()
        if any(
            location.lower() in job_location_norm or job_location_norm in location.lower()
            for location in preferred
        ):
            return 100.0, f"Job location '{job.location}' matches a preferred location."
        return (
            20.0,
            f"Job location '{job.location}' does not match any preferred location "
            f"({', '.join(preferred)}).",
        )

    def _score_remote(
        self, job: DiscoveredJob, profile: CareerProfile, preferences: JobSearchPreferences
    ) -> tuple[float, str]:
        preferred = (
            preferences.preferred_remote_types
            or profile.preferences.application.preferred_remote_types
        )
        if not preferred:
            return 70.0, "No remote-work preference on file; neutral score assigned."
        if job.remote_type is None:
            return 55.0, "Job listing does not specify a work arrangement."
        if job.remote_type in preferred:
            return 100.0, f"Job's '{job.remote_type.value}' arrangement matches your preference."
        preferred_values = ", ".join(remote_type.value for remote_type in preferred)
        return (
            25.0,
            f"Job's '{job.remote_type.value}' arrangement does not match your preferred "
            f"arrangement(s) ({preferred_values}).",
        )

    def _score_salary(
        self, job: DiscoveredJob, profile: CareerProfile, preferences: JobSearchPreferences
    ) -> tuple[float, str]:
        floor = preferences.salary_floor
        if floor is None:
            floor = profile.preferences.application.observed_salary_min
        if floor is None:
            return 70.0, "No salary preference on file; neutral score assigned."

        job_salary = job.salary_max if job.salary_max is not None else job.salary_min
        if job_salary is None:
            return 55.0, "Job listing does not disclose salary."
        if job_salary >= floor:
            return 100.0, f"Job's salary (~{job_salary:,.0f}) meets your target of {floor:,.0f}."

        score = max(0.0, (job_salary / floor) * 100.0) if floor else 0.0
        return (
            round(score, 1),
            f"Job's salary (~{job_salary:,.0f}) is below your target of {floor:,.0f}.",
        )

    def _score_company(
        self, job: DiscoveredJob, preferences: JobSearchPreferences
    ) -> tuple[float, str]:
        company_norm = job.company.strip().lower()
        if any(company.lower() == company_norm for company in preferences.excluded_companies):
            return 0.0, f"'{job.company}' is on your excluded companies list."
        if any(company.lower() == company_norm for company in preferences.preferred_companies):
            return 100.0, f"'{job.company}' is on your preferred companies list."
        return 70.0, "No specific preference recorded for this company; neutral score assigned."
