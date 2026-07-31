"""Fake Playwright objects for Sprint 10 Browser Automation tests.

No test in this suite launches a real browser — every Playwright
interaction is behind a small async surface (`Page.goto`, `.click`,
`.locator(...)`, ...) that these fakes implement, mirroring how Sprint
4/7 test LLM/HTTP providers by faking the one boundary method rather than
hitting a real network or, here, a real Chromium process.
"""

from pathlib import Path
from typing import Any

from playwright.async_api import TimeoutError as PlaywrightTimeoutError


class _ExpectNavigationCtx:
    def __init__(self, page: "FakePage") -> None:
        self._page = page

    async def __aenter__(self) -> "_ExpectNavigationCtx":
        return self

    async def __aexit__(self, *args: object) -> bool:
        return False


class FakeLocator:
    def __init__(self, page: "FakePage", selector: str) -> None:
        self._page = page
        self.selector = selector

    async def count(self) -> int:
        return self._page.selector_counts.get(self.selector, 0)

    async def evaluate(self, script: str) -> Any:
        if "tagName" in script:
            return self._page.tag_names.get(self.selector, "input")
        if "files" in script:
            return self.selector in self._page.uploaded_files
        return self._page.input_types.get(self.selector, "text")

    async def fill(self, value: str, timeout: float | None = None) -> None:
        self._page.filled_values[self.selector] = value

    async def select_option(self, label: str) -> None:
        self._page.filled_values[self.selector] = label

    async def check(self) -> None:
        self._page.checked_selectors.add(self.selector)

    async def uncheck(self) -> None:
        self._page.checked_selectors.discard(self.selector)

    async def set_input_files(self, path: str) -> None:
        self._page.uploaded_files[self.selector] = path


class FakePage:
    def __init__(self, url: str = "https://example.com/job/1") -> None:
        self.url = url
        self.selector_counts: dict[str, int] = {}
        self.tag_names: dict[str, str] = {}
        self.input_types: dict[str, str] = {}
        self.filled_values: dict[str, str] = {}
        self.checked_selectors: set[str] = set()
        self.uploaded_files: dict[str, str] = {}
        self.clicked: list[str] = []
        self.goto_calls: list[str] = []
        self.screenshot_calls: list[str] = []
        self.closed = False
        self.raise_on_goto = False
        self.goto_fail_times = 0
        self.raise_on_click: set[str] = set()
        self.wait_for_selector_result = True
        self.wait_for_url_result = True

    def locator(self, selector: str) -> FakeLocator:
        return FakeLocator(self, selector)

    async def goto(self, url: str, wait_until: str = "load", timeout: float = 0) -> None:
        self.goto_calls.append(url)
        if self.raise_on_goto:
            raise PlaywrightTimeoutError("goto timed out")
        if self.goto_fail_times > 0:
            self.goto_fail_times -= 1
            raise PlaywrightTimeoutError("goto timed out (transient)")
        self.url = url

    async def click(self, selector: str, timeout: float = 0) -> None:
        self.clicked.append(selector)
        if selector in self.raise_on_click:
            raise PlaywrightTimeoutError(f"click on {selector} timed out")

    async def fill(self, selector: str, value: str) -> None:
        self.filled_values[selector] = value

    def expect_navigation(self, timeout: float = 0) -> _ExpectNavigationCtx:
        return _ExpectNavigationCtx(self)

    async def wait_for_selector(self, selector: str, timeout: float = 0) -> None:
        if not self.wait_for_selector_result:
            raise PlaywrightTimeoutError("wait_for_selector timed out")

    async def wait_for_url(self, pattern: str, timeout: float = 0) -> None:
        if not self.wait_for_url_result:
            raise PlaywrightTimeoutError("wait_for_url timed out")

    async def close(self) -> None:
        self.closed = True

    async def screenshot(self, path: str) -> None:
        self.screenshot_calls.append(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("fake-screenshot", encoding="utf-8")


class FakeBrowserContext:
    def __init__(self) -> None:
        self.pages: list[FakePage] = []
        self.closed = False
        self.storage_state_calls: list[str] = []

    async def new_page(self) -> FakePage:
        page = FakePage()
        self.pages.append(page)
        return page

    async def storage_state(self, path: str) -> None:
        self.storage_state_calls.append(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("{}", encoding="utf-8")

    async def close(self) -> None:
        self.closed = True

    def set_default_navigation_timeout(self, timeout_ms: float) -> None:
        return None

    def set_default_timeout(self, timeout_ms: float) -> None:
        return None


class FakeBrowser:
    def __init__(self) -> None:
        self.contexts: list[FakeBrowserContext] = []
        self.closed = False

    async def new_context(self, **kwargs: object) -> FakeBrowserContext:
        context = FakeBrowserContext()
        self.contexts.append(context)
        return context

    async def close(self) -> None:
        self.closed = True


class FakeChromium:
    def __init__(self, browser: FakeBrowser) -> None:
        self._browser = browser
        self.launch_calls: list[dict[str, object]] = []

    async def launch(self, **kwargs: object) -> FakeBrowser:
        self.launch_calls.append(kwargs)
        return self._browser


class FakePlaywright:
    def __init__(self) -> None:
        self.chromium = FakeChromium(FakeBrowser())
        self.stopped = False

    async def stop(self) -> None:
        self.stopped = True


class FakeAsyncPlaywrightContextManager:
    def __init__(self) -> None:
        self.playwright = FakePlaywright()

    async def start(self) -> FakePlaywright:
        return self.playwright


def fake_async_playwright_factory() -> FakeAsyncPlaywrightContextManager:
    return FakeAsyncPlaywrightContextManager()
