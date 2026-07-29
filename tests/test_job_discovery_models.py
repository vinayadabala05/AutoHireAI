"""Unit tests for `app.job_discovery.models`."""

from app.job_discovery.models import DeduplicationResult, JobFilterCriteria, JobSearchQuery
from app.models.enums import RemoteType
from tests.job_discovery_fixtures import sample_job


def test_is_remote_hybrid_onsite_properties() -> None:
    remote = sample_job(remote_type=RemoteType.REMOTE)
    hybrid = sample_job(remote_type=RemoteType.HYBRID)
    onsite = sample_job(remote_type=RemoteType.ONSITE)
    unknown = sample_job(remote_type=None)

    assert (remote.is_remote, remote.is_hybrid, remote.is_onsite) == (True, False, False)
    assert (hybrid.is_remote, hybrid.is_hybrid, hybrid.is_onsite) == (False, True, False)
    assert (onsite.is_remote, onsite.is_hybrid, onsite.is_onsite) == (False, False, True)
    assert (unknown.is_remote, unknown.is_hybrid, unknown.is_onsite) == (False, False, False)


def test_salary_display_with_both_bounds() -> None:
    job = sample_job(salary_min=100000.0, salary_max=150000.0, currency="USD")
    assert job.salary_display == "USD 100,000-150,000"


def test_salary_display_with_only_minimum() -> None:
    job = sample_job(salary_min=100000.0, salary_max=None, currency="USD")
    assert job.salary_display == "USD 100,000"


def test_salary_display_with_only_maximum() -> None:
    job = sample_job(salary_min=None, salary_max=150000.0, currency=None)
    assert job.salary_display == "150,000"


def test_salary_display_none_when_no_salary() -> None:
    job = sample_job(salary_min=None, salary_max=None)
    assert job.salary_display is None


def test_job_search_query_defaults() -> None:
    query = JobSearchQuery()
    assert query.keywords == []
    assert query.limit == 50
    assert query.remote_only is False


def test_job_filter_criteria_defaults_are_unconstrained() -> None:
    criteria = JobFilterCriteria()
    assert criteria.work_arrangement is None
    assert criteria.experience_levels == []
    assert criteria.salary_min is None


def test_deduplication_result_holds_unique_jobs_and_count() -> None:
    job = sample_job()
    result = DeduplicationResult(unique_jobs=[job], duplicates_removed=2)
    assert result.unique_jobs == [job]
    assert result.duplicates_removed == 2
