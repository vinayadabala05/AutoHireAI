"""Retry helper for browser actions.

Deliberately does not redefine a retry-policy hierarchy — Sprint 8
(`app.graph.retry`) already ships one (immediate, fixed-delay, exponential
backoff, configurable retryable-exception filtering), fully tested. This
module is a thin `async def` wrapper applying an injected `RetryPolicy` to
a single browser action, so `executor.py` doesn't hand-roll its own
retry loop.
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from loguru import logger

from app.graph.retry import RetryPolicy

T = TypeVar("T")


async def retry_action(
    action: Callable[[], Awaitable[T]],
    policy: RetryPolicy,
    action_name: str = "action",
) -> T:
    """Run `action()`, retrying per `policy` on a retryable exception.

    Re-raises the final exception once `policy` says no further retry
    should happen (either the exception type isn't retryable, or
    `max_retries` has been exhausted).
    """
    attempt = 0
    while True:
        try:
            return await action()
        except Exception as exc:
            next_attempt = attempt + 1
            if not policy.is_retryable(next_attempt, exc):
                raise
            delay = policy.delay_seconds(next_attempt)
            logger.warning(
                "Retrying {} (attempt {}) after error: {}", action_name, next_attempt, exc
            )
            if delay > 0:
                await asyncio.sleep(delay)
            attempt = next_attempt
