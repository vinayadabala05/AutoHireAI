"""Unit tests for `app.job_discovery.filters.JobFilter`."""

from app.job_discovery.filters import JobFilter
from app.job_discovery.models import JobFilterCriteria
from app.models.enums import ExperienceLevel, RemoteType
from tests.job_discovery_fixtures import sample_job


def test_apply_with_no_criteria_returns_all_jobs() -> None:
    jobs = [sample_job(), sample_job(title="Other Role")]
    result = JobFilter().apply(jobs, JobFilterCriteria())
    assert result == jobs


def test_work_arrangement_remote_only() -> None:
    remote = sample_job(remote_type=RemoteType.REMOTE)
    onsite = sample_job(remote_type=RemoteType.ONSITE)
    result = JobFilter().apply(
        [remote, onsite], JobFilterCriteria(work_arrangement=RemoteType.REMOTE)
    )
    assert result == [remote]


def test_work_arrangement_hybrid_only() -> None:
    hybrid = sample_job(remote_type=RemoteType.HYBRID)
    remote = sample_job(remote_type=RemoteType.REMOTE)
    result = JobFilter().apply(
        [hybrid, remote], JobFilterCriteria(work_arrangement=RemoteType.HYBRID)
    )
    assert result == [hybrid]


def test_work_arrangement_onsite_only() -> None:
    onsite = sample_job(remote_type=RemoteType.ONSITE)
    hybrid = sample_job(remote_type=RemoteType.HYBRID)
    result = JobFilter().apply(
        [onsite, hybrid], JobFilterCriteria(work_arrangement=RemoteType.ONSITE)
    )
    assert result == [onsite]


def test_work_arrangement_excludes_jobs_with_unknown_arrangement() -> None:
    unknown = sample_job(remote_type=None)
    result = JobFilter().apply([unknown], JobFilterCriteria(work_arrangement=RemoteType.REMOTE))
    assert result == []


def test_experience_level_filter() -> None:
    senior = sample_job(experience_level=ExperienceLevel.SENIOR)
    junior = sample_job(experience_level=ExperienceLevel.JUNIOR)
    result = JobFilter().apply(
        [senior, junior], JobFilterCriteria(experience_levels=[ExperienceLevel.SENIOR])
    )
    assert result == [senior]


def test_salary_min_filter_uses_max_when_available() -> None:
    high_paying = sample_job(salary_min=100000.0, salary_max=200000.0)
    low_paying = sample_job(salary_min=40000.0, salary_max=50000.0)
    result = JobFilter().apply([high_paying, low_paying], JobFilterCriteria(salary_min=100000.0))
    assert result == [high_paying]


def test_salary_min_filter_excludes_jobs_with_no_salary_disclosed() -> None:
    undisclosed = sample_job(salary_min=None, salary_max=None)
    result = JobFilter().apply([undisclosed], JobFilterCriteria(salary_min=50000.0))
    assert result == []


def test_country_filter_matches_substring_in_location() -> None:
    us_job = sample_job(location="Austin, TX, United States")
    uk_job = sample_job(location="London, United Kingdom")
    result = JobFilter().apply([us_job, uk_job], JobFilterCriteria(countries=["United States"]))
    assert result == [us_job]


def test_city_filter_matches_substring_in_location() -> None:
    sf_job = sample_job(location="San Francisco, CA")
    nyc_job = sample_job(location="New York, NY")
    result = JobFilter().apply([sf_job, nyc_job], JobFilterCriteria(cities=["San Francisco"]))
    assert result == [sf_job]


def test_location_filter_excludes_jobs_with_no_location() -> None:
    no_location = sample_job(location=None)
    result = JobFilter().apply([no_location], JobFilterCriteria(cities=["San Francisco"]))
    assert result == []


def test_technology_filter_matches_any_overlap() -> None:
    python_job = sample_job(skills=["Python", "FastAPI"])
    java_job = sample_job(skills=["Java", "Spring"])
    result = JobFilter().apply([python_job, java_job], JobFilterCriteria(technologies=["python"]))
    assert result == [python_job]


def test_keyword_filter_matches_title_or_description() -> None:
    matching = sample_job(title="Staff Backend Engineer", description="")
    other = sample_job(title="Frontend Engineer", description="React and CSS work.")
    result = JobFilter().apply([matching, other], JobFilterCriteria(keywords=["staff"]))
    assert result == [matching]


def test_filters_compose_with_and_semantics() -> None:
    matches_both = sample_job(remote_type=RemoteType.REMOTE, location="Austin, TX")
    matches_only_location = sample_job(remote_type=RemoteType.ONSITE, location="Austin, TX")
    criteria = JobFilterCriteria(work_arrangement=RemoteType.REMOTE, cities=["Austin"])
    result = JobFilter().apply([matches_both, matches_only_location], criteria)
    assert result == [matches_both]
