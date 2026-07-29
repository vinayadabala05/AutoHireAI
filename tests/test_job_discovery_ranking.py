"""Unit tests for `app.job_discovery.ranking.JobRankingEngine`."""

from datetime import date

from app.job_discovery.models import JobSearchPreferences
from app.job_discovery.ranking import JobRankingEngine, _level_from_years, _total_years_experience
from app.models.enums import ExperienceLevel, RemoteType
from tests.job_discovery_fixtures import sample_blueprint, sample_career_profile, sample_job


def test_rank_returns_score_between_zero_and_hundred() -> None:
    result = JobRankingEngine().rank(sample_job(), sample_career_profile())
    assert 0.0 <= result.score <= 100.0


def test_rank_returns_one_explanation_per_factor() -> None:
    result = JobRankingEngine().rank(sample_job(), sample_career_profile())
    factors = {explanation.factor for explanation in result.explanations}
    assert factors == {
        "skills",
        "experience",
        "location",
        "remote_preference",
        "salary",
        "company_preference",
    }


def test_rank_weights_sum_to_one() -> None:
    result = JobRankingEngine().rank(sample_job(), sample_career_profile())
    assert round(sum(e.weight for e in result.explanations), 6) == 1.0


def test_perfect_match_scores_highly() -> None:
    job = sample_job(
        skills=["Python", "FastAPI"],
        location="San Francisco, CA",
        remote_type=RemoteType.REMOTE,
        salary_min=150000.0,
        salary_max=180000.0,
        experience_level=ExperienceLevel.MID,
        company="Acme Corp",
    )
    profile = sample_career_profile()
    result = JobRankingEngine().rank(
        job, profile, preferences=JobSearchPreferences(preferred_companies=["Acme Corp"])
    )
    assert result.score > 85.0


def test_job_with_no_skills_gets_neutral_skill_score() -> None:
    result = JobRankingEngine().rank(sample_job(skills=[]), sample_career_profile())
    skill_explanation = next(e for e in result.explanations if e.factor == "skills")
    assert skill_explanation.score == 60.0


def test_blueprint_overlap_gives_skill_bonus() -> None:
    profile = sample_career_profile()
    job = sample_job(skills=["Python", "FastAPI", "PostgreSQL"])
    without_blueprint = JobRankingEngine().rank(job, profile)
    with_blueprint = JobRankingEngine().rank(job, profile, sample_blueprint())
    skill_without = next(e for e in without_blueprint.explanations if e.factor == "skills").score
    skill_with = next(e for e in with_blueprint.explanations if e.factor == "skills").score
    assert skill_with >= skill_without


def test_job_with_no_experience_level_gets_neutral_experience_score() -> None:
    result = JobRankingEngine().rank(sample_job(experience_level=None), sample_career_profile())
    explanation = next(e for e in result.explanations if e.factor == "experience")
    assert explanation.score == 65.0


def test_matching_experience_level_scores_highly() -> None:
    # Compute the candidate's true level from the same helpers the engine
    # uses, rather than hardcoding a level — the candidate's estimated
    # years of experience (and therefore level) shifts as real time passes
    # since `sample_career_profile` uses an open-ended "is_current" role.
    profile = sample_career_profile()
    candidate_level = _level_from_years(_total_years_experience(profile))
    result = JobRankingEngine().rank(sample_job(experience_level=candidate_level), profile)
    explanation = next(e for e in result.explanations if e.factor == "experience")
    assert explanation.score == 100.0


def test_distant_experience_level_scores_lower() -> None:
    profile = sample_career_profile()
    candidate_level = _level_from_years(_total_years_experience(profile))
    # EXECUTIVE is the most senior level; guaranteed to differ from any
    # early/mid-career candidate level, so this always exercises a penalty
    # unless the candidate is themselves already at EXECUTIVE.
    distant_level = (
        ExperienceLevel.INTERN
        if candidate_level is ExperienceLevel.EXECUTIVE
        else ExperienceLevel.EXECUTIVE
    )
    result = JobRankingEngine().rank(sample_job(experience_level=distant_level), profile)
    explanation = next(e for e in result.explanations if e.factor == "experience")
    assert explanation.score < 100.0


def test_no_location_preference_gives_neutral_score() -> None:
    profile = sample_career_profile(preferred_locations=[])
    result = JobRankingEngine().rank(sample_job(), profile)
    explanation = next(e for e in result.explanations if e.factor == "location")
    assert explanation.score == 70.0


def test_job_with_no_location_gets_neutral_score_when_preference_exists() -> None:
    result = JobRankingEngine().rank(sample_job(location=None), sample_career_profile())
    explanation = next(e for e in result.explanations if e.factor == "location")
    assert explanation.score == 60.0


def test_matching_location_scores_highly() -> None:
    result = JobRankingEngine().rank(
        sample_job(location="San Francisco, CA"), sample_career_profile()
    )
    explanation = next(e for e in result.explanations if e.factor == "location")
    assert explanation.score == 100.0


def test_non_matching_location_scores_low() -> None:
    result = JobRankingEngine().rank(
        sample_job(location="Berlin, Germany"), sample_career_profile()
    )
    explanation = next(e for e in result.explanations if e.factor == "location")
    assert explanation.score == 20.0


