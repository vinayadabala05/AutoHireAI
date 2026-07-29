"""Exception hierarchy for the Job Discovery Engine.

Mirrors `app.llm.exceptions`: a single base class, plus specific subclasses
so callers can catch broadly (`JobDiscoveryError`) or narrowly (e.g. only
`ProviderFetchError` to retry transient network failures).
"""


class JobDiscoveryError(Exception):
    """Base class for every exception raised by `app.job_discovery`."""


class ProviderNotFoundError(JobDiscoveryError):
    """Raised when a provider is looked up by a `JobSource` with no registration."""


class ProviderFetchError(JobDiscoveryError):
    """Raised when a provider's network call fails. Transient; safe to retry."""


class InvalidJobPayloadError(JobDiscoveryError):
    """Raised when a provider's response cannot be parsed into a `DiscoveredJob`."""
