"""Structural tests for `app.browser_automation.interfaces`."""

from app.browser_automation.interfaces import PortalAdapterProtocol
from app.browser_automation.portal import (
    AshbyAdapter,
    GreenhouseAdapter,
    LeverAdapter,
    LinkedInEasyApplyAdapter,
)

_PROTOCOL_MEMBERS = (
    "portal_type",
    "field_selectors",
    "is_logged_in",
    "find_apply_button",
    "submit",
    "detect_success",
    "extract_application_id",
)


def _satisfies(instance: object) -> bool:
    return all(hasattr(instance, member) for member in _PROTOCOL_MEMBERS)


def test_linkedin_adapter_satisfies_protocol() -> None:
    assert _satisfies(LinkedInEasyApplyAdapter())


def test_greenhouse_adapter_satisfies_protocol() -> None:
    assert _satisfies(GreenhouseAdapter())


def test_lever_adapter_satisfies_protocol() -> None:
    assert _satisfies(LeverAdapter())


def test_ashby_adapter_satisfies_protocol() -> None:
    assert _satisfies(AshbyAdapter())


def test_protocol_is_importable_and_a_runtime_type() -> None:
    assert isinstance(PortalAdapterProtocol, type)
