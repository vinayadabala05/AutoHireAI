"""Renders cover letter Markdown to HTML and exports both formats to disk.

PDF generation is out of scope for this sprint, matching Sprint 5's
convention — a future sprint can feed the HTML this module produces into a
headless renderer.

This is a purpose-built converter for the plain-paragraph Markdown
`formatter.py` emits (bold spans, blank-line-separated paragraphs) — not a
general Markdown parser — kept independent of `app.resume.renderer` so each
generation engine stays self-contained, per Sprint 4/5's "one facade per
subsystem, no cross-package reach-through" convention.
"""

import html
import re
from pathlib import Path

from app.cover_letter.models import CoverLetterDocument

_BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*")

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
</head>
<body>
{body}
</body>
</html>
"""


def _inline(text: str) -> str:
    escaped = html.escape(text)
    return _BOLD_PATTERN.sub(r"<strong>\1</strong>", escaped)


def markdown_to_html(markdown: str) -> str:
    paragraphs = [block.strip() for block in markdown.split("\n\n")]
    html_blocks = []
    for block in paragraphs:
        if not block:
            continue
        inner = "<br>".join(_inline(line) for line in block.splitlines() if line.strip())
        if inner:
            html_blocks.append(f"<p>{inner}</p>")
    return "\n".join(html_blocks)


def to_html(document: CoverLetterDocument, *, markdown: str) -> str:
    body = markdown_to_html(markdown)
    title = html.escape(f"{document.full_name} — {document.company_name}")
    return _HTML_TEMPLATE.format(title=title, body=body)


def export_markdown_file(markdown: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return path


def export_html_file(document: CoverLetterDocument, markdown: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_html(document, markdown=markdown), encoding="utf-8")
    return path
