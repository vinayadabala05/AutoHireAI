"""Unit tests for `app.browser_automation.portal` — registry + adapters."""

import pytest

from app.browser_automation.exceptions import PortalNotSupportedError
from app.browser_automation.models import FormFieldType, PortalType
from app.browser_automation.portal import (
    AshbyAdapter,
    GreenhouseAdapter,
    LeverAdapter,
    LinkedInEasyApplyAdapter,
    available_portals,
    get_portal_adapter,
)
from tests.browser_automation_fixtures import FakePage


def test_available_portals_includes_all_four_built_ins() -> None:
    assert set(available_portals()) == {
        PortalType.LINKEDIN,
        PortalType.GREENHOUSE,
        PortalType.LEVER,
        PortalType.ASHBY,
    }


def test_get_portal_adapter_returns_correct_type() -> None:
    assert isinstance(get_portal_adapter(PortalType.LINKEDIN), LinkedInEasyApplyAdapter)
    assert isinstance(get_portal_adapter(PortalType.GREENHOUSE), GreenhouseAdapter)
    assert isinstance(get_portal_adapter(PortalType.LEVER), LeverAdapter)
    assert isinstance(get_portal_adapter(PortalType.ASHBY), AshbyAdapter)


def test_get_portal_adapter_raises_for_unregistered_portal() -> None:
    class _FakePortalType:
        value = "not-a-real-portal"

    with pytest.raises(PortalNotSupportedError):
        get_portal_adapter(_FakePortalType())  # type: ignore[arg-type]


@pytest.mark.parametrize(
    (
        "adapter_cls",
        "portal_type",
        "apply_selector",
        "logged_in_selector",
        "submit_selector",
        "success_selector",
    ),
    [
        (
            LinkedInEasyApplyAdapter,
            PortalType.LINKEDIN,
            "button.jobs-apply-button",
            "img.global-nav__me-photo",
            "button[aria-label='Submit application']",
            "h3:has-text('Your application was sent')",
        ),
        (
            GreenhouseAdapter,
            PortalType.GREENHOUSE,
            "a:has-text('Apply for this job')",
            "a:has-text('Sign out')",
            "button#submit_app, input#submit_app",
            "text=Thank you for your interest",
        ),
        (
            LeverAdapter,
            PortalType.LEVER,
            "a.postings-btn",
            "a:has-text('Log out')",
            "button.template-btn-submit",
            "text=Thank you for applying",
        ),
        (
            AshbyAdapter,
            PortalType.ASHBY,
            "button:has-text('Apply for this Job')",
            "button:has-text('Sign out')",
            "button:has-text('Submit Application')",
            "text=Your application has been submitted",
        ),
    ],
)
async def test_adapter_full_lifecycle(
    adapter_cls: type,
    portal_type: PortalType,
    apply_selector: str,
    logged_in_selector: str,
    submit_selector: str,
    success_selector: str,
) -> None:
    adapter = adapter_cls()
    assert adapter.portal_type is portal_type
    assert isinstance(adapter.field_selectors, dict)

    page = FakePage()
    assert await adapter.is_logged_in(page) is False
    assert await adapter.find_apply_button(page) is None

    page.selector_counts[logged_in_selector] = 1
    page.selector_counts[apply_selector] = 1
    assert await adapter.is_logged_in(page) is True
    assert await adapter.find_apply_button(page) == apply_selector

    await adapter.submit(page)
    assert submit_selector in page.clicked

    assert await adapter.detect_success(page) is False
    page.selector_counts[success_selector] = 1
    assert await adapter.detect_success(page) is True

    assert await adapter.extract_application_id(page) is None


def test_field_selectors_returns_a_copy_not_the_internal_dict() -> None:
    adapter = GreenhouseAdapter()
    selectors = adapter.field_selectors
    selectors[FormFieldType.FULL_NAME] = "tampered"
    assert adapter.field_selectors[FormFieldType.FULL_NAME] != "tampered"


async def test_linkedin_submit_clicks_next_step_when_present() -> None:
    adapter = LinkedInEasyApplyAdapter()
    page = FakePage()
    page.selector_counts["button[aria-label='Continue to next step']"] = 1
    await adapter.submit(page)
    assert "button[aria-label='Continue to next step']" in page.clicked
    assert "button[aria-label='Submit application']" in page.clicked
