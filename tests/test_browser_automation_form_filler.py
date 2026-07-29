"""Unit tests for `app.browser_automation.form_filler.FormFiller`."""

import pytest

from app.browser_automation.exceptions import FormFillError
from app.browser_automation.form_filler import FormFiller
from app.browser_automation.models import FormFieldType, FormFillOptions
from app.browser_automation.portal import GreenhouseAdapter
from tests.browser_automation_fixtures import FakePage
from tests.resume_fixtures import sample_career_profile


def _present(page: FakePage, selectors: dict) -> None:
    for selector in selectors.values():
        page.selector_counts[selector] = 1


async def test_fill_populates_known_text_fields_from_profile() -> None:
    adapter = GreenhouseAdapter()
    page = FakePage()
    _present(page, adapter.field_selectors)

    result = await FormFiller().fill(page, adapter, sample_career_profile())

    assert page.filled_values["#job_application_first_name"] == "Jordan Smith"
    assert page.filled_values["#job_application_email"] == "jordan.smith@example.com"
    assert FormFieldType.FULL_NAME in result.filled_fields
    assert FormFieldType.EMAIL in result.filled_fields


async def test_fill_reports_unsupported_when_no_value_available() -> None:
    adapter = GreenhouseAdapter()
    page = FakePage()
    _present(page, adapter.field_selectors)

    result = await FormFiller().fill(page, adapter, sample_career_profile())

    unsupported_fields = {question.label for question in result.unsupported_questions}
    assert FormFieldType.WORK_AUTHORIZATION.value in unsupported_fields
    assert FormFieldType.SALARY_EXPECTATION.value in unsupported_fields


async def test_fill_uses_options_for_configurable_fields() -> None:
    adapter = GreenhouseAdapter()
    page = FakePage()
    _present(page, adapter.field_selectors)
    options = FormFillOptions(
        work_authorization="US Citizen",
        visa_sponsorship_required=False,
        notice_period="2 weeks",
        salary_expectation="$150,000",
    )

    result = await FormFiller().fill(page, adapter, sample_career_profile(), options)

    assert page.filled_values["select[id*='work_authorization']"] == "US Citizen"
    assert page.filled_values["input[id*='notice_period']"] == "2 weeks"
    assert page.filled_values["input[id*='salary_expectation']"] == "$150,000"
    assert result.is_complete is True


async def test_fill_skips_fields_absent_from_the_page() -> None:
    adapter = GreenhouseAdapter()
    page = FakePage()  # no selectors present at all

    result = await FormFiller().fill(page, adapter, sample_career_profile())

    assert result.filled_fields == []
    assert result.unsupported_questions == []


async def test_fill_dispatches_to_select_option_for_select_elements() -> None:
    adapter = GreenhouseAdapter()
    page = FakePage()
    selector = adapter.field_selectors[FormFieldType.WORK_AUTHORIZATION]
    page.selector_counts[selector] = 1
    page.tag_names[selector] = "select"

    await FormFiller().fill(
        page, adapter, sample_career_profile(), FormFillOptions(work_authorization="US Citizen")
    )
    assert page.filled_values[selector] == "US Citizen"


async def test_fill_dispatches_to_checkbox_for_yes_no_values() -> None:
    adapter = GreenhouseAdapter()
    page = FakePage()
    selector = adapter.field_selectors[FormFieldType.VISA_SPONSORSHIP]
    page.selector_counts[selector] = 1
    page.input_types[selector] = "checkbox"

    await FormFiller().fill(
        page, adapter, sample_career_profile(), FormFillOptions(visa_sponsorship_required=True)
    )
    assert selector in page.checked_selectors

    page.checked_selectors.clear()
    await FormFiller().fill(
        page, adapter, sample_career_profile(), FormFillOptions(visa_sponsorship_required=False)
    )
    assert selector not in page.checked_selectors


async def test_fill_dispatches_to_radio_for_radio_inputs() -> None:
    adapter = GreenhouseAdapter()
    page = FakePage()
    selector = adapter.field_selectors[FormFieldType.NOTICE_PERIOD]
    page.selector_counts[selector] = 1
    page.input_types[selector] = "radio"

    await FormFiller().fill(
        page, adapter, sample_career_profile(), FormFillOptions(notice_period="Immediately")
    )
    assert selector in page.checked_selectors


async def test_fill_wraps_unexpected_failure_as_form_fill_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = GreenhouseAdapter()
    page = FakePage()
    selector = adapter.field_selectors[FormFieldType.FULL_NAME]
    page.selector_counts[selector] = 1

    async def _boom(self: object, script: str) -> None:
        raise RuntimeError("evaluate failed")

    from tests.browser_automation_fixtures import FakeLocator

    monkeypatch.setattr(FakeLocator, "evaluate", _boom)

    with pytest.raises(FormFillError):
        await FormFiller().fill(page, adapter, sample_career_profile())


async def test_fill_ignores_upload_field_types() -> None:
    from app.browser_automation.models import PortalType
    from app.browser_automation.portal import PortalAdapter

    class _UploadOnlyAdapter(PortalAdapter):
        @property
        def portal_type(self) -> PortalType:
            return PortalType.GREENHOUSE

        @property
        def field_selectors(self) -> dict:
            return {FormFieldType.RESUME_UPLOAD: "input[type=file]"}

        async def is_logged_in(self, page: FakePage) -> bool:
            return True

        async def find_apply_button(self, page: FakePage) -> str | None:
            return None

        async def submit(self, page: FakePage) -> None:
            return None

        async def detect_success(self, page: FakePage) -> bool:
            return True

    page = FakePage()
    page.selector_counts["input[type=file]"] = 1
    result = await FormFiller().fill(page, _UploadOnlyAdapter(), sample_career_profile())
    assert result.filled_fields == []
    assert result.unsupported_questions == []