def test_explicit_preferences_override_profile_location() -> None:
    profile = sample_career_profile(preferred_locations=["San Francisco"])
    result = JobRankingEngine().rank(
        sample_job(location="Berlin, Germany"),
        profile,
        preferences=JobSearchPreferences(preferred_locations=["Berlin"]),
    )
    explanation = next(e for e in result.explanations if e.factor == "location")
    assert explanation.score == 100.0


def test_no_remote_preference_gives_neutral_score() -> None:
    profile = sample_career_profile(preferred_remote_types=[])
    result = JobRankingEngine().rank(sample_job(), profile)
    explanation = next(e for e in result.explanations if e.factor == "remote_preference")
    assert explanation.score == 70.0


def test_unknown_remote_type_gives_neutral_score() -> None:
    result = JobRankingEngine().rank(sample_job(remote_type=None), sample_career_profile())
    explanation = next(e for e in result.explanations if e.factor == "remote_preference")
    assert explanation.score == 55.0


def test_matching_remote_type_scores_highly() -> None:
    result = JobRankingEngine().rank(
        sample_job(remote_type=RemoteType.REMOTE), sample_career_profile()
    )
    explanation = next(e for e in result.explanations if e.factor == "remote_preference")
    assert explanation.score == 100.0


def test_non_matching_remote_type_scores_low() -> None:
    result = JobRankingEngine().rank(
        sample_job(remote_type=RemoteType.ONSITE), sample_career_profile()
    )
    explanation = next(e for e in result.explanations if e.factor == "remote_preference")
    assert explanation.score == 25.0


def test_no_salary_preference_gives_neutral_score() -> None:
    profile = sample_career_profile(observed_salary_min=None)
    result = JobRankingEngine().rank(sample_job(), profile)
    explanation = next(e for e in result.explanations if e.factor == "salary")
    assert explanation.score == 70.0


def test_job_with_no_disclosed_salary_gets_neutral_score() -> None:
    result = JobRankingEngine().rank(
        sample_job(salary_min=None, salary_max=None), sample_career_profile()
    )
    explanation = next(e for e in result.explanations if e.factor == "salary")
    assert explanation.score == 55.0


def test_salary_meeting_target_scores_highly() -> None:
    result = JobRankingEngine().rank(
        sample_job(salary_min=150000.0, salary_max=180000.0), sample_career_profile()
    )
    explanation = next(e for e in result.explanations if e.factor == "salary")
    assert explanation.score == 100.0


def test_salary_below_target_scores_proportionally() -> None:
    profile = sample_career_profile(observed_salary_min=100000.0)
    result = JobRankingEngine().rank(sample_job(salary_min=50000.0, salary_max=50000.0), profile)
    explanation = next(e for e in result.explanations if e.factor == "salary")
    assert explanation.score == 50.0


def test_excluded_company_scores_zero() -> None:
    result = JobRankingEngine().rank(
        sample_job(company="Acme Corp"),
        sample_career_profile(),
        preferences=JobSearchPreferences(excluded_companies=["acme corp"]),
    )
    explanation = next(e for e in result.explanations if e.factor == "company_preference")
    assert explanation.score == 0.0


def test_preferred_company_scores_highly() -> None:
    result = JobRankingEngine().rank(
        sample_job(company="Acme Corp"),
        sample_career_profile(),
        preferences=JobSearchPreferences(preferred_companies=["Acme Corp"]),
    )
    explanation = next(e for e in result.explanations if e.factor == "company_preference")
    assert explanation.score == 100.0


def test_no_company_preference_gives_neutral_score() -> None:
    result = JobRankingEngine().rank(sample_job(), sample_career_profile())
    explanation = next(e for e in result.explanations if e.factor == "company_preference")
    assert explanation.score == 70.0


def test_rank_all_sorts_descending_by_score() -> None:
    profile = sample_career_profile()
    strong = sample_job(
        title="Backend Engineer",
        skills=["Python", "FastAPI"],
        remote_type=RemoteType.REMOTE,
        location="San Francisco, CA",
        salary_min=160000.0,
    )
    weak = sample_job(
        title="Other Role",
        skills=["COBOL"],
        remote_type=RemoteType.ONSITE,
        location="Antarctica",
        salary_min=10000.0,
        salary_max=10000.0,
    )
    results = JobRankingEngine().rank_all([weak, strong], profile)
    assert results[0].job.title == "Backend Engineer"
    assert results[0].score >= results[1].score


def test_total_years_experience_sums_durations() -> None:
    profile = sample_career_profile()
    years = _total_years_experience(profile, today=date(2026, 1, 1))
    assert years > 0


def test_level_from_years_boundaries() -> None:
    assert _level_from_years(0.5) is ExperienceLevel.INTERN
    assert _level_from_years(1.5) is ExperienceLevel.ENTRY
    assert _level_from_years(3.0) is ExperienceLevel.JUNIOR
    assert _level_from_years(5.0) is ExperienceLevel.MID
    assert _level_from_years(8.0) is ExperienceLevel.SENIOR
    assert _level_from_years(12.0) is ExperienceLevel.LEAD
    assert _level_from_years(20.0) is ExperienceLevel.PRINCIPAL
