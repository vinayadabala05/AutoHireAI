"""Validation for the cover letter generation pipeline.

Two independent passes, mirroring `app.resume.validator.ResumeValidator`:

- `validate_inputs` runs *before* generation — catching missing
  personalization data (company name, job title, contact info) or a resume
  document too thin to summarize from.
- `validate_document` runs *after* generation — catching missing required
  sections, malformed Markdown, ATS-compliance issues, and unfilled
  placeholder text (e.g. a stray `[Company Name]`) that would otherwise slip
  through into a "personalized" letter.

Both return a `CoverLetterValidationResult` rather than raising, so callers
(and tests) can inspect every issue found instead of only the first one.
"""

import re

from app.career_profile.models import CareerProfile
from app.cover_letter.models import (
    CoverLetterDocument,
    CoverLetterSection,
    CoverLetterSectionType,
    CoverLetterValidationIssue,
    CoverLetterValidationResult,
)
from app.intelligence.models import ResumeBlueprint
from app.resume.models import ResumeDocument, ResumeSectionType

REQUIRED_SECTIONS = (
    CoverLetterSectionType.GREETING,
    CoverLetterSectionType.BODY,
    CoverLetterSectionType.CLOSING,
    CoverLetterSectionType.SIGNATURE,
)

_PLACEHOLDER_PATTERN = re.compile(r"\[[A-Za-z][A-Za-z '\-]*\]|\{\{[^}]*\}\}")


class CoverLetterValidator:
    def validate_inputs(
        self,
        profile: CareerProfile,
        blueprint: ResumeBlueprint,
        resume_document: ResumeDocument,
        company_name: str,
        job_title: str,
    ) -> CoverLetterValidationResult:
        issues: list[CoverLetterValidationIssue] = []

        if not company_name.strip():
            issues.append(
                CoverLetterValidationIssue(
                    code="missing_company_name",
                    field="company_name",
                    message="A company name is required to personalize the cover letter.",
                    severity="error",
                )
            )

        if not job_title.strip():
            issues.append(
                CoverLetterValidationIssue(
                    code="missing_job_title",
                    field="job_title",
                    message="A job title is required to personalize the cover letter.",
                    severity="error",
                )
            )

        if not profile.personal_info.email:
            issues.append(
                CoverLetterValidationIssue(
                    code="missing_contact_info",
                    field="profile.personal_info.email",
                    message="Career profile has no email address for the signature block.",
                    severity="error",
                )
            )

        has_source_material = any(
            resume_document.section(section_type) is not None
            for section_type in (
                ResumeSectionType.SUMMARY,
                ResumeSectionType.EXPERIENCE,
                ResumeSectionType.PROJECTS,
            )
        )
        if not has_source_material:
            issues.append(
                CoverLetterValidationIssue(
                    code="no_source_material",
                    field="resume_document.sections",
                    message=(
                        "Resume document has no Summary, Experience, or Projects section to "
                        "summarize."
                    ),
                    severity="error",
                )
            )

        if not blueprint.recommended_skills:
            issues.append(
                CoverLetterValidationIssue(
                    code="empty_recommended_skills",
                    field="blueprint.recommended_skills",
                    message="Blueprint has no recommended skills to reference for this role.",
                    severity="warning",
                )
            )

        return CoverLetterValidationResult(is_valid=self._is_valid(issues), issues=issues)

    def validate_document(self, document: CoverLetterDocument) -> CoverLetterValidationResult:
        issues: list[CoverLetterValidationIssue] = []
        present = {section.section_type for section in document.sections}

        for required in REQUIRED_SECTIONS:
            if required not in present:
                issues.append(
                    CoverLetterValidationIssue(
                        code="missing_section",
                        field=required.value,
                        message=f"Required section '{required.value}' is missing.",
                        severity="error",
                    )
                )

        for section in document.sections:
            issues.extend(self._section_issues(section))

        return CoverLetterValidationResult(is_valid=self._is_valid(issues), issues=issues)

    def _section_issues(self, section: CoverLetterSection) -> list[CoverLetterValidationIssue]:
        issues: list[CoverLetterValidationIssue] = []
        content = section.content

        if not content.strip():
            issues.append(
                CoverLetterValidationIssue(
                    code="empty_section",
                    field=section.title,
                    message=f"Section '{section.title}' has no content.",
                    severity="error",
                )
            )
            return issues

        if "\t" in content:
            issues.append(
                CoverLetterValidationIssue(
                    code="tab_character",
                    field=section.title,
                    message="Tab characters break ATS parsing and should be avoided.",
                    severity="warning",
                )
            )

        if "![" in content:
            issues.append(
                CoverLetterValidationIssue(
                    code="image_reference",
                    field=section.title,
                    message="Images are not ATS-parseable and must not appear in a cover letter.",
                    severity="error",
                )
            )

        if content.count("|") > 2:
            issues.append(
                CoverLetterValidationIssue(
                    code="possible_table",
                    field=section.title,
                    message="Content looks like a Markdown table; tables are not ATS-friendly.",
                    severity="warning",
                )
            )

        placeholder_match = _PLACEHOLDER_PATTERN.search(content)
        if placeholder_match:
            issues.append(
                CoverLetterValidationIssue(
                    code="unfilled_placeholder",
                    field=section.title,
                    message=(
                        f"Section '{section.title}' contains an unfilled placeholder: "
                        f"'{placeholder_match.group(0)}'."
                    ),
                    severity="error",
                )
            )

        return issues

    @staticmethod
    def _is_valid(issues: list[CoverLetterValidationIssue]) -> bool:
        return not any(issue.severity == "error" for issue in issues)
