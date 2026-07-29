"""Unit tests for `app.browser_automation.navigator.Navigator`."""

import pytest

from app.browser_automation.exceptions import NavigationError
from app.browser_automation.navigator import Navigator
from app.browser_automation.portal import GreenhouseAdapter
from tests.browser_automation_fixtures import FakePage


async def test_open_job_page_navigates() -> None:
    page = FakePage()
    await Navigator().open_job_page(page, "https://example.com/job/1")
    assert page.goto_calls == ["https://example.com/job/1"]


async def test_open_job_page_raises_navigation_error_on_timeout() -> None:
    page = FakePage()
    page.raise_on_goto = True
    with pytest.raises(NavigationError):
        await Navigator().open_job_page(page, "https://example.com/job/1")


async def test_click_apply_raises_when_no_button_found() -> None:
    page = FakePage()
    with pytest.raises(NavigationError):
        await Navigator().click_apply(page, GreenhouseAdapter())


async def test_click_apply_clicks_the_found_selector() -> None:
    page = FakePage()
    page.selector_counts["a:has-text('Apply for this job')"] = 1
    await Navigator().click_apply(page, GreenhouseAdapter())
    assert "a:has-text('Apply for this job')" in page.clicked


async def test_click_apply_tolerates_missing_navigation_event() -> None:
    # Simulates a portal (e.g. LinkedIn) opening a modal instead of navigating:
    # expect_navigation's timeout should be swallowed, not raised.
    page = FakePage()
    page.selector_counts["a:has-text('Apply for this job')"] = 1
    page.raise_on_click.add("a:has-text('Apply for this job')")
    await Navigator().click_apply(page, GreenhouseAdapter())  # should not raise


async def test_wait_for_selector_true_when_found() -> None:
    page = FakePage()
    assert await Navigator().wait_for_selector(page, "#anything") is True


async def test_wait_for_selector_false_on_timeout() -> None:
    page = FakePage()
    page.wait_for_selector_result = False
    assert await Navigator().wait_for_selector(page, "#anything") is False


async def test_wait_for_redirect_true_when_matched() -> None:
    page = FakePage()
    assert await Navigator().wait_for_redirect(page, "thanks") is True


async def test_wait_for_redirect_false_on_timeout() -> None:
    page = FakePage()
    page.wait_for_url_result = False
    assert await Navigator().wait_for_redirect(page, "thanks") is False


async def test_custom_timeout_is_honored_in_constructor() -> None:
    navigator = Navigator(timeout_ms=5000.0)
    assert navigator.timeout_ms == 5000.0
