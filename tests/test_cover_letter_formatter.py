"""Unit tests for `app.cover_letter.formatter.to_markdown` — deterministic Markdown output."""

from datetime import UTC, datetime

from app.cover_letter.formatter import to_markdown
from app.cover_letter.models import (
    CoverLetterDocument,
    CoverLetterSection,
    CoverLetterSectionType,
    CoverLetterTemplate,
)


def _document() -> CoverLetterDocument:
    return CoverLetterDocument(
        full_name="Jordan Smith",
        contact_line="jordan@example.com | Remote",
        date_line="January 01, 2026",
        company_name="Acme Corp",
        hiring_manager="Alex Lee",
        job_title="Backend Engineer",
        template=CoverLetterTemplate.BACKEND_ENGINEER,
        generated_at=datetime(2026, 1, 1, tzinfo=UTC),
        sections=[
            CoverLetterSection(
                section_type=CoverLetterSectionType.GREETING,
                title="Greeting",
                content="Dear Alex Lee,",
                order=0,
            ),
            CoverLetterSection(
                section_type=CoverLetterSectionType.BODY,
                title="Body",
                content="I am excited to apply.",
                order=1,
            ),
            CoverLetterSection(
                section_type=CoverLetterSectionType.CLOSING,
                title="Closing",
                content="Sincerely,",
                order=2,
            ),
            CoverLetterSection(
                section_type=CoverLetterSectionType.SIGNATURE,
                title="Signature",
                content="Jordan Smith",
                order=3,
            ),
        ],
    )


def test_to_markdown_includes_header_block() -> None:
    markdown = to_markdown(_document())
    lines = markdown.splitlines()
    assert lines[0] == "Jordan Smith"
    assert "jordan@example.com | Remote" in lines
    assert "Acme Corp" in lines
    assert "Re: Backend Engineer" in lines


def test_to_markdown_renders_sections_in_order() -> None:
    markdown = to_markdown(_document())
    assert (
        markdown.index("Dear Alex Lee,")
        < markdown.index("I am excited to apply.")
        < markdown.index("Sincerely,")
        < markdown.index("Jordan Smith", markdown.index("Sincerely,"))
    )


def test_to_markdown_is_deterministic() -> None:
    document = _document()
    assert to_markdown(document) == to_markdown(document)


def test_to_markdown_ends_with_signature() -> None:
    markdown = to_markdown(_document())
    assert markdown.strip().splitlines()[-1] == "Jordan Smith"
