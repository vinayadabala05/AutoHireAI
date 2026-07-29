"""Unit tests for `app.resume.formatter.to_markdown` — deterministic Markdown output."""

from datetime import UTC, datetime

from app.resume.formatter import to_markdown
from app.resume.models import ResumeDocument, ResumeSection, ResumeSectionType, ResumeTemplate


def _document() -> ResumeDocument:
    return ResumeDocument(
        full_name="Jordan Smith",
        headline="Backend Engineer",
        contact_line="jordan@example.com | Remote",
        template=ResumeTemplate.BACKEND_ENGINEER,
        job_title="Backend Engineer",
        match_score=0.87,
        generated_at=datetime(2026, 1, 1, tzinfo=UTC),
        sections=[
            ResumeSection(
                section_type=ResumeSectionType.SUMMARY,
                title="Summary",
                content="Experienced backend engineer.",
                order=0,
            ),
            ResumeSection(
                section_type=ResumeSectionType.SKILLS,
                title="Skills",
                content="- **Language:** Python",
                order=1,
            ),
        ],
    )


def test_to_markdown_includes_name_headline_and_contact() -> None:
    markdown = to_markdown(_document())
    lines = markdown.splitlines()
    assert lines[0] == "# Jordan Smith"
    assert "Backend Engineer" in lines
    assert "jordan@example.com | Remote" in lines


def test_to_markdown_renders_sections_in_order() -> None:
    markdown = to_markdown(_document())
    assert markdown.index("## Summary") < markdown.index("## Skills")
    assert "Experienced backend engineer." in markdown
    assert "- **Language:** Python" in markdown


def test_to_markdown_is_deterministic() -> None:
    document = _document()
    assert to_markdown(document) == to_markdown(document)


def test_to_markdown_respects_explicit_order_over_list_order() -> None:
    document = _document()
    document.sections = list(reversed(document.sections))
    markdown = to_markdown(document)
    assert markdown.index("## Summary") < markdown.index("## Skills")
