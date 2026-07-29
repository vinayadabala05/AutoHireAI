"""Unit tests for `app.job_discovery.deduplication`."""

from app.job_discovery.deduplication import JobDeduplicator, content_hash, content_key
from tests.job_discovery_fixtures import sample_job


def test_deduplicate_removes_exact_url_duplicates() -> None:
    job_a = sample_job(source_url="https://boards.example.com/acme/x")
    job_b = sample_job(source_url="https://boards.example.com/acme/x", title="Different Title")
    result = JobDeduplicator().deduplicate([job_a, job_b])
    assert len(result.unique_jobs) == 1
    assert result.duplicates_removed == 1


def test_deduplicate_removes_content_hash_duplicates_with_different_urls() -> None:
    job_a = sample_job(source_url="https://a.example.com/1")
    job_b = sample_job(source_url="https://b.example.com/2")
    result = JobDeduplicator().deduplicate([job_a, job_b])
    assert len(result.unique_jobs) == 1
    assert result.duplicates_removed == 1


def test_deduplicate_keeps_distinct_jobs() -> None:
    job_a = sample_job(title="Backend Engineer", source_url="https://a.example.com/1")
    job_b = sample_job(title="Frontend Engineer", source_url="https://b.example.com/2")
    result = JobDeduplicator().deduplicate([job_a, job_b])
    assert len(result.unique_jobs) == 2
    assert result.duplicates_removed == 0


def test_deduplicate_is_case_and_whitespace_insensitive() -> None:
    job_a = sample_job(
        title="Backend Engineer",
        company="Acme Corp",
        location="San Francisco, CA",
        source_url="https://a.example.com/1",
    )
    job_b = sample_job(
        title="  BACKEND   engineer  ",
        company=" acme corp ",
        location=" san francisco,  ca ",
        source_url="https://b.example.com/2",
    )
    result = JobDeduplicator().deduplicate([job_a, job_b])
    assert len(result.unique_jobs) == 1


def test_deduplicate_empty_list_returns_empty_result() -> None:
    result = JobDeduplicator().deduplicate([])
    assert result.unique_jobs == []
    assert result.duplicates_removed == 0


def test_content_key_and_hash_are_stable_and_deterministic() -> None:
    job = sample_job()
    assert content_key(job) == content_key(job)
    assert content_hash(job) == content_hash(job)
    assert content_hash(job) != content_hash(sample_job(title="Something Else"))
