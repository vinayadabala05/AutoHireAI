from app.intelligence.experience_ranker import ExperienceRanker
from app.intelligence.job_analyzer import JobAnalyzer
from tests.intelligence_fixtures import SAMPLE_JOBS, sample_career_context

analyzer = JobAnalyzer()
ranker = ExperienceRanker()


def test_backend_experience_ranks_above_intern_experience_for_backend_job() -> None:
    context = sample_career_context()
    analysis = analyzer.analyze(SAMPLE_JOBS["backend_engineer"])

    rankings = ranker.rank(context.experiences, analysis)

    assert rankings[0].title == "Backend Engineer"
    assert rankings[0].company_name == "Acme Corp"
    assert rankings[0].score > rankings[1].score


def test_current_role_gets_full_recency_bonus() -> None:
    context = sample_career_context()
    analysis = analyzer.analyze(SAMPLE_JOBS["backend_engineer"])

    rankings = ranker.rank(context.experiences, analysis)
    current = next(r for r in rankings if r.title == "Backend Engineer")

    assert "Current role" in current.reasons


def test_rankings_sorted_descending_by_score() -> None:
    context = sample_career_context()
    analysis = analyzer.analyze(SAMPLE_JOBS["ai_engineer"])

    rankings = ranker.rank(context.experiences, analysis)

    scores = [r.score for r in rankings]
    assert scores == sorted(scores, reverse=True)
