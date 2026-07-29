"""Shared, provider-agnostic parsing helpers.

Every provider in `providers/` fetches a different vendor JSON shape and
knows how to map its own fields — but all four need the same *text*
extraction from a free-form job description: stripping HTML, guessing
work-arrangement and experience level from natural language, extracting a
salary range, and pulling out a skill list. Centralizing that here means a
future provider (LinkedIn, Indeed) reuses it immediately instead of
reimplementing per-vendor heuristics.

Skill extraction reuses Sprint 3's `KeywordExtractor` (the same curated
vocabulary `JobAnalyzer` already matches resumes against), so a discovered
job's `skills` list speaks the same vocabulary a `ResumeBlueprint` was
computed from.
"""

import re

from app.intelligence.keyword_extractor import KeywordExtractor
from app.models.enums import ExperienceLevel, RemoteType

_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_WHITESPACE_PATTERN = re.compile(r"[ \t]+")
_BLANK_LINES_PATTERN = re.compile(r"\n{3,}")

_REMOTE_PATTERN = re.compile(r"\b(fully\s+)?remote\b", re.IGNORECASE)
_HYBRID_PATTERN = re.compile(r"\bhybrid\b", re.IGNORECASE)
_ONSITE_PATTERN = re.compile(r"\b(on[\s-]?site|in[\s-]?office)\b", re.IGNORECASE)

# Ordered least -> most senior; matched against title/description with the
# *last* matching keyword winning, so "Senior" in a description mentioning
# "mentors junior engineers" doesn't misclassify an otherwise senior role.
_EXPERIENCE_KEYWORDS: list[tuple[ExperienceLevel, re.Pattern[str]]] = [
    (ExperienceLevel.INTERN, re.compile(r"\bintern(ship)?\b", re.IGNORECASE)),
    (ExperienceLevel.ENTRY, re.compile(r"\bentry[\s-]?level\b", re.IGNORECASE)),
    (ExperienceLevel.JUNIOR, re.compile(r"\bjunior\b", re.IGNORECASE)),
    (ExperienceLevel.MID, re.compile(r"\bmid[\s-]?level\b", re.IGNORECASE)),
    (ExperienceLevel.SENIOR, re.compile(r"\bsenior\b|\bsr\.\b", re.IGNORECASE)),
    (ExperienceLevel.LEAD, re.compile(r"\blead\b", re.IGNORECASE)),
    (ExperienceLevel.PRINCIPAL, re.compile(r"\bprincipal\b|\bstaff\b", re.IGNORECASE)),
    (ExperienceLevel.EXECUTIVE, re.compile(r"\bdirector\b|\bvp\b|\bexecutive\b", re.IGNORECASE)),
]

_SALARY_PATTERN = re.compile(
    r"(?P<currency>[$€£]|USD|EUR|GBP)?\s*"
    r"(?P<low>\d{2,3}(?:,\d{3})?(?:\.\d+)?)\s*[kK]?"
    r"\s*(?:-|to|–)\s*"
    r"(?P<currency2>[$€£]|USD|EUR|GBP)?\s*"
    r"(?P<high>\d{2,3}(?:,\d{3})?(?:\.\d+)?)\s*[kK]?"
)

_CURRENCY_SYMBOLS = {"$": "USD", "€": "EUR", "£": "GBP"}


def strip_html(text: str | None) -> str:
    """Strip HTML tags and collapse whitespace from provider-supplied rich text."""
    if not text:
        return ""
    without_tags = _HTML_TAG_PATTERN.sub(" ", text)
    without_tags = without_tags.replace("&nbsp;", " ").replace("&amp;", "&")
    collapsed = _WHITESPACE_PATTERN.sub(" ", without_tags)
    return _BLANK_LINES_PATTERN.sub("\n\n", collapsed).strip()


def extract_skills(*texts: str) -> list[str]:
    """Extract a flat, deduplicated technical skill list from job text."""
    keywords = KeywordExtractor().extract(" ".join(t for t in texts if t))
    return keywords.all_technical()


def guess_remote_type(*texts: str) -> RemoteType | None:
    """Heuristically infer work arrangement from location/description text.

    Checked in specificity order: hybrid and onsite mentions are more
    specific than a bare "remote", so they're matched first to avoid a
    description like "hybrid (remote-friendly)" being misread as fully
    remote.
    """
    combined = " ".join(t for t in texts if t)
    if _HYBRID_PATTERN.search(combined):
        return RemoteType.HYBRID
    if _ONSITE_PATTERN.search(combined):
        return RemoteType.ONSITE
    if _REMOTE_PATTERN.search(combined):
        return RemoteType.REMOTE
    return None


def guess_experience_level(*texts: str) -> ExperienceLevel | None:
    """Heuristically infer seniority from title/description text.

    The last matching keyword wins (scanning title then description, in
    increasing seniority order) so a more specific/later mention overrides
    an earlier, more generic one.
    """
    combined = " ".join(t for t in texts if t)
    best: ExperienceLevel | None = None
    for level, pattern in _EXPERIENCE_KEYWORDS:
        if pattern.search(combined):
            best = level
    return best


def extract_salary_from_text(text: str | None) -> tuple[float | None, float | None, str | None]:
    """Best-effort salary range extraction from free-form text.

    Returns `(min, max, currency)`, any of which may be `None` if not
    found. Handles `"$120,000 - $150,000"`, `"120k-150k USD"`, and similar
    patterns; this is a heuristic fallback for providers with no structured
    compensation field, not a substitute for one that has it.
    """
    if not text:
        return None, None, None
    match = _SALARY_PATTERN.search(text)
    if not match:
        return None, None, None

    span = match.group(0)
    currency_symbol = match.group("currency") or match.group("currency2")
    if not currency_symbol and "k" not in span.lower():
        # Too ambiguous without a currency marker or "k" suffix — e.g. a
        # "3-5 years" experience range would otherwise false-positive.
        return None, None, None

    def _to_number(raw: str, had_k_suffix_context: str) -> float:
        value = float(raw.replace(",", ""))
        if "k" in had_k_suffix_context.lower():
            value *= 1000
        return value

    low = _to_number(match.group("low"), span)
    high = _to_number(match.group("high"), span)
    currency = _CURRENCY_SYMBOLS.get(currency_symbol or "", currency_symbol)
    return min(low, high), max(low, high), currency


def normalize_location(location: str | None) -> str | None:
    """Collapse whitespace/casing artifacts in a provider's raw location string."""
    if not location:
        return None
    cleaned = _WHITESPACE_PATTERN.sub(" ", location).strip(" ,")
    return cleaned or None
