"""Renders a `ResumeDocument` to ATS-friendly Markdown.

ATS-friendly means: a single H1 for the name, H2 per section in document
order, no tables, no images, no multi-column layout, and plain `-` bullets —
the format most Applicant Tracking Systems parse reliably. This module is a
pure function of `ResumeDocument`; given the same document it always
produces the same string, which is what makes resume generation testable
without mocking anything beyond the LLM calls that built the document.
"""

from app.resume.models import ResumeDocument


def to_markdown(document: ResumeDocument) -> str:
    lines: list[str] = [f"# {document.full_name}"]
    if document.headline:
        lines.append(document.headline)
    lines.append(document.contact_line)
    lines.append("")

    for section in sorted(document.sections, key=lambda s: s.order):
        lines.append(f"## {section.title}")
        lines.append(section.content)
        lines.append("")

    markdown = "\n".join(lines).strip() + "\n"
    return markdown
