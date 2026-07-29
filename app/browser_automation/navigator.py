"""Generic page navigation: opening job pages, clicking Apply, smart waits,
timeout handling, and redirect detection.

Portal-specific selectors always come from a `PortalAdapter` (`portal.py`)
— this module only knows how to *use* a selector it's handed, never which
one to pick for a given portal.
"""

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.browser_automation.exceptions import NavigationError
from app.browser_automation.interfaces import PortalAdapterProtocol


class Navigator:
    def __init__(self, timeout_ms: float = 30_000.0) -> None:
        self.timeout_ms = timeout_ms

    async def open_job_page(self, page: Page, url: str) -> None:
        """Open `url`. Raises `NavigationError` on timeout."""
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
        except PlaywrightTimeoutError as exc:
            raise NavigationError(f"Timed out opening job page '{url}': {exc}") from exc

    async def click_apply(self, page: Page, adapter: PortalAdapterProtocol) -> None:
        """Find and click the portal's Apply control.

        Raises `NavigationError` if no Apply control is found. A missing
        post-click navigation event is not an error — some portals (e.g.
        LinkedIn Easy Apply) open an in-page modal instead of navigating.
        """
        selector = await adapter.find_apply_button(page)
        if selector is None:
            raise NavigationError(
                f"Could not find an Apply button for portal '{adapter.portal_type.value}'."
            )
        try:
            async with page.expect_navigation(timeout=self.timeout_ms):
                await page.click(selector, timeout=self.timeout_ms)
        except PlaywrightTimeoutError:
            pass

    async def wait_for_selector(
        self, page: Page, selector: str, timeout_ms: float | None = None
    ) -> bool:
        """Wait for `selector` to appear. Returns `False` (never raises) on timeout."""
        try:
            await page.wait_for_selector(selector, timeout=timeout_ms or self.timeout_ms)
            return True
        except PlaywrightTimeoutError:
            return False

    async def wait_for_redirect(
        self, page: Page, expected_url_substring: str, timeout_ms: float | None = None
    ) -> bool:
        """Wait for the page URL to contain `expected_url_substring`. Never raises."""
        try:
            await page.wait_for_url(
                f"**/*{expected_url_substring}*", timeout=timeout_ms or self.timeout_ms
            )
            return True
        except PlaywrightTimeoutError:
            return False
