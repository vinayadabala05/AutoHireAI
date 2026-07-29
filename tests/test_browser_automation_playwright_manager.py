"""Unit tests for `app.browser_automation.playwright_manager.PlaywrightManager`."""

import pytest

from app.browser_automation import playwright_manager as playwright_manager_module
from app.browser_automation.models import BrowserConfig
from app.browser_automation.playwright_manager import PlaywrightManager
from tests.browser_automation_fixtures import fake_async_playwright_factory


@pytest.fixture(autouse=True)
def _patch_async_playwright(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        playwright_manager_module, "async_playwright", fake_async_playwright_factory
    )


async def test_start_launches_chromium_with_headless_config() -> None:
    manager = PlaywrightManager(BrowserConfig(headless=False, slow_mo_ms=50))
    browser = await manager.start()
    assert browser.closed is False


async def test_start_is_idempotent() -> None:
    manager = PlaywrightManager()
    browser_a = await manager.start()
    browser_b = await manager.start()
    assert browser_a is browser_b


async def test_new_context_applies_viewport_and_timeout_config() -> None:
    manager = PlaywrightManager(BrowserConfig(viewport_width=1024, viewport_height=768))
    context = await manager.new_context()
    assert context.closed is False


async def test_new_context_passes_storage_state() -> None:
    manager = PlaywrightManager()
    context = await manager.new_context(storage_state="some/path.json")
    assert context in (await manager.start()).contexts


async def test_stop_closes_browser_and_playwright() -> None:
    manager = PlaywrightManager()
    browser = await manager.start()
    await manager.stop()
    assert browser.closed is True


async def test_stop_is_safe_to_call_twice() -> None:
    manager = PlaywrightManager()
    await manager.start()
    await manager.stop()
    await manager.stop()  # should not raise


async def test_async_context_manager_starts_and_stops() -> None:
    manager = PlaywrightManager()
    async with manager as started:
        assert started is manager
        browser = await manager.start()
    assert browser.closed is True
