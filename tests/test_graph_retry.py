"""Unit tests for `app.graph.retry` retry policies."""

from app.graph.retry import (
    ExponentialBackoffRetryPolicy,
    FixedDelayRetryPolicy,
    ImmediateRetryPolicy,
    NoRetryPolicy,
)


def test_no_retry_policy_never_retries() -> None:
    policy = NoRetryPolicy()
    assert policy.is_retryable(1, ValueError()) is False
    assert policy.delay_seconds(1) == 0.0


def test_immediate_retry_policy_has_no_delay() -> None:
    policy = ImmediateRetryPolicy(max_retries=2)
    assert policy.delay_seconds(1) == 0.0
    assert policy.delay_seconds(2) == 0.0


def test_immediate_retry_policy_respects_max_retries() -> None:
    policy = ImmediateRetryPolicy(max_retries=2)
    assert policy.is_retryable(1, ValueError()) is True
    assert policy.is_retryable(2, ValueError()) is True
    assert policy.is_retryable(3, ValueError()) is False


def test_fixed_delay_retry_policy_constant_delay() -> None:
    policy = FixedDelayRetryPolicy(2.5, max_retries=3)
    assert policy.delay_seconds(1) == 2.5
    assert policy.delay_seconds(3) == 2.5


def test_exponential_backoff_grows_and_caps() -> None:
    policy = ExponentialBackoffRetryPolicy(base_delay=1.0, factor=2.0, max_delay=5.0, max_retries=5)
    assert policy.delay_seconds(1) == 1.0
    assert policy.delay_seconds(2) == 2.0
    assert policy.delay_seconds(3) == 4.0
    assert policy.delay_seconds(4) == 5.0  # capped at max_delay (would be 8.0 uncapped)


def test_retryable_exceptions_gate_is_retryable() -> None:
    policy = FixedDelayRetryPolicy(0.0, max_retries=3, retryable_exceptions=(ValueError,))
    assert policy.is_retryable(1, ValueError("x")) is True
    assert policy.is_retryable(1, TypeError("x")) is False


def test_no_retry_policy_rejects_all_exception_types() -> None:
    policy = NoRetryPolicy()
    assert policy.is_retryable(1, TypeError()) is False
    assert policy.is_retryable(1, RuntimeError()) is False


def test_is_retryable_false_once_max_retries_exceeded() -> None:
    policy = ExponentialBackoffRetryPolicy(max_retries=2)
    assert policy.is_retryable(2, ValueError()) is True
    assert policy.is_retryable(3, ValueError()) is False


def test_default_retryable_exceptions_matches_any_exception() -> None:
    policy = FixedDelayRetryPolicy(0.0, max_retries=1)
    assert policy.is_retryable(1, KeyError()) is True
    assert policy.is_retryable(1, Exception()) is True


def test_exponential_backoff_default_constructor_values() -> None:
    policy = ExponentialBackoffRetryPolicy()
    assert policy.base_delay == 1.0
    assert policy.factor == 2.0
    assert policy.max_retries == 3
