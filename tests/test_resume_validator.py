"""Unit tests for `app.resume.validator.ResumeValidator`."""

from datetime import UTC, datetime

from app.intelligence.models import ResumeBlueprint
from app.resume.models import ResumeDocument, ResumeSection, ResumeSectionType, ResumeTemplate
from app.resume.validator import ResumeValidator
from tests.resume_fixtures import (
    profile_with_duplicate_projects,
    profile_with_no_skills,
    sample_career_profile,
)


def _blueprint(**overrides: object) -> ResumeBlueprint:
    defaults: dict[str, object] = {
        "match_score": 80.0,
        "recommended_projects": [],
        "recommended_skills": ["Python"],
        "missing_skills": [],
        "resume_sections": ["Summary", "Experience", "Skills", "Education"],
        "reasoning": ["reason"],
    }
    defaults.update(overrides)
    return ResumeBlueprint(**defaults)


def test_validate_inputs_passes_for_healthy_profile() -> None:
    result = ResumeValidator().validate_inputs(_blueprint(), sample_career_profile())
    assert result.is_valid is True
    assert result.errors == []


def test_validate_inputs_flags_empty_skills() -> None:
    result = ResumeValidator().validate_inputs(_blueprint(), profile_with_no_skills())
    codes = {issue.code for issue in result.errors}
    assert "empty_skills" in codes
    assert result.is_valid is False


def test_validate_inputs_flags_duplicate_projects() -> None:
    result = ResumeValidator().validate_inputs(_blueprint(), profile_with_duplicate_projects())
    codes = {issue.code for issue in result.errors}
    assert "duplicate_project" in codes
    assert result.is_valid is False


def test_validate_inputs_warns_on_empty_recommended_skills() -> None:
    result = ResumeValidator().validate_inputs(
        _blueprint(recommended_skills=[]), sample_career_profile()
    )
    codes = {issue.code for issue in result.warnings}
    assert "empty_recommended_skills" in codes
    assert result.is_valid is True


def _document(**section_overrides: str) -> ResumeDocument:
    base_content = {
        ResumeSectionType.SUMMARY: "A summary.",
        ResumeSectionType.EXPERIENCE: "- Did things.",
        ResumeSectionType.SKILLS: "- Python",
        ResumeSectionType.EDUCATION: "### B.S.",
    }
    sections = [
        ResumeSection(
            section_type=section_type,
            title=section_type.value,
            content=section_overrides.get(section_type.value, content),
            order=index,
        )
        for index, (section_type, content) in enumerate(base_content.items())
    ]
    return ResumeDocument(
        full_name="Jordan Smith",
        contact_line="jordan@example.com",
        template=ResumeTemplate.SOFTWARE_ENGINEER,
        match_score=0.5,
        generated_at=datetime(2026, 1, 1, tzinfo=UTC),
        sections=sections,
    )


def test_validate_document_passes_for_complete_document() -> None:
    result = ResumeValidator().validate_document(_document())
    assert result.is_valid is True


def test_validate_document_flags_missing_required_section() -> None:
    document = _document()
    document.sections = [s for s in document.sections if s.section_type != ResumeSectionType.SKILLS]
    result = ResumeValidator().validate_document(document)
    codes = {issue.code for issue in result.errors}
    assert "missing_section" in codes


def test_validate_document_flags_empty_section_content() -> None:
    document = _document(Summary="   ")
    result = ResumeValidator().validate_document(document)
    codes = {issue.code for issue in result.errors}
    assert "empty_section" in codes


def test_validate_document_flags_image_reference() -> None:
    document = _document(Summary="![alt](image.png)")
    result = ResumeValidator().validate_document(document)
    codes = {issue.code for issue in result.errors}
    assert "image_reference" in codes


def test_validate_document_warns_on_tab_characters() -> None:
    document = _document(Summary="A summary\twith a tab.")
    result = ResumeValidator().validate_document(document)
    codes = {issue.code for issue in result.warnings}
    assert "tab_character" in codes


def test_validate_document_warns_on_non_standard_bullet() -> None:
    document = _document(Experience="• Did things with a fancy bullet.")
    result = ResumeValidator().validate_document(document)
    codes = {issue.code for issue in result.warnings}
    assert "non_standard_bullet" in codes
