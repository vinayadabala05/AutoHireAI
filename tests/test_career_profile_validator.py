"""Unit tests for `ProfileValidator` — pure Pydantic data, no database."""

import uuid
from datetime import UTC, datetime

from app.career_profile.models import (
    CareerProfile,
    CertificateProfile,
    EducationProfile,
    ExperienceProfile,
    GithubProfile,
    PersonalInfo,
    ProjectProfile,
    SkillProfile,
)
from app.career_profile.validator import ProfileValidator, _field_fill_ratio

validator = ProfileValidator()


def _minimal_profile(**overrides: object) -> CareerProfile:
    defaults: dict[str, object] = {
        "user_id": uuid.uuid4(),
        "generated_at": datetime.now(UTC),
        "personal_info": PersonalInfo(full_name="Jordan Smith", email="jordan@example.com"),
    }
    defaults.update(overrides)
    return CareerProfile(**defaults)  # type: ignore[arg-type]


def test_sparse_profile_flags_all_missing_warnings_but_stays_valid() -> None:
    profile = _minimal_profile()

    report = validator.validate(profile)

    fields = {issue.field for issue in report.issues}
    assert fields == {
        "personal_info.phone",
        "personal_info.linkedin_url",
        "github_repositories",
        "projects",
        "skills",
        "education",
    }
    assert all(issue.severity == "warning" for issue in report.issues)
    assert report.is_valid is True


def test_missing_email_is_an_error_and_invalidates_the_profile() -> None:
    profile = _minimal_profile(personal_info=PersonalInfo(full_name="Jordan Smith", email=""))

    report = validator.validate(profile)

    email_issues = [i for i in report.issues if i.field == "personal_info.email"]
    assert email_issues and email_issues[0].severity == "error"
    assert report.is_valid is False


def test_fully_filled_profile_has_no_issues() -> None:
    profile = _minimal_profile(
        personal_info=PersonalInfo(
            full_name="Jordan Smith",
            email="jordan@example.com",
            phone="555-0100",
            location="Remote",
            headline="Backend Engineer",
            summary="Summary",
            linkedin_url="https://linkedin.com/in/jordan",
            portfolio_url="https://jordan.dev",
            timezone="UTC",
        ),
        education=[EducationProfile(institution="MIT", degree="BSc")],
        experience=[
            ExperienceProfile(title="Engineer", company_name="Acme", start_date="2022-01-01")
        ],
        projects=[ProjectProfile(name="Project")],
        skills=[SkillProfile(name="Python")],
        certificates=[CertificateProfile(name="AWS Certified", issuing_organization="AWS")],
        github_repositories=[
            GithubProfile(name="repo", full_name="a/repo", url="https://github.com/a/repo")
        ],
    )

    report = validator.validate(profile)

    assert report.issues == []
    assert report.is_valid is True


def test_completeness_scores_reflect_field_fill_ratio() -> None:
    # Personal info: 7 of 9 fields filled (missing phone + timezone).
    profile = _minimal_profile(
        personal_info=PersonalInfo(
            full_name="Jordan Smith",
            email="jordan@example.com",
            location="Remote",
            headline="Backend Engineer",
            summary="Summary",
            linkedin_url="https://linkedin.com/in/jordan",
            portfolio_url="https://jordan.dev",
        ),
        skills=[SkillProfile(name="Python", years_experience=5), SkillProfile(name="Go")],
    )

    report = validator.validate(profile)
    sections_by_name = {s.name: s for s in report.completeness.sections}

    assert sections_by_name["Personal Information"].score == round(7 / 9 * 100, 1)
    # One skill has years_experience filled (1/2 fields), the other has neither (0/2) -> avg 25%.
    assert sections_by_name["Skills"].score == 25.0
    assert sections_by_name["Education"].score == 0.0
    assert sections_by_name["Education"].item_count == 0


def test_empty_field_list_scores_full_marks() -> None:
    # A section with no meaningful sub-fields to check (defensive edge case
    # for `_field_fill_ratio`) should never be penalized.
    assert _field_fill_ratio(object(), []) == 100.0
