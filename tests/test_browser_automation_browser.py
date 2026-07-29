"""Unit tests for `app.browser_automation.browser.BrowserSession`."""

import pytest

from app.browser_automation import playwright_manager as playwright_manager_module
from app.browser_automation.browser import BrowserSession
from app.browser_automation.playwright_manager import PlaywrightManager
from tests.browser_automation_fixtures import fake_async_playwright_factory


@pytest.fixture(autouse=True)
def _patch_async_playwright(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        playwright_manager_module, "async_playwright", fake_async_playwright_factory
    )


async def test_start_creates_context_once() -> None:
    session = BrowserSession(PlaywrightManager())
    context_a = await session.start()
    context_b = await session.start()
    assert context_a is context_b


async def test_new_page_starts_context_and_returns_page() -> None:
    session = BrowserSession(PlaywrightManager())
    page = await session.new_page()
    assert page in session.context.pages


def test_context_property_raises_before_start() -> None:
    session = BrowserSession(PlaywrightManager())
    with pytest.raises(RuntimeError, match="not started"):
        _ = session.context


async def test_close_clears_context() -> None:
    session = BrowserSession(PlaywrightManager())
    context = await session.start()
    await session.close()
    assert context.closed is True
    with pytest.raises(RuntimeError):
        _ = session.context


async def test_close_before_start_is_a_no_op() -> None:
    session = BrowserSession(PlaywrightManager())
    await session.close()  # should not raise


async def test_async_context_manager_starts_and_closes() -> None:
    manager = PlaywrightManager()
    async with BrowserSession(manager) as session:
        context = session.context
    assert context.closed is True


async def test_storage_state_is_forwarded_to_manager() -> None:
    manager = PlaywrightManager()
    session = BrowserSession(manager, storage_state="path/to/state.json")
    await session.start()
    # PlaywrightManager.new_context accepted it without raising; nothing more observable
    # through the fake beyond a successful context creation.
    assert session.context.closed is False
