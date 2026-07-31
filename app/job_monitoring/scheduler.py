"""`MonitoringScheduler`: a real, time-based interval loop.

Sprints 7 and 8 each shipped a scheduler.py that deliberately stopped at
"prepare the architecture — no cron/interval implementation yet." This is
where that gets resolved for real: an `asyncio`-based interval loop
supporting manual polling (`scan_fn()` called directly, no scheduler
involved), scheduled polling (`start()` with a fixed interval), and
continuous monitoring (the same loop, left running indefinitely until
`stop()`). No external scheduler/cron dependency — plain `asyncio`.
"""

import asyncio
import contextlib
from collections.abc import Awaitable, Callable

from loguru import logger

from app.job_monitoring.exceptions import MonitoringAlreadyRunningError


class MonitoringScheduler:
    def __init__(self, scan_fn: Callable[[], Awaitable[None]], interval_seconds: float) -> None:
        self._scan_fn = scan_fn
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        """Start the interval loop. Raises if already running."""
        if self.is_running:
            raise MonitoringAlreadyRunningError("Monitoring scheduler is already running.")
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Monitoring scheduler started (interval={}s).", self.interval_seconds)

    async def stop(self) -> None:
        """Stop the interval loop. A no-op if not running."""
        if not self.is_running:
            return
        self._stop_event.set()
        assert self._task is not None
        await self._task
        self._task = None
        logger.info("Monitoring scheduler stopped.")

    async def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._scan_fn()
            except Exception as exc:
                logger.error("Scheduled scan failed: {}", exc)
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval_seconds)
