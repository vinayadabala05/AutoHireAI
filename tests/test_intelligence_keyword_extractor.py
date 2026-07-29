from app.intelligence.keyword_extractor import KeywordExtractor


def test_extracts_keywords_across_categories() -> None:
    text = (
        "We use Python, FastAPI, and PostgreSQL, deployed with Docker and Kubernetes on AWS. "
        "Familiarity with Machine Learning and strong Communication skills required."
    )
    result = KeywordExtractor().extract(text)

    assert "Python" in result.programming_languages
    assert "FastAPI" in result.frameworks
    assert "AWS" in result.cloud
    assert "Docker" in result.devops
    assert "Kubernetes" in result.devops
    assert "PostgreSQL" in result.databases
    assert "Machine Learning" in result.ai_ml
    assert "Communication" in result.soft_skills


def test_aliases_resolve_to_canonical_name() -> None:
    result = KeywordExtractor().extract("Experience with Postgres, K8s, and Golang required.")

    assert "PostgreSQL" in result.databases
    assert "Postgres" not in result.databases
    assert "Kubernetes" in result.devops
    assert "Go" in result.programming_languages


def test_does_not_false_positive_on_substrings() -> None:
    # "Go" must not match inside unrelated words like "Goal", and "R" must
    # not match inside ordinary English words like "order" or "for".
    result = KeywordExtractor().extract(
        "We order supplies for the team, staying goal-oriented throughout the process."
    )

    assert "Go" not in result.programming_languages
    assert "R" not in result.programming_languages


def test_all_technical_deduplicates_and_excludes_soft_skills() -> None:
    result = KeywordExtractor().extract("Python and Python again, plus strong Leadership.")

    technical = result.all_technical()
    assert technical.count("Python") == 1
    assert "Leadership" not in technical
