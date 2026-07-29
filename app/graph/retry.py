"""Retry policies for node execution.

Every policy answers two questions for `executor.py`: *should this
exception be retried at all* (`is_retryable`) and *how long to wait before
attempt N* (`delay_seconds`). `max_retries` is the number of retries after
the first attempt — `max_retries=2` means up to 3 total attempts.
"""

from abc import ABC, abstractmethod


class RetryPolicy(ABC):
    def __init__(
        self,
        max_retries: int = 0,
        retryable_exceptions: tuple[type[BaseException], ...] = (Exception,),
    ) -> None:
        self.max_retries = max_retries
        self.retryable_exceptions = retryable_exceptions

    def is_retryable(self, attempt: int, exc: BaseException) -> bool:
        """Whether attempt `attempt` (0-indexed retry number) should happen.

        `attempt` is the retry number about to be made (1 for the first
        retry after the initial attempt), so `attempt <= max_retries` gates
        the retry count and `isinstance` gates the exception type.
        """
        return attempt <= self.max_retries and isinstance(exc, self.retryable_exceptions)

    @abstractmethod
    def delay_seconds(self, attempt: int) -> float:
        """Seconds to wait before making retry number `attempt` (1-indexed)."""


class NoRetryPolicy(RetryPolicy):
    """Never retries — the first failure is final."""

    def __init__(self) -> None:
        super().__init__(max_retries=0, retryable_exceptions=())

    def delay_seconds(self, attempt: int) -> float:
        return 0.0


class ImmediateRetryPolicy(RetryPolicy):
    """Retries immediately, with no delay between attempts."""

    def delay_seconds(self, attempt: int) -> float:
        return 0.0


class FixedDelayRetryPolicy(RetryPolicy):
    """Waits a constant delay before every retry."""

    def __init__(
        self,
        delay_seconds_value: float,
        max_retries: int = 3,
        retryable_exceptions: tuple[type[BaseException], ...] = (Exception,),
    ) -> None:
        super().__init__(max_retries, retryable_exceptions)
        self._delay = delay_seconds_value

    def delay_seconds(self, attempt: int) -> float:
        return self._delay


class ExponentialBackoffRetryPolicy(RetryPolicy):
    """Waits `base_delay * (factor ** (attempt - 1))`, capped at `max_delay`."""

    def __init__(
        self,
        base_delay: float = 1.0,
        factor: float = 2.0,
        max_delay: float = 60.0,
        max_retries: int = 3,
        retryable_exceptions: tuple[type[BaseException], ...] = (Exception,),
    ) -> None:
        super().__init__(max_retries, retryable_exceptions)
        self.base_delay = base_delay
        self.factor = factor
        self.max_delay = max_delay

    def delay_seconds(self, attempt: int) -> float:
        return min(self.max_delay, self.base_delay * (self.factor ** (attempt - 1)))
