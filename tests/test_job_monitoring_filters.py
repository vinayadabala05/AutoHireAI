"""Unit tests for `app.job_monitoring.filters.MonitoringJobFilter`."""

from app.job_discovery.models import JobFilterCriteria
from app.job_monitoring.filters import MonitoringJobFilter
from app.job_monitoring.models import MonitoringFilterCriteria
from tests.job_discovery_fixtures import sample_job
from tests.resume_fixtures import sample_career_profile


def test_matches_true_with_no_criteria() -> None:
    assert MonitoringJobFilter().matches(sample_job(), MonitoringFilterCriteria()) is True


def test_base_criteria_delegates_to_job_discovery_filter() -> None:
    from app.models.enums import RemoteType

    job = sample_job(remote_type=RemoteType.ONSITE)
    criteria = MonitoringFilterCriteria(base=JobFilterCriteria(work_arrangement=RemoteType.REMOTE))
    assert MonitoringJobFilter().matches(job, criteria) is False


def test_company_blacklist_excludes_matching_company() -> None:
    job = sample_job(company="Acme Corp")
    criteria = MonitoringFilterCriteria(company_blacklist=["acme corp"])
    assert MonitoringJobFilter().matches(job, criteria) is False


def test_company_whitelist_excludes_non_matching_company() -> None:
    job = sample_job(company="Acme Corp")
    criteria = MonitoringFilterCriteria(company_whitelist=["Other Corp"])
    assert MonitoringJobFilter().matches(job, criteria) is False


def test_company_whitelist_allows_matching_company() -> None:
    job = sample_job(company="Acme Corp")
    criteria = MonitoringFilterCriteria(company_whitelist=["acme corp"])
    assert MonitoringJobFilter().matches(job, criteria) is True


def test_min_skill_overlap_requires_profile() -> None:
    job = sample_job(skills=["Python", "FastAPI"])
    criteria = MonitoringFilterCriteria(min_skill_overlap=1)
    assert (
        MonitoringJobFilter().matches(job, criteria, profile=None) is True
    )  # no profile, skip check


def test_min_skill_overlap_filters_out_low_overlap_jobs() -> None:
    job = sample_job(skills=["Rust", "Go"])
    criteria = MonitoringFilterCriteria(min_skill_overlap=1)
    assert MonitoringJobFilter().matches(job, criteria, profile=sample_career_profile()) is False


def test_min_skill_overlap_passes_sufficient_overlap() -> None:
    job = sample_job(skills=["Python", "FastAPI"])
    criteria = MonitoringFilterCriteria(min_skill_overlap=2)
    assert MonitoringJobFilter().matches(job, criteria, profile=sample_career_profile()) is True


def test_custom_rules_must_all_pass() -> None:
    job = sample_job(title="Backend Engineer")
    always_true = lambda j: True  # noqa: E731
    always_false = lambda j: False  # noqa: E731

    assert MonitoringJobFilter([always_true]).matches(job, MonitoringFilterCriteria()) is True
    assert (
        MonitoringJobFilter([always_true, always_false]).matches(job, MonitoringFilterCriteria())
        is False
    )


def test_custom_rule_can_inspect_job_fields() -> None:
    job = sample_job(title="Staff Engineer")
    rule = lambda j: "staff" in j.title.lower()  # noqa: E731
    assert MonitoringJobFilter([rule]).matches(job, MonitoringFilterCriteria()) is True
    assert (
        MonitoringJobFilter([rule]).matches(sample_job(title="Other"), MonitoringFilterCriteria())
        is False
    )
