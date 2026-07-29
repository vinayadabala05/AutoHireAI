"""Integration tests for `app.job_discovery.service.JobDiscoveryService`."""

from app.job_discovery.exceptions import ProviderFetchError
from app.job_discovery.models import JobFilterCriteria, JobProviderName, JobSearchQuery
from app.job_discovery.providers.base import BaseJobProvider
from app.job_discovery.service import JobDiscoveryService
from app.models.enums import JobSource, RemoteType
from tests.job_discovery_fixtures import sample_career_profile, sample_job


class _FakeProvider(BaseJobProvider):
    def __init__(self, name: JobProviderName, jobs: list, fail: bool = False) -> None:
        super().__init__(board_token="fake")
        self._name = name
        self._jobs = jobs
        self._fail = fail

    @property
    def provider_name(self) -> JobProviderName:
        return self._name

    @property
    def source(self) -> JobSource:
        return JobSource.COMPANY_SITE

    async def fetch_jobs(self, query: JobSearchQuery) -> list:
        if self._fail:
            raise ProviderFetchError("simulated failure")
        return self._jobs[: query.limit]


async def test_discover_with_no_providers_returns_empty_list() -> None:
    service = JobDiscoveryService(providers=[])
    assert await service.discover(JobSearchQuery()) == []


async def test_discover_aggregates_jobs_from_multiple_providers() -> None:
    provider_a = _FakeProvider(
        JobProviderName.GREENHOUSE, [sample_job(title="Backend Engineer", source_url="https://a/1")]
    )
    provider_b = _FakeProvider(
        JobProviderName.LEVER, [sample_job(title="Frontend Engineer", source_url="https://b/2")]
    )
    service = JobDiscoveryService(providers=[provider_a, provider_b])
    jobs = await service.discover(JobSearchQuery())
    assert len(jobs) == 2


async def test_discover_deduplicates_across_providers() -> None:
    same_job = sample_job(source_url="https://shared.example.com/1")
    provider_a = _FakeProvider(JobProviderName.GREENHOUSE, [same_job])
    provider_b = _FakeProvider(JobProviderName.LEVER, [same_job])
    service = JobDiscoveryService(providers=[provider_a, provider_b])
    jobs = await service.discover(JobSearchQuery())
    assert len(jobs) == 1


async def test_discover_tolerates_a_failing_provider() -> None:
    healthy = _FakeProvider(JobProviderName.GREENHOUSE, [sample_job(source_url="https://a/1")])
    failing = _FakeProvider(JobProviderName.LEVER, [], fail=True)
    service = JobDiscoveryService(providers=[healthy, failing])
    jobs = await service.discover(JobSearchQuery())
    assert len(jobs) == 1


def test_filter_jobs_delegates_to_job_filter() -> None:
    service = JobDiscoveryService()
    remote = sample_job(remote_type=RemoteType.REMOTE, source_url="https://a/1")
    onsite = sample_job(remote_type=RemoteType.ONSITE, source_url="https://a/2")
    result = service.filter_jobs(
        [remote, onsite], JobFilterCriteria(work_arrangement=RemoteType.REMOTE)
    )
    assert result == [remote]


def test_rank_jobs_delegates_to_ranking_engine() -> None:
    service = JobDiscoveryService()
    jobs = [sample_job()]
    results = service.rank_jobs(jobs, sample_career_profile())
    assert len(results) == 1
    assert 0.0 <= results[0].score <= 100.0


async def test_discover_ranked_runs_the_full_pipeline() -> None:
    provider = _FakeProvider(
        JobProviderName.GREENHOUSE,
        [
            sample_job(source_url="https://a/1", remote_type=RemoteType.REMOTE),
            sample_job(source_url="https://a/2", remote_type=RemoteType.ONSITE),
        ],
    )
    service = JobDiscoveryService(providers=[provider])
    results = await service.discover_ranked(
        JobSearchQuery(),
        sample_career_profile(),
        criteria=JobFilterCriteria(work_arrangement=RemoteType.REMOTE),
    )
    assert len(results) == 1
    assert results[0].job.remote_type is RemoteType.REMOTE


def test_providers_property_returns_a_copy() -> None:
    provider = _FakeProvider(JobProviderName.GREENHOUSE, [])
    service = JobDiscoveryService(providers=[provider])
    returned = service.providers
    returned.append(provider)
    assert len(service.providers) == 1
