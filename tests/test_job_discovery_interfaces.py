"""Structural tests for `app.job_discovery.interfaces`.

These `Protocol`s carry no runtime logic — the meaningful check is that
every concrete implementation in this package actually satisfies the
shape its Protocol declares (checked by explicit member name, not a
private `typing` internal), so a future LinkedIn/Indeed provider (or a new
ranking/dedup/filter implementation) has a contract to conform to.
"""

from app.job_discovery.deduplication import JobDeduplicator
from app.job_discovery.filters import JobFilter
from app.job_discovery.interfaces import (
    JobDeduplicatorProtocol,
    JobFilterProtocol,
    JobProviderProtocol,
    JobRankingEngineProtocol,
)
from app.job_discovery.providers.greenhouse import GreenhouseProvider
from app.job_discovery.ranking import JobRankingEngine

_PROTOCOL_MEMBERS: dict[type, tuple[str, ...]] = {
    JobProviderProtocol: ("provider_name", "source", "fetch_jobs", "health_check"),
    JobRankingEngineProtocol: ("rank",),
    JobDeduplicatorProtocol: ("deduplicate",),
    JobFilterProtocol: ("apply",),
}


def _satisfies(instance: object, protocol: type) -> bool:
    return all(hasattr(instance, member) for member in _PROTOCOL_MEMBERS[protocol])


def test_greenhouse_provider_satisfies_job_provider_protocol() -> None:
    provider = GreenhouseProvider(board_token="acme")
    assert _satisfies(provider, JobProviderProtocol)


def test_job_ranking_engine_satisfies_protocol() -> None:
    assert _satisfies(JobRankingEngine(), JobRankingEngineProtocol)


def test_job_deduplicator_satisfies_protocol() -> None:
    assert _satisfies(JobDeduplicator(), JobDeduplicatorProtocol)


def test_job_filter_satisfies_protocol() -> None:
    assert _satisfies(JobFilter(), JobFilterProtocol)
