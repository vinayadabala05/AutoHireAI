"""Graceful shutdown, composed into the same lifespan Sprint 1's `app.main.lifespan` runs.

`build_production_lifespan()` wraps Sprint 1's `lifespan` (imported, never
modified) rather than replacing it: Sprint 1's own shutdown step —
disposing the shared DB engine — still runs, just *after* this module's
extra step (stopping a background worker, if one was started) so a
worker mid-poll never loses its database connection out from under it.
"""

import asyncio
from collections.abc import AsyncGenerator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Protocol

from fastapi import FastAPI
from loguru import logger

from deployment.settings import DeploymentSettings

Lifespan = Callable[[FastAPI], AbstractAsyncContextManager[None]]


class StoppableWorker(Protocol):
    """Structural shape `JobMonitoringService` (Sprint 11) already satisfies."""

    @property
    def is_running(self) -> bool: ...

    async def stop_monitoring(self) -> None: ...


async def stop_background_worker(worker: StoppableWorker, timeout_seconds: float) -> None:
    """Stop `worker` if it's running, within `timeout_seconds`. Never raises."""
    if not worker.is_running:
        return
    try:
        await asyncio.wait_for(worker.stop_monitoring(), timeout=timeout_seconds)
        logger.info("Background worker stopped gracefully.")
    except TimeoutError:
        logger.error(
            "Background worker did not stop within {}s; abandoning the wait.", timeout_seconds
        )


def build_production_lifespan(
    base_lifespan: Lifespan,
    ops_settings: DeploymentSettings,
    worker: StoppableWorker | None = None,
) -> Lifespan:
    """Wrap `base_lifespan` with a graceful-worker-stop step before its own shutdown."""

    @asynccontextmanager
    async def _lifespan(app: FastAPI) -> AsyncGenerator[None]:
        async with base_lifespan(app):
            yield
            if worker is not None:
                await stop_background_worker(worker, ops_settings.GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS)

    return _lifespan
