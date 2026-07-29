"""Unit tests for `app.cover_letter.renderer` — Markdown -> HTML conversion and file export."""

from datetime import UTC, datetime
from pathlib import Path

from app.cover_letter.formatter import to_markdown
from app.cover_letter.models import (
    CoverLetterDocument,
    CoverLetterSection,
    CoverLetterSectionType,
    CoverLetterTemplate,
)
from app.cover_letter.renderer import (
    export_html_file,
    export_markdown_file,
    markdown_to_html,
    to_html,
)


def _document() -> CoverLetterDocument:
    return CoverLetterDocument(
        full_name="Jordan Smith",
        contact_line="jordan@example.com",
        date_line="January 01, 2026",
        company_name="Acme Corp",
        job_title="Backend Engineer",
        template=CoverLetterTemplate.SOFTWARE_ENGINEER,
        generated_at=datetime(2026, 1, 1, tzinfo=UTC),
        sections=[
            CoverLetterSection(
                section_type=CoverLetterSectionType.GREETING,
                title="Greeting",
                content="Dear Hiring Manager,",
                order=0,
            ),
            CoverLetterSection(
                section_type=CoverLetterSectionType.BODY,
                title="Body",
                content="I bring **strong** Python skills.",
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


def test_markdown_to_html_wraps_paragraphs_and_renders_bold() -> None:
    html = markdown_to_html("Dear Hiring Manager,\n\nI bring **strong** skills.\n\nSincerely,")
    assert html.count("<p>") == 3
    assert "<strong>strong</strong>" in html


def test_markdown_to_html_escapes_html_special_characters() -> None:
    html = markdown_to_html("Use <script>alert(1)</script> & such")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_to_html_wraps_body_with_title() -> None:
    document = _document()
    html = to_html(document, markdown=to_markdown(document))
    assert "Jordan Smith" in html
    assert "Acme Corp" in html
    assert "<p>Dear Hiring Manager,</p>" in html


def test_export_markdown_file_writes_to_disk(tmp_path: Path) -> None:
    path = export_markdown_file("Jordan Smith\n", tmp_path / "out" / "letter.md")
    assert path.read_text(encoding="utf-8") == "Jordan Smith\n"


def test_export_html_file_writes_to_disk(tmp_path: Path) -> None:
    document = _document()
    markdown = to_markdown(document)
    path = export_html_file(document, markdown, tmp_path / "out" / "letter.html")
    assert "Dear Hiring Manager" in path.read_text(encoding="utf-8")
