"""Unit tests for `app.resume.renderer` — Markdown -> HTML conversion and file export."""

from datetime import UTC, datetime
from pathlib import Path

from app.resume.formatter import to_markdown
from app.resume.models import ResumeDocument, ResumeSection, ResumeSectionType, ResumeTemplate
from app.resume.renderer import export_html_file, export_markdown_file, markdown_to_html, to_html


def _document() -> ResumeDocument:
    return ResumeDocument(
        full_name="Jordan Smith",
        contact_line="jordan@example.com",
        template=ResumeTemplate.SOFTWARE_ENGINEER,
        match_score=0.5,
        generated_at=datetime(2026, 1, 1, tzinfo=UTC),
        sections=[
            ResumeSection(
                section_type=ResumeSectionType.SUMMARY,
                title="Summary",
                content="Loves **Python** and testing.",
                order=0,
            ),
            ResumeSection(
                section_type=ResumeSectionType.SKILLS,
                title="Skills",
                content="- Python\n- FastAPI",
                order=1,
            ),
        ],
    )


def test_markdown_to_html_renders_headings_bold_and_lists() -> None:
    html = markdown_to_html("# Name\n\n## Summary\nLoves **Python**.\n\n- Item one\n- Item two\n")
    assert "<h1>Name</h1>" in html
    assert "<h2>Summary</h2>" in html
    assert "<strong>Python</strong>" in html
    assert "<ul>" in html and "<li>Item one</li>" in html and "<li>Item two</li>" in html


def test_markdown_to_html_escapes_html_special_characters() -> None:
    html = markdown_to_html("Use <script>alert(1)</script> & such")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "&amp;" in html


def test_to_html_wraps_body_with_document_title() -> None:
    document = _document()
    html = to_html(document, markdown=to_markdown(document))
    assert "<title>Jordan Smith</title>" in html
    assert "<h1>Jordan Smith</h1>" in html


def test_export_markdown_file_writes_to_disk(tmp_path: Path) -> None:
    path = export_markdown_file("# Hello\n", tmp_path / "out" / "resume.md")
    assert path.read_text(encoding="utf-8") == "# Hello\n"


def test_export_html_file_writes_to_disk(tmp_path: Path) -> None:
    document = _document()
    markdown = to_markdown(document)
    path = export_html_file(document, markdown, tmp_path / "out" / "resume.html")
    assert "<h1>Jordan Smith</h1>" in path.read_text(encoding="utf-8")
