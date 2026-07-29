"""Unit tests for `app.job_discovery.parser` shared text-extraction helpers."""

from app.job_discovery.parser import (
    extract_salary_from_text,
    extract_skills,
    guess_experience_level,
    guess_remote_type,
    normalize_location,
    strip_html,
)
from app.models.enums import ExperienceLevel, RemoteType


def test_strip_html_removes_tags_and_entities() -> None:
    result = strip_html("<p>Build APIs with <b>Python</b> &amp; FastAPI.</p>")
    assert "<" not in result
    assert "Python" in result
    assert "&" in result


def test_strip_html_collapses_excess_blank_lines() -> None:
    result = strip_html("Para one.\n\n\n\nPara two.")
    assert "\n\n\n" not in result


def test_strip_html_handles_none_and_empty() -> None:
    assert strip_html(None) == ""
    assert strip_html("") == ""


def test_extract_skills_finds_known_technologies() -> None:
    skills = extract_skills("We use Python, FastAPI, and PostgreSQL daily.")
    assert "Python" in skills
    assert "FastAPI" in skills
    assert "PostgreSQL" in skills


def test_extract_skills_across_multiple_text_fragments() -> None:
    skills = extract_skills("Python role", "Requires Docker and Kubernetes experience.")
    assert "Docker" in skills
    assert "Kubernetes" in skills


def test_guess_remote_type_detects_hybrid_before_remote() -> None:
    assert guess_remote_type("Hybrid role, remote-friendly") is RemoteType.HYBRID


def test_guess_remote_type_detects_onsite() -> None:
    assert guess_remote_type("This is an on-site position in NYC") is RemoteType.ONSITE


def test_guess_remote_type_detects_remote() -> None:
    assert guess_remote_type("Fully remote position") is RemoteType.REMOTE


def test_guess_remote_type_returns_none_when_no_signal() -> None:
    assert guess_remote_type("Software Engineer", "Build great things.") is None


def test_guess_experience_level_detects_senior() -> None:
    assert guess_experience_level("Senior Backend Engineer", "") is ExperienceLevel.SENIOR


def test_guess_experience_level_detects_intern() -> None:
    assert guess_experience_level("Summer Internship", "") is ExperienceLevel.INTERN


def test_guess_experience_level_most_senior_match_wins() -> None:
    # Both "junior" and "Senior" appear; the more senior keyword wins
    # since keywords are scanned in increasing-seniority order and the
    # last (most senior) match overwrites earlier ones.
    level = guess_experience_level("Senior Engineer", "Will mentor junior engineers directly.")
    assert level is ExperienceLevel.SENIOR


def test_guess_experience_level_returns_none_when_no_signal() -> None:
    assert guess_experience_level("Software Engineer", "Build things.") is None


def test_extract_salary_from_text_with_currency_symbol() -> None:
    salary_min, salary_max, currency = extract_salary_from_text("Pay: $120,000 - $150,000 per year")
    assert salary_min == 120000.0
    assert salary_max == 150000.0
    assert currency == "USD"


def test_extract_salary_from_text_with_k_suffix() -> None:
    salary_min, salary_max, currency = extract_salary_from_text("Compensation: 120k-150k USD")
    assert salary_min == 120000.0
    assert salary_max == 150000.0


def test_extract_salary_from_text_ignores_ambiguous_ranges() -> None:
    # "3-5 years" has no currency marker or "k" suffix, so should not be
    # mistaken for a salary range.
    assert extract_salary_from_text("Requires 3-5 years of experience") == (None, None, None)


def test_extract_salary_from_text_ignores_two_digit_ranges_without_currency_or_k() -> None:
    # A bare "24-36 months" has 2-digit numbers (matching the digit-count
    # pattern) but no currency symbol or "k" suffix, so the ambiguity
    # guard should still discard it.
    assert extract_salary_from_text("Contract length: 24-36 months") == (None, None, None)


def test_extract_salary_from_text_returns_none_for_no_text() -> None:
    assert extract_salary_from_text(None) == (None, None, None)
    assert extract_salary_from_text("") == (None, None, None)


def test_extract_salary_from_text_returns_none_when_no_match() -> None:
    assert extract_salary_from_text("Competitive salary, benefits included.") == (None, None, None)


def test_normalize_location_collapses_whitespace_and_trailing_commas() -> None:
    assert normalize_location("  San   Francisco,  CA, ") == "San Francisco, CA"


def test_normalize_location_returns_none_for_empty() -> None:
    assert normalize_location(None) is None
    assert normalize_location("") is None
    assert normalize_location("   ") is None
