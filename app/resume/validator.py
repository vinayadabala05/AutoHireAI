"""Validation for the resume generation pipeline.

Two independent passes are exposed, because they catch different classes of
problems at different pipeline stages:

- `validate_inputs` runs *before* generation, on the raw `ResumeBlueprint` +
  `CareerProfile` — catching problems (empty skills, duplicate projects)
  that would otherwise silently produce a thin or confusing resume.
- `validate_document` runs *after* generation, on the assembled
  `ResumeDocument` — catching missing required sections, malformed
  Markdown, and ATS-compliance issues (tables, images, non-standard bullet
  characters) that an ATS parser would choke on.

Both return a `ResumeValidationResult` rather than raising, so callers (and
tests) can inspect every issue found instead of only the first one.
"""

from app.career_profile.models import CareerProfile
from app.intelligence.models import ResumeBlueprint
from app.resume.models import (
    ResumeDocument,
    ResumeSection,
    ResumeSectionType,
    ResumeValidationIssue,
    ResumeValidationResult,
)

REQUIRED_SECTIONS = (
    ResumeSectionType.SUMMARY,
    ResumeSectionType.EXPERIENCE,
    ResumeSectionType.SKILLS,
    ResumeSectionType.EDUCATION,
)

_NON_STANDARD_BULLETS = ("•", "◦", "▪", "●", "*")


class ResumeValidator:
    def validate_inputs(
        self, blueprint: ResumeBlueprint, profile: CareerProfile
    ) -> ResumeValidationResult:
        issues: list[ResumeValidationIssue] = []

        if not profile.skills:
            issues.append(
                ResumeValidationIssue(
                    code="empty_skills",
                    field="profile.skills",
                    message="Career profile has no skills; the Skills section will be empty.",
                    severity="error",
                )
            )

        if not blueprint.recommended_skills:
            issues.append(
                ResumeValidationIssue(
                    code="empty_recommended_skills",
                    field="blueprint.recommended_skills",
                    message="Blueprint has no recommended skills to prioritize in generation.",
                    severity="warning",
                )
            )

        if not profile.experience and not profile.projects:
            issues.append(
                ResumeValidationIssue(
                    code="no_track_record",
                    field="profile",
                    message="Career profile has neither experience nor projects.",
                    severity="error",
                )
            )

        issues.extend(self._duplicate_project_issues(profile))

        return ResumeValidationResult(is_valid=self._is_valid(issues), issues=issues)

    def validate_document(self, document: ResumeDocument) -> ResumeValidationResult:
        issues: list[ResumeValidationIssue] = []
        present = {section.section_type for section in document.sections}

        for required in REQUIRED_SECTIONS:
            if required not in present:
                issues.append(
                    ResumeValidationIssue(
                        code="missing_section",
                        field=required.value,
                        message=f"Required section '{required.value}' is missing.",
                        severity="error",
                    )
                )

        for section in document.sections:
            issues.extend(self._section_issues(section))

        return ResumeValidationResult(is_valid=self._is_valid(issues), issues=issues)

    def _duplicate_project_issues(self, profile: CareerProfile) -> list[ResumeValidationIssue]:
        seen: set[str] = set()
        duplicates: set[str] = set()
        for project in profile.projects:
            key = project.name.strip().lower()
            if key in seen:
                duplicates.add(key)
            seen.add(key)
        return [
            ResumeValidationIssue(
                code="duplicate_project",
                field=f"projects.{name}",
                message=f"Project '{name}' appears more than once in the career profile.",
                severity="error",
            )
            for name in sorted(duplicates)
        ]

    def _section_issues(self, section: ResumeSection) -> list[ResumeValidationIssue]:
        issues: list[ResumeValidationIssue] = []
        content = section.content

        if not content.strip():
            issues.append(
                ResumeValidationIssue(
                    code="empty_section",
                    field=section.title,
                    message=f"Section '{section.title}' has no content.",
                    severity="error",
                )
            )
            return issues

        if "\t" in content:
            issues.append(
                ResumeValidationIssue(
                    code="tab_character",
                    field=section.title,
                    message="Tab characters break ATS parsing and should be avoided.",
                    severity="warning",
                )
            )

        if "\n\n\n" in content:
            issues.append(
                ResumeValidationIssue(
                    code="excess_blank_lines",
                    field=section.title,
                    message="Section contains three or more consecutive blank lines.",
                    severity="warning",
                )
            )

        if "![" in content:
            issues.append(
                ResumeValidationIssue(
                    code="image_reference",
                    field=section.title,
                    message="Images are not ATS-parseable and must not appear in a resume.",
                    severity="error",
                )
            )

        if content.count("|") > 2:
            issues.append(
                ResumeValidationIssue(
                    code="possible_table",
                    field=section.title,
                    message="Content looks like a Markdown table; tables are not ATS-friendly.",
                    severity="warning",
                )
            )

        for line in content.splitlines():
            stripped = line.strip()
            if any(
                stripped.startswith(bullet) for bullet in _NON_STANDARD_BULLETS
            ) and not stripped.startswith("- "):
                issues.append(
                    ResumeValidationIssue(
                        code="non_standard_bullet",
                        field=section.title,
                        message=(
                            "Use a plain '-' for bullet points; other bullet glyphs may not "
                            "parse in ATS."
                        ),
                        severity="warning",
                    )
                )
                break

        return issues

    @staticmethod
    def _is_valid(issues: list[ResumeValidationIssue]) -> bool:
        return not any(issue.severity == "error" for issue in issues)
