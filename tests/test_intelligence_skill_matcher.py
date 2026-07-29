from app.intelligence.job_analyzer import JobAnalyzer
from app.intelligence.models import SkillInput
from app.intelligence.skill_matcher import SkillMatcher
from tests.intelligence_fixtures import SAMPLE_JOBS, sample_career_context

analyzer = JobAnalyzer()
matcher = SkillMatcher()


def test_backend_engineer_has_high_coverage_and_no_missing_required_skills() -> None:
    context = sample_career_context()
    analysis = analyzer.analyze(SAMPLE_JOBS["backend_engineer"])

    match = matcher.match(context.skills, analysis.required_skills, analysis.preferred_skills)

    assert set(match.exact_matches) >= {"Python", "FastAPI", "PostgreSQL", "Docker", "AWS"}
    assert not any(m.importance == "required" for m in match.missing_skills)
    # All 5 required skills match exactly; only 1 of 3 preferred skills
    # (Kubernetes, via the related-skills table) is covered, so coverage
    # sits around 69% rather than near-100 — that's the correct, honest
    # signal that Redis and CI/CD are genuinely absent from the profile.
    assert match.coverage_percentage > 60
    assert match.weighted_score > 70


def test_ai_engineer_flags_missing_required_skills() -> None:
    context = sample_career_context()
    analysis = analyzer.analyze(SAMPLE_JOBS["ai_engineer"])

    match = matcher.match(context.skills, analysis.required_skills, analysis.preferred_skills)

    missing_required = {m.name for m in match.missing_skills if m.importance == "required"}
    assert "PyTorch" in missing_required or "Machine Learning" in missing_required
    assert "Python" in match.exact_matches


def test_related_skill_via_alias_table() -> None:
    match = matcher.match(
        user_skills=[SkillInput(name="Django")],
        required_skills=["Python"],
        preferred_skills=[],
    )

    assert "Python" in match.related_matches
    assert match.coverage_percentage == 50.0  # one related match, weighted at 0.5


def test_related_skill_via_fuzzy_match() -> None:
    match = matcher.match(
        user_skills=[SkillInput(name="Postgres")],
        required_skills=["PostgreSQL"],
        preferred_skills=[],
    )

    # "Postgres" isn't an exact string match for "PostgreSQL" but is close
    # enough (SequenceMatcher ratio) to count as related.
    assert "PostgreSQL" in match.related_matches or "PostgreSQL" in match.exact_matches


def test_no_preferred_skills_still_scores_from_required_only() -> None:
    match = matcher.match(
        user_skills=[SkillInput(name="Python")],
        required_skills=["Python"],
        preferred_skills=[],
    )

    assert match.weighted_score == 100.0
