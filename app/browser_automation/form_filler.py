"""Form filling: populates known application fields from `CareerProfile`
(reused as-is, Sprint 3.5) plus `FormFillOptions` (per-application facts
`CareerProfile` doesn't carry), and returns any question it can't
confidently answer instead of guessing.
"""

from playwright.async_api import Page

from app.browser_automation.exceptions import FormFillError
from app.browser_automation.interfaces import PortalAdapterProtocol
from app.browser_automation.models import (
    FormFieldType,
    FormFillOptions,
    FormFillResult,
    QuestionInputType,
    UnsupportedQuestion,
)
from app.career_profile.models import CareerProfile

_UPLOAD_FIELDS = frozenset({FormFieldType.RESUME_UPLOAD, FormFieldType.COVER_LETTER_UPLOAD})


class FormFiller:
    async def fill(
        self,
        page: Page,
        adapter: PortalAdapterProtocol,
        profile: CareerProfile,
        options: FormFillOptions | None = None,
    ) -> FormFillResult:
        options = options or FormFillOptions()
        values = self._field_values(profile, options)

        filled: list[FormFieldType] = []
        unsupported: list[UnsupportedQuestion] = []

        for field_type, selector in adapter.field_selectors.items():
            if field_type in _UPLOAD_FIELDS:
                continue  # handled by uploader.py, not text/dropdown/checkbox filling

            locator = page.locator(selector)
            if await locator.count() == 0:
                continue  # field not present on this portal's form for this job posting

            value = values.get(field_type)
            if value is None:
                unsupported.append(
                    UnsupportedQuestion(
                        label=field_type.value,
                        input_type=QuestionInputType.TEXT,
                        selector=selector,
                        reason=f"No value available for '{field_type.value}'.",
                    )
                )
                continue

            try:
                await self._fill_field(page, selector, value)
                filled.append(field_type)
            except Exception as exc:
                raise FormFillError(f"Failed to fill '{field_type.value}': {exc}") from exc

        return FormFillResult(filled_fields=filled, unsupported_questions=unsupported)

    async def _fill_field(self, page: Page, selector: str, value: str) -> None:
        locator = page.locator(selector)
        tag_name = await locator.evaluate("el => el.tagName.toLowerCase()")
        input_type = await locator.evaluate("el => el.type || ''")

        if tag_name == "select":
            await locator.select_option(label=value)
        elif input_type == "checkbox":
            if value.strip().lower() in {"yes", "true", "1"}:
                await locator.check()
            else:
                await locator.uncheck()
        elif input_type == "radio":
            await locator.check()
        else:
            await locator.fill(value)

    def _field_values(
        self, profile: CareerProfile, options: FormFillOptions
    ) -> dict[FormFieldType, str | None]:
        info = profile.personal_info
        education_summary = (
            "; ".join(
                f"{education.degree} in {education.field_of_study}, {education.institution}"
                if education.field_of_study
                else f"{education.degree}, {education.institution}"
                for education in profile.education
            )
            or None
        )
        experience_summary = (
            "; ".join(f"{exp.title} at {exp.company_name}" for exp in profile.experience) or None
        )
        skills_summary = ", ".join(skill.name for skill in profile.skills) or None
        visa_sponsorship = (
            None
            if options.visa_sponsorship_required is None
            else ("Yes" if options.visa_sponsorship_required else "No")
        )

        return {
            FormFieldType.FULL_NAME: info.full_name,
            FormFieldType.EMAIL: info.email,
            FormFieldType.PHONE: info.phone,
            FormFieldType.ADDRESS: info.location,
            FormFieldType.EDUCATION: education_summary,
            FormFieldType.EXPERIENCE: experience_summary,
            FormFieldType.SKILLS: skills_summary,
            FormFieldType.WORK_AUTHORIZATION: options.work_authorization,
            FormFieldType.VISA_SPONSORSHIP: visa_sponsorship,
            FormFieldType.NOTICE_PERIOD: options.notice_period,
            FormFieldType.SALARY_EXPECTATION: options.salary_expectation,
        }
