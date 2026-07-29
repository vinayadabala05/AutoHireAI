"""Unit tests for `app.resume.templates` — section-order resolution."""

from app.resume.models import ResumeSectionType, ResumeTemplate
from app.resume.templates import all_templates, get_template_spec, resolve_section_order


def test_all_four_required_templates_are_registered() -> None:
    assert set(all_templates()) == {
        ResumeTemplate.SOFTWARE_ENGINEER,
        ResumeTemplate.AI_ENGINEER,
        ResumeTemplate.BACKEND_ENGINEER,
        ResumeTemplate.RESEARCH_ENGINEER,
    }


def test_get_template_spec_returns_display_name() -> None:
    spec = get_template_spec(ResumeTemplate.AI_ENGINEER)
    assert spec.display_name == "AI Engineer"
    assert ResumeSectionType.SKILLS in spec.emphasize_sections


def test_resolve_section_order_prefers_blueprint_order() -> None:
    order = resolve_section_order(
        ResumeTemplate.SOFTWARE_ENGINEER, ["Projects", "Summary", "Skills"]
    )
    assert order == [
        ResumeSectionType.PROJECTS,
        ResumeSectionType.SUMMARY,
        ResumeSectionType.SKILLS,
    ]


def test_resolve_section_order_drops_unknown_section_names() -> None:
    order = resolve_section_order(ResumeTemplate.SOFTWARE_ENGINEER, ["Summary", "Hobbies"])
    assert order == [ResumeSectionType.SUMMARY]


def test_resolve_section_order_falls_back_to_template_default_when_blueprint_empty() -> None:
    order = resolve_section_order(ResumeTemplate.RESEARCH_ENGINEER, [])
    assert order == list(get_template_spec(ResumeTemplate.RESEARCH_ENGINEER).default_section_order)


def test_resolve_section_order_falls_back_when_all_names_unknown() -> None:
    order = resolve_section_order(ResumeTemplate.BACKEND_ENGINEER, ["Hobbies", "References"])
    assert order == list(get_template_spec(ResumeTemplate.BACKEND_ENGINEER).default_section_order)
