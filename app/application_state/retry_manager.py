"""`RetryManager`: decides whether a FAILED application should be retried, and when.

Reuses Sprint 8's `RetryPolicy` hierarchy (`app.graph.retry`) directly
instead of inventing a second backoff scheme — `ExponentialBackoffRetryPolicy`
is a sensible default for a transient portal/network failure, exactly the
same reasoning Sprint 8's own node execution uses it for.
"""

from app.application_state.models import ApplicationState
from app.graph.retry import ExponentialBackoffRetryPolicy, RetryPolicy


class RetryManager:
    def __init__(self, policy: RetryPolicy | None = None) -> None:
        self._policy = policy or ExponentialBackoffRetryPolicy(max_retries=3)

    def can_retry(self, state: ApplicationState) -> bool:
        """Whether `state` (assumed FAILED) is eligible for another attempt."""
        return (
            state.retry_count < state.max_retries and state.retry_count < self._policy.max_retries
        )

    def next_delay_seconds(self, state: ApplicationState) -> float:
        return self._policy.delay_seconds(state.retry_count + 1)
