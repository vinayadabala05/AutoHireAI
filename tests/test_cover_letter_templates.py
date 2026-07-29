"""Unit tests for `app.cover_letter.templates`."""

from app.cover_letter.models import CoverLetterTemplate
from app.cover_letter.templates import all_templates, get_template_spec
from app.resume.models import ResumeSectionType


def test_all_four_required_templates_are_registered() -> None:
    assert set(all_templates()) == {
        CoverLetterTemplate.SOFTWARE_ENGINEER,
        CoverLetterTemplate.AI_ENGINEER,
        CoverLetterTemplate.BACKEND_ENGINEER,
        CoverLetterTemplate.RESEARCH_ENGINEER,
    }


def test_get_template_spec_returns_display_name_and_closing() -> None:
    spec = get_template_spec(CoverLetterTemplate.RESEARCH_ENGINEER)
    assert spec.display_name == "Research Engineer"
    assert spec.closing_phrase == "Respectfully,"
    assert ResumeSectionType.PROJECTS in spec.emphasize_resume_sections


def test_ai_engineer_template_emphasizes_projects_over_experience() -> None:
    spec = get_template_spec(CoverLetterTemplate.AI_ENGINEER)
    assert spec.emphasize_resume_sections.index(
        ResumeSectionType.PROJECTS
    ) < spec.emphasize_resume_sections.index(ResumeSectionType.EXPERIENCE)


def test_every_template_has_a_non_empty_closing_phrase() -> None:
    for template in all_templates():
        assert get_template_spec(template).closing_phrase.strip()
