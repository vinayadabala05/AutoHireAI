"""Renders resume Markdown to HTML and exports both formats to disk.

PDF generation is intentionally out of scope for this sprint (per the
mission brief) — `export_pdf` does not exist here and should be added in a
future sprint, likely by feeding the HTML this module produces into a
headless renderer.

Only the Markdown subset `formatter.py` actually emits is supported here
(H1/H2/H3 headings, bold spans, `-` bullet lists, plain paragraphs) — this is
a purpose-built converter for our own deterministic output, not a general
Markdown parser, so it has no third-party dependency to pin or drift from.
"""

import html
import re
from pathlib import Path

from app.resume.models import ResumeDocument

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
    lines = markdown.splitlines()
    html_lines: list[str] = []
    in_list = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            html_lines.append("</ul>")
            in_list = False

    for raw_line in lines:
        line = raw_line.rstrip()
        if not line:
            close_list()
            continue
        if line.startswith("### "):
            close_list()
            html_lines.append(f"<h3>{_inline(line[4:])}</h3>")
        elif line.startswith("## "):
            close_list()
            html_lines.append(f"<h2>{_inline(line[3:])}</h2>")
        elif line.startswith("# "):
            close_list()
            html_lines.append(f"<h1>{_inline(line[2:])}</h1>")
        elif line.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{_inline(line[2:])}</li>")
        else:
            close_list()
            html_lines.append(f"<p>{_inline(line)}</p>")
    close_list()
    return "\n".join(html_lines)


def to_html(document: ResumeDocument, *, markdown: str) -> str:
    body = markdown_to_html(markdown)
    return _HTML_TEMPLATE.format(title=html.escape(document.full_name), body=body)


def export_markdown_file(markdown: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return path


def export_html_file(document: ResumeDocument, markdown: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_html(document, markdown=markdown), encoding="utf-8")
    return path
