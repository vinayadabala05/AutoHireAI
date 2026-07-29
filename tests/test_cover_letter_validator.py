"""Unit tests for `app.cover_letter.validator.CoverLetterValidator`."""

from datetime import UTC, datetime

from app.cover_letter.models import (
    CoverLetterDocument,
    CoverLetterSection,
    CoverLetterSectionType,
    CoverLetterTemplate,
)
from app.cover_letter.validator import CoverLetterValidator
from app.resume.models import ResumeDocument, ResumeTemplate
from tests.cover_letter_fixtures import (
    sample_blueprint,
    sample_career_profile,
    sample_resume_document,
)


def _empty_resume_document() -> ResumeDocument:
    return ResumeDocument(
        full_name="Jordan Smith",
        contact_line="jordan@example.com",
        template=ResumeTemplate.SOFTWARE_ENGINEER,
        match_score=50.0,
        generated_at=datetime(2026, 1, 1, tzinfo=UTC),
        sections=[],
    )


async def test_validate_inputs_passes_for_healthy_inputs() -> None:
    resume_document = await sample_resume_document()
    result = CoverLetterValidator().validate_inputs(
        sample_career_profile(),
        sample_blueprint(),
        resume_document,
        "Acme Corp",
        "Backend Engineer",
    )
    assert result.is_valid is True
    assert result.errors == []


async def test_validate_inputs_flags_missing_company_name() -> None:
    resume_document = await sample_resume_document()
    result = CoverLetterValidator().validate_inputs(
        sample_career_profile(), sample_blueprint(), resume_document, "  ", "Backend Engineer"
    )
    codes = {issue.code for issue in result.errors}
    assert "missing_company_name" in codes
    assert result.is_valid is False


async def test_validate_inputs_flags_missing_job_title() -> None:
    resume_document = await sample_resume_document()
    result = CoverLetterValidator().validate_inputs(
        sample_career_profile(), sample_blueprint(), resume_document, "Acme Corp", ""
    )
    codes = {issue.code for issue in result.errors}
    assert "missing_job_title" in codes


async def test_validate_inputs_flags_thin_resume_document() -> None:
    result = CoverLetterValidator().validate_inputs(
        sample_career_profile(),
        sample_blueprint(),
        _empty_resume_document(),
        "Acme Corp",
        "Backend Engineer",
    )
    codes = {issue.code for issue in result.errors}
    assert "no_source_material" in codes


async def test_validate_inputs_flags_missing_contact_email() -> None:
    profile = sample_career_profile()
    profile.personal_info.email = ""
    resume_document = await sample_resume_document()
    result = CoverLetterValidator().validate_inputs(
        profile, sample_blueprint(), resume_document, "Acme Corp", "Backend Engineer"
    )
    codes = {issue.code for issue in result.errors}
    assert "missing_contact_info" in codes


def _document(**section_overrides: str) -> CoverLetterDocument:
    base_content = {
        CoverLetterSectionType.GREETING: "Dear Hiring Manager,",
        CoverLetterSectionType.BODY: "I would love to join your team.",
        CoverLetterSectionType.CLOSING: "Sincerely,",
        CoverLetterSectionType.SIGNATURE: "Jordan Smith",
    }
    sections = [
        CoverLetterSection(
            section_type=section_type,
            title=section_type.value,
            content=section_overrides.get(section_type.value, content),
            order=index,
        )
        for index, (section_type, content) in enumerate(base_content.items())
    ]
    return CoverLetterDocument(
        full_name="Jordan Smith",
        contact_line="jordan@example.com",
        date_line="January 01, 2026",
        company_name="Acme Corp",
        job_title="Backend Engineer",
        template=CoverLetterTemplate.SOFTWARE_ENGINEER,
        generated_at=datetime(2026, 1, 1, tzinfo=UTC),
        sections=sections,
    )


def test_validate_document_passes_for_complete_letter() -> None:
    result = CoverLetterValidator().validate_document(_document())
    assert result.is_valid is True


def test_validate_document_flags_missing_required_section() -> None:
    document = _document()
    document.sections = [
        s for s in document.sections if s.section_type != CoverLetterSectionType.CLOSING
    ]
    result = CoverLetterValidator().validate_document(document)
    codes = {issue.code for issue in result.errors}
    assert "missing_section" in codes


def test_validate_document_flags_empty_section() -> None:
    document = _document(Body="   ")
    result = CoverLetterValidator().validate_document(document)
    codes = {issue.code for issue in result.errors}
    assert "empty_section" in codes


def test_validate_document_flags_unfilled_placeholder() -> None:
    document = _document(Body="I am excited to join [Company Name] as a developer.")
    result = CoverLetterValidator().validate_document(document)
    codes = {issue.code for issue in result.errors}
    assert "unfilled_placeholder" in codes


def test_validate_document_flags_image_reference() -> None:
    document = _document(Body="![alt](image.png)")
    result = CoverLetterValidator().validate_document(document)
    codes = {issue.code for issue in result.errors}
    assert "image_reference" in codes


def test_validate_document_warns_on_tab_characters() -> None:
    document = _document(Body="I bring\tstrong skills.")
    result = CoverLetterValidator().validate_document(document)
    codes = {issue.code for issue in result.warnings}
    assert "tab_character" in codes
