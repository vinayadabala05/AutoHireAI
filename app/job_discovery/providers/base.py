"""Abstract base provider contract + self-registration registry.

Mirrors `app.llm.base`/`app.llm.registry`: a provider only needs to
subclass `BaseJobProvider` and decorate itself with `@register_provider`.
Adding LinkedIn or Indeed later is exactly one new file in `providers/`
plus one import in `providers/__init__.py` — no change to
`JobDiscoveryService`, `ranking.py`, `deduplication.py`, or `filters.py`,
since all of those operate on `DiscoveredJob`, never on a provider's raw
vendor payload.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

import httpx

from app.job_discovery.exceptions import ProviderFetchError, ProviderNotFoundError
from app.job_discovery.models import DiscoveredJob, JobProviderName, JobSearchQuery
from app.models.enums import JobSource

_DEFAULT_TIMEOUT_SECONDS = 10.0

_PROVIDER_REGISTRY: dict[JobProviderName, type["BaseJobProvider"]] = {}


def register_provider(
    name: JobProviderName,
) -> Callable[[type["BaseJobProvider"]], type["BaseJobProvider"]]:
    """Class decorator that registers a `BaseJobProvider` subclass under `name`."""

    def decorator(provider_cls: type["BaseJobProvider"]) -> type["BaseJobProvider"]:
        _PROVIDER_REGISTRY[name] = provider_cls
        return provider_cls

    return decorator


def get_provider_class(name: JobProviderName) -> type["BaseJobProvider"]:
    """Look up a registered provider class by `JobProviderName`.

    Raises `ProviderNotFoundError` if no provider is registered under `name`.
    """
    try:
        return _PROVIDER_REGISTRY[name]
    except KeyError as exc:
        raise ProviderNotFoundError(f"No job provider registered under name '{name}'") from exc


def available_providers() -> list[JobProviderName]:
    """Return every currently registered `JobProviderName`."""
    return sorted(_PROVIDER_REGISTRY, key=lambda name: name.value)


class BaseJobProvider(ABC):
    """Contract every concrete job board provider must implement."""

    def __init__(self, board_token: str, timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS) -> None:
        self.board_token = board_token
        self.timeout_seconds = timeout_seconds

    @property
    @abstractmethod
    def provider_name(self) -> JobProviderName:
        """The registry key this provider integration is identified by."""

    @property
    @abstractmethod
    def source(self) -> JobSource:
        """The `JobSource` category stamped onto every job this provider returns."""

    @abstractmethod
    async def fetch_jobs(self, query: JobSearchQuery) -> list[DiscoveredJob]:
        """Fetch and parse postings matching `query` into `DiscoveredJob`s.

        Raises `ProviderFetchError` for a transient network/HTTP failure.
        Malformed individual postings should be skipped, not raised — one
        bad entry in a 200-job board response shouldn't fail the whole
        fetch.
        """

    async def health_check(self) -> bool:
        """Return True if the provider's board is reachable.

        Default implementation attempts a real (empty) fetch; providers
        may override this if a cheaper reachability check exists.
        """
        try:
            await self.fetch_jobs(JobSearchQuery(limit=1))
        except ProviderFetchError:
            return False
        return True

    async def _get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            raise ProviderFetchError(f"{self.provider_name.value} fetch failed: {exc}") from exc
