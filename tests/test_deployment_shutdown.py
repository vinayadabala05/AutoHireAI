"""Unit tests for `deployment.shutdown`."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from deployment.settings import DeploymentSettings
from deployment.shutdown import build_production_lifespan, stop_background_worker


class _FakeWorker:
    def __init__(self, *, running: bool, hang: bool = False) -> None:
        self.running = running
        self.hang = hang
        self.stop_called = False

    @property
    def is_running(self) -> bool:
        return self.running

    async def stop_monitoring(self) -> None:
        self.stop_called = True
        if self.hang:
            await asyncio.sleep(10)
        self.running = False


async def test_stop_background_worker_noop_when_not_running() -> None:
    worker = _FakeWorker(running=False)
    await stop_background_worker(worker, timeout_seconds=1.0)
    assert worker.stop_called is False


async def test_stop_background_worker_stops_a_running_worker() -> None:
    worker = _FakeWorker(running=True)
    await stop_background_worker(worker, timeout_seconds=1.0)
    assert worker.stop_called is True
    assert worker.running is False


async def test_stop_background_worker_gives_up_after_timeout() -> None:
    worker = _FakeWorker(running=True, hang=True)
    await stop_background_worker(worker, timeout_seconds=0.05)  # must not raise
    assert worker.stop_called is True


async def test_build_production_lifespan_runs_worker_stop_before_base_shutdown() -> None:
    events: list[str] = []

    @asynccontextmanager
    async def fake_base_lifespan(app: FastAPI) -> AsyncGenerator[None]:
        events.append("base-start")
        yield
        events.append("base-end")

    worker = _FakeWorker(running=True)
    lifespan = build_production_lifespan(fake_base_lifespan, DeploymentSettings(), worker)

    async with lifespan(FastAPI()):
        events.append("serving")

    assert events == ["base-start", "serving", "base-end"]
    assert worker.stop_called is True


async def test_build_production_lifespan_without_worker_is_a_passthrough() -> None:
    @asynccontextmanager
    async def fake_base_lifespan(app: FastAPI) -> AsyncGenerator[None]:
        yield

    lifespan = build_production_lifespan(fake_base_lifespan, DeploymentSettings(), worker=None)
    async with lifespan(FastAPI()):
        pass  # must not raise
