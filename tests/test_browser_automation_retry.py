"""Unit tests for `app.browser_automation.retry.retry_action`."""

import pytest

from app.browser_automation.retry import retry_action
from app.graph.retry import FixedDelayRetryPolicy, NoRetryPolicy


async def test_retry_action_returns_result_on_first_success() -> None:
    async def action() -> str:
        return "ok"

    assert await retry_action(action, NoRetryPolicy()) == "ok"


async def test_retry_action_raises_immediately_with_no_retry_policy() -> None:
    async def action() -> str:
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        await retry_action(action, NoRetryPolicy())


async def test_retry_action_retries_and_eventually_succeeds() -> None:
    calls = {"count": 0}

    async def action() -> str:
        calls["count"] += 1
        if calls["count"] < 3:
            raise RuntimeError("transient")
        return "recovered"

    result = await retry_action(action, FixedDelayRetryPolicy(0.0, max_retries=3), "test_action")
    assert result == "recovered"
    assert calls["count"] == 3


async def test_retry_action_raises_after_exhausting_retries() -> None:
    async def action() -> str:
        raise RuntimeError("always fails")

    with pytest.raises(RuntimeError, match="always fails"):
        await retry_action(action, FixedDelayRetryPolicy(0.0, max_retries=2))


async def test_retry_action_sleeps_for_a_positive_delay() -> None:
    calls = {"count": 0}

    async def action() -> str:
        calls["count"] += 1
        if calls["count"] < 2:
            raise RuntimeError("transient")
        return "recovered"

    result = await retry_action(action, FixedDelayRetryPolicy(0.01, max_retries=1))
    assert result == "recovered"
