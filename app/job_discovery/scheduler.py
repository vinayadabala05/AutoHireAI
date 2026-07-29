"""Scheduler architecture for future background polling.

This sprint deliberately does **not** implement cron or interval-based
polling — only the registration bookkeeping and a single-shot execution
path (`run_once`) a future scheduler backend (APScheduler, Celery beat, a
plain cron entrypoint calling into this module on a timer) will drive.
Wiring that backend later only needs to call `run_once(provider_name)` for
each `PollingRegistration` on its own interval; no change to this class,
`JobDiscoveryService`, or any provider is required.

The scheduler is deliberately decoupled from `JobDiscoveryService` and from
any concrete provider class — it stores an injected async `fetch` callable
per registration (typically a provider's own `fetch_jobs`), so it has no
import dependency on `service.py` and no circular-import risk.
"""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from app.job_discovery.models import (
    DiscoveredJob,
    JobProviderName,
    JobSearchQuery,
    PollingRegistration,
)

FetchCallable = Callable[[JobSearchQuery], Awaitable[list[DiscoveredJob]]]


class JobDiscoveryScheduler:
    """Registers providers for future periodic polling."""

    def __init__(self) -> None:
        self._registrations: dict[JobProviderName, PollingRegistration] = {}
        self._fetchers: dict[JobProviderName, FetchCallable] = {}

    def register(
        self,
        provider_name: JobProviderName,
        query: JobSearchQuery,
        interval_seconds: int,
        fetch: FetchCallable,
    ) -> PollingRegistration:
        registration = PollingRegistration(
            provider_name=provider_name, query=query, interval_seconds=interval_seconds
        )
        self._registrations[provider_name] = registration
        self._fetchers[provider_name] = fetch
        return registration

    def unregister(self, provider_name: JobProviderName) -> None:
        self._registrations.pop(provider_name, None)
        self._fetchers.pop(provider_name, None)

    def is_registered(self, provider_name: JobProviderName) -> bool:
        return provider_name in self._registrations

    def list_registrations(self) -> list[PollingRegistration]:
        return list(self._registrations.values())

    async def run_once(self, provider_name: JobProviderName) -> list[DiscoveredJob]:
        """Execute a single poll immediately for a registered provider.

        This is the only execution path implemented this sprint — no
        internal timer or loop calls it automatically. Raises `KeyError`
        if `provider_name` was never registered.
        """
        registration = self._registrations[provider_name]
        fetch = self._fetchers[provider_name]
        jobs = await fetch(registration.query)
        self._registrations[provider_name] = registration.model_copy(
            update={"last_run_at": datetime.now(UTC)}
        )
        return jobs
