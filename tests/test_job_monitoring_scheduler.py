"""Unit tests for `app.job_monitoring.scheduler.MonitoringScheduler`."""

import asyncio

import pytest

from app.job_monitoring.exceptions import MonitoringAlreadyRunningError
from app.job_monitoring.scheduler import MonitoringScheduler


async def test_is_running_false_before_start() -> None:
    scheduler = MonitoringScheduler(lambda: _noop(), interval_seconds=10.0)
    assert scheduler.is_running is False


async def _noop() -> None:
    return None


async def test_start_runs_scan_fn_immediately() -> None:
    calls = {"count": 0}

    async def scan() -> None:
        calls["count"] += 1

    scheduler = MonitoringScheduler(scan, interval_seconds=10.0)
    await scheduler.start()
    await asyncio.sleep(0.01)
    assert calls["count"] >= 1
    await scheduler.stop()


async def test_start_twice_raises() -> None:
    scheduler = MonitoringScheduler(_noop, interval_seconds=10.0)
    await scheduler.start()
    with pytest.raises(MonitoringAlreadyRunningError):
        await scheduler.start()
    await scheduler.stop()


async def test_stop_before_start_is_a_no_op() -> None:
    scheduler = MonitoringScheduler(_noop, interval_seconds=10.0)
    await scheduler.stop()  # should not raise
    assert scheduler.is_running is False


async def test_stop_returns_promptly_without_waiting_full_interval() -> None:
    scheduler = MonitoringScheduler(_noop, interval_seconds=100.0)
    await scheduler.start()
    await asyncio.wait_for(scheduler.stop(), timeout=1.0)
    assert scheduler.is_running is False


async def test_scan_fn_exception_does_not_stop_the_loop() -> None:
    calls = {"count": 0}

    async def flaky_scan() -> None:
        calls["count"] += 1
        raise RuntimeError("boom")

    scheduler = MonitoringScheduler(flaky_scan, interval_seconds=0.01)
    await scheduler.start()
    await asyncio.sleep(0.05)
    await scheduler.stop()
    assert calls["count"] >= 2  # ran more than once despite raising every time


async def test_repeated_start_stop_cycles_work() -> None:
    scheduler = MonitoringScheduler(_noop, interval_seconds=10.0)
    await scheduler.start()
    await scheduler.stop()
    await scheduler.start()
    assert scheduler.is_running is True
    await scheduler.stop()
