from app.intelligence.job_analyzer import JobAnalyzer
from app.intelligence.models import JobAnalysis
from app.intelligence.project_ranker import ProjectRanker
from tests.intelligence_fixtures import SAMPLE_JOBS, sample_career_context

analyzer = JobAnalyzer()
ranker = ProjectRanker()


def test_market_data_platform_ranks_first_for_backend_engineer() -> None:
    context = sample_career_context()
    analysis = analyzer.analyze(SAMPLE_JOBS["backend_engineer"])

    rankings = ranker.rank(context.projects, analysis)

    assert rankings[0].name == "Market Data Platform"
    assert rankings[0].confidence > rankings[-1].confidence
    assert any("FastAPI" in reason for reason in rankings[0].reasons)


def test_ml_recommendation_engine_ranks_first_for_ai_engineer() -> None:
    context = sample_career_context()
    analysis = analyzer.analyze(SAMPLE_JOBS["ai_engineer"])

    rankings = ranker.rank(context.projects, analysis)

    assert rankings[0].name == "ML Recommendation Engine"


def test_rankings_are_sorted_descending_by_confidence() -> None:
    context = sample_career_context()
    analysis = analyzer.analyze(SAMPLE_JOBS["python_developer"])

    rankings = ranker.rank(context.projects, analysis)

    confidences = [r.confidence for r in rankings]
    assert confidences == sorted(confidences, reverse=True)


def test_no_job_keywords_yields_zero_confidence_for_all_projects() -> None:
    context = sample_career_context()
    empty_analysis = JobAnalysis(title="Mystery Role")

    rankings = ranker.rank(context.projects, empty_analysis)

    assert all(r.confidence == 0.0 for r in rankings)
