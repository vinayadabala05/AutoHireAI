"""Renders a `CoverLetterDocument` to ATS-friendly Markdown.

ATS-friendly means: plain header lines (no tables, no columns), no images,
and section content rendered as-is in fixed order — the format most
Applicant Tracking Systems parse reliably. This module is a pure function
of `CoverLetterDocument`; given the same document it always produces the
same string.
"""

from app.cover_letter.models import CoverLetterDocument, CoverLetterSectionType


def to_markdown(document: CoverLetterDocument) -> str:
    lines: list[str] = [document.full_name, document.contact_line, document.date_line, ""]
    lines.append(document.company_name)
    lines.append(f"Re: {document.job_title}")
    lines.append("")

    ordered = sorted(document.sections, key=lambda s: s.order)
    greeting = document.section(CoverLetterSectionType.GREETING)
    body = document.section(CoverLetterSectionType.BODY)
    closing = document.section(CoverLetterSectionType.CLOSING)
    signature = document.section(CoverLetterSectionType.SIGNATURE)

    for section in ordered:
        if section is greeting or section is body:
            lines.append(section.content)
            lines.append("")
        elif section is closing or section is signature:
            lines.append(section.content)
        else:
            lines.append(section.content)
            lines.append("")

    markdown = "\n".join(lines).strip() + "\n"
    return markdown
