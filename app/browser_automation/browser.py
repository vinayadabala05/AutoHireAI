"""`BrowserSession`: one reusable browser context + page, with cleanup guaranteed.

`PlaywrightManager` owns the process-wide `Browser`; `BrowserSession` owns
one `BrowserContext` — reusable across multiple job applications in the
same run ("browser context reuse") — and hands out `Page`s, closing the
context via `close()`/the async context manager protocol even if a step
partway through an application fails.
"""

from types import TracebackType
from typing import Self

from loguru import logger
from playwright.async_api import BrowserContext, Page

from app.browser_automation.playwright_manager import PlaywrightManager


class BrowserSession:
    def __init__(self, manager: PlaywrightManager, storage_state: str | None = None) -> None:
        self._manager = manager
        self._storage_state = storage_state
        self._context: BrowserContext | None = None

    async def start(self) -> BrowserContext:
        """Create the underlying `BrowserContext` if not already started. Idempotent."""
        if self._context is None:
            self._context = await self._manager.new_context(storage_state=self._storage_state)
        return self._context

    async def new_page(self) -> Page:
        context = await self.start()
        return await context.new_page()

    @property
    def context(self) -> BrowserContext:
        if self._context is None:
            raise RuntimeError("BrowserSession not started — call start() or new_page() first.")
        return self._context

    async def close(self) -> None:
        """Close the context. Safe to call more than once."""
        if self._context is not None:
            await self._context.close()
            self._context = None
            logger.info("Closed browser context.")

    async def __aenter__(self) -> Self:
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()
