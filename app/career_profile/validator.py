"""Validates a `CareerProfile` for completeness and computes a data quality report.

Nothing here is a hard failure in the traditional sense — a sparse profile
is still a valid `CareerProfile`, just an incomplete one. `is_valid` only
goes `False` for a genuinely broken required field (an empty name/email);
everything else surfaces as a `"warning"` the consumer (a future dashboard,
an AI prompt builder) can act on.
"""

from typing import Any

from app.career_profile.models import (
    CareerProfile,
    CompletenessReport,
    SectionScore,
    ValidationIssue,
    ValidationReport,
)

# Field lists used to score how "filled in" each section's entries are.
# See docs/career_profile.md for the rationale behind each list.
_PERSONAL_INFO_FIELDS = [
    "full_name",
    "email",
    "phone",
    "location",
    "headline",
    "summary",
    "linkedin_url",
    "portfolio_url",
    "timezone",
]
_EDUCATION_FIELDS = ["field_of_study", "start_date", "end_date", "gpa", "description"]
_EXPERIENCE_FIELDS = ["location", "description", "achievements", "technologies"]
_PROJECT_FIELDS = ["description", "technologies", "achievements", "github_url", "demo_url"]
_SKILL_FIELDS = ["years_experience", "confidence_level"]
_CERTIFICATE_FIELDS = ["issue_date", "expiration_date", "credential_id", "credential_url"]
_GITHUB_FIELDS = ["description", "primary_language", "topics"]

# Overall score weighting — Personal Info and Projects count most heavily
# since they're what every downstream AI feature reads first; Certificates
# count least since most roles don't require any.
_SECTION_WEIGHTS = {
    "Personal Information": 0.20,
    "Education": 0.15,
    "Experience": 0.15,
    "Projects": 0.20,
    "Skills": 0.15,
    "Certificates": 0.05,
    "GitHub": 0.10,
}


def _is_filled(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list | tuple | set):
        return len(value) > 0
    return True


def _field_fill_ratio(instance: Any, fields: list[str]) -> float:
    if not fields:
        return 100.0
    filled = sum(1 for field_name in fields if _is_filled(getattr(instance, field_name)))
    return filled / len(fields) * 100


def _section_score(name: str, items: list[Any], fields: list[str]) -> SectionScore:
    if not items:
        return SectionScore(name=name, score=0.0, item_count=0)
    ratios = [_field_fill_ratio(item, fields) for item in items]
    return SectionScore(name=name, score=round(sum(ratios) / len(ratios), 1), item_count=len(items))


class ProfileValidator:
    def validate(self, profile: CareerProfile) -> ValidationReport:
        issues = self._collect_issues(profile)
        completeness = self._score_completeness(profile)
        has_errors = any(issue.severity == "error" for issue in issues)
        return ValidationReport(is_valid=not has_errors, issues=issues, completeness=completeness)

    def _collect_issues(self, profile: CareerProfile) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        info = profile.personal_info

        if not _is_filled(info.email):
            issues.append(
                ValidationIssue(
                    field="personal_info.email", message="Email is missing.", severity="error"
                )
            )
        if not _is_filled(info.phone):
            issues.append(
                ValidationIssue(
                    field="personal_info.phone",
                    message="Phone number is missing.",
                    severity="warning",
                )
            )
        if not _is_filled(info.linkedin_url):
            issues.append(
                ValidationIssue(
                    field="personal_info.linkedin_url",
                    message="LinkedIn URL is missing.",
                    severity="warning",
                )
            )
        if not profile.github_repositories:
            issues.append(
                ValidationIssue(
                    field="github_repositories",
                    message="No GitHub repositories linked to this profile.",
                    severity="warning",
                )
            )
        if not profile.projects:
            issues.append(
                ValidationIssue(
                    field="projects", message="No projects on this profile.", severity="warning"
                )
            )
        if not profile.skills:
            issues.append(
                ValidationIssue(
                    field="skills", message="No skills on this profile.", severity="warning"
                )
            )
        if not profile.education:
            issues.append(
                ValidationIssue(
                    field="education",
                    message="No education history on this profile.",
                    severity="warning",
                )
            )
        return issues

    def _score_completeness(self, profile: CareerProfile) -> CompletenessReport:
        sections = [
            SectionScore(
                name="Personal Information",
                score=round(_field_fill_ratio(profile.personal_info, _PERSONAL_INFO_FIELDS), 1),
                item_count=1,
            ),
            _section_score("Education", profile.education, _EDUCATION_FIELDS),
            _section_score("Experience", profile.experience, _EXPERIENCE_FIELDS),
            _section_score("Projects", profile.projects, _PROJECT_FIELDS),
            _section_score("Skills", profile.skills, _SKILL_FIELDS),
            _section_score("Certificates", profile.certificates, _CERTIFICATE_FIELDS),
            _section_score("GitHub", profile.github_repositories, _GITHUB_FIELDS),
        ]
        overall = sum(section.score * _SECTION_WEIGHTS[section.name] for section in sections)
        return CompletenessReport(sections=sections, overall_score=round(overall, 1))
