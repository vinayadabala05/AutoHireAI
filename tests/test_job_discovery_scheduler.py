"""Unit tests for `app.job_discovery.scheduler.JobDiscoveryScheduler`."""

import pytest

from app.job_discovery.models import JobProviderName, JobSearchQuery
from app.job_discovery.scheduler import JobDiscoveryScheduler
from tests.job_discovery_fixtures import sample_job


async def _fetch(_: JobSearchQuery) -> list:
    return [sample_job()]


def test_register_creates_a_polling_registration() -> None:
    scheduler = JobDiscoveryScheduler()
    query = JobSearchQuery(keywords=["python"])
    registration = scheduler.register(JobProviderName.GREENHOUSE, query, 3600, _fetch)
    assert registration.provider_name is JobProviderName.GREENHOUSE
    assert registration.interval_seconds == 3600
    assert registration.last_run_at is None


def test_is_registered_reflects_registration_state() -> None:
    scheduler = JobDiscoveryScheduler()
    assert scheduler.is_registered(JobProviderName.LEVER) is False
    scheduler.register(JobProviderName.LEVER, JobSearchQuery(), 60, _fetch)
    assert scheduler.is_registered(JobProviderName.LEVER) is True


def test_unregister_removes_registration_and_fetcher() -> None:
    scheduler = JobDiscoveryScheduler()
    scheduler.register(JobProviderName.ASHBY, JobSearchQuery(), 60, _fetch)
    scheduler.unregister(JobProviderName.ASHBY)
    assert scheduler.is_registered(JobProviderName.ASHBY) is False


def test_unregister_is_a_no_op_for_unknown_provider() -> None:
    scheduler = JobDiscoveryScheduler()
    scheduler.unregister(JobProviderName.WORKABLE)  # should not raise


def test_list_registrations_returns_every_registration() -> None:
    scheduler = JobDiscoveryScheduler()
    scheduler.register(JobProviderName.GREENHOUSE, JobSearchQuery(), 60, _fetch)
    scheduler.register(JobProviderName.LEVER, JobSearchQuery(), 120, _fetch)
    registrations = scheduler.list_registrations()
    assert len(registrations) == 2
    assert {r.provider_name for r in registrations} == {
        JobProviderName.GREENHOUSE,
        JobProviderName.LEVER,
    }


async def test_run_once_executes_the_registered_fetch_callable() -> None:
    scheduler = JobDiscoveryScheduler()
    scheduler.register(JobProviderName.GREENHOUSE, JobSearchQuery(), 60, _fetch)
    jobs = await scheduler.run_once(JobProviderName.GREENHOUSE)
    assert len(jobs) == 1


async def test_run_once_updates_last_run_at() -> None:
    scheduler = JobDiscoveryScheduler()
    scheduler.register(JobProviderName.GREENHOUSE, JobSearchQuery(), 60, _fetch)
    await scheduler.run_once(JobProviderName.GREENHOUSE)
    registration = scheduler.list_registrations()[0]
    assert registration.last_run_at is not None


async def test_run_once_raises_for_unregistered_provider() -> None:
    scheduler = JobDiscoveryScheduler()
    with pytest.raises(KeyError):
        await scheduler.run_once(JobProviderName.ASHBY)
