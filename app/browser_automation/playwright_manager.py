"""Playwright/Chromium process lifecycle management.

Owns the single `async_playwright()` context and the `Browser` instance;
every `BrowserContext` is created through here so `stop()` guarantees
everything is closed, even after a failure partway through a run.
"""

from types import TracebackType
from typing import Self

from loguru import logger
from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright

from app.browser_automation.models import BrowserConfig


class PlaywrightManager:
    """Launches and owns exactly one Chromium `Browser` for its lifetime."""

    def __init__(self, config: BrowserConfig | None = None) -> None:
        self.config = config or BrowserConfig()
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    async def start(self) -> Browser:
        """Launch Chromium. Idempotent — returns the existing browser if already started."""
        if self._browser is not None:
            return self._browser
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.config.headless, slow_mo=self.config.slow_mo_ms
        )
        logger.info("Launched Chromium (headless={}).", self.config.headless)
        return self._browser

    async def new_context(self, storage_state: str | None = None) -> BrowserContext:
        """Create a fresh `BrowserContext`, optionally restoring a persisted `storage_state`."""
        browser = await self.start()
        context = await browser.new_context(
            viewport={"width": self.config.viewport_width, "height": self.config.viewport_height},
            user_agent=self.config.user_agent,
            storage_state=storage_state,
        )
        context.set_default_navigation_timeout(self.config.navigation_timeout_ms)
        context.set_default_timeout(self.config.navigation_timeout_ms)
        return context

    async def stop(self) -> None:
        """Close the browser and stop Playwright. Safe to call more than once."""
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None
        logger.info("Playwright stopped and browser closed.")

    async def __aenter__(self) -> Self:
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.stop()
