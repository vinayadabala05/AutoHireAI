"""Deterministic job description analysis.

Turns a `JobPostingInput` into a structured `JobAnalysis` — required vs.
preferred skills, seniority, employment type, education/certificate asks —
using regex heuristics and the shared keyword vocabulary. No LLM calls.
"""

import re

from app.intelligence.keyword_extractor import KeywordExtractor
from app.intelligence.models import JobAnalysis, JobPostingInput, KeywordSet
from app.models.enums import EmploymentType, ExperienceLevel

# Checked in order — more specific seniority markers before broader ones,
# so e.g. "Senior Manager" resolves to LEAD (people-management) rather than
# just SENIOR.
_EXPERIENCE_LEVEL_PATTERNS: list[tuple[ExperienceLevel, re.Pattern[str]]] = [
    (ExperienceLevel.INTERN, re.compile(r"\bintern(ship)?\b", re.IGNORECASE)),
    (
        ExperienceLevel.ENTRY,
        re.compile(r"\bentry[- ]level\b|\bnew grad(uate)?\b|\b0-1 years?\b", re.IGNORECASE),
    ),
    (
        ExperienceLevel.EXECUTIVE,
        re.compile(r"\bdirector\b|\bvp\b|\bhead of\b|\bchief\b", re.IGNORECASE),
    ),
    (ExperienceLevel.PRINCIPAL, re.compile(r"\bprincipal\b|\bstaff\b", re.IGNORECASE)),
    (ExperienceLevel.LEAD, re.compile(r"\blead\b|\bmanager\b", re.IGNORECASE)),
    (
        ExperienceLevel.SENIOR,
        re.compile(
            r"\bsenior\b|\bsr\.?\b|\b[5-9]\+? ?years?\b|\b1[0-9]\+? ?years?\b", re.IGNORECASE
        ),
    ),
    (ExperienceLevel.JUNIOR, re.compile(r"\bjunior\b|\b1-2 years?\b", re.IGNORECASE)),
    (ExperienceLevel.MID, re.compile(r"\bmid[- ]level\b|\b3-5 years?\b", re.IGNORECASE)),
]

_EMPLOYMENT_TYPE_PATTERNS: list[tuple[EmploymentType, re.Pattern[str]]] = [
    (EmploymentType.INTERNSHIP, re.compile(r"\binternship\b|\bintern\b", re.IGNORECASE)),
    (
        EmploymentType.CONTRACT,
        re.compile(r"\bcontract\b|\bc2c\b|\bcorp[- ]to[- ]corp\b", re.IGNORECASE),
    ),
    (EmploymentType.FREELANCE, re.compile(r"\bfreelance\b", re.IGNORECASE)),
    (EmploymentType.PART_TIME, re.compile(r"\bpart[- ]time\b", re.IGNORECASE)),
    (EmploymentType.TEMPORARY, re.compile(r"\btemporary\b|\btemp\b", re.IGNORECASE)),
    (EmploymentType.FULL_TIME, re.compile(r"\bfull[- ]time\b", re.IGNORECASE)),
]

_EDUCATION_PATTERN = re.compile(
    r"(bachelor'?s?(?: degree)?|b\.?s\.?c?\.?|master'?s?(?: degree)?|m\.?s\.?c?\.?|ph\.?d\.?|"
    r"doctorate|associate'?s? degree)(?: in [a-zA-Z, ]+)?",
    re.IGNORECASE,
)

_CERTIFICATE_KEYWORDS = [
    "AWS Certified",
    "Azure Certified",
    "Google Cloud Certified",
    "PMP",
    "CKA",
    "CKAD",
    "CISSP",
    "CompTIA",
    "Scrum Master",
    "CSM",
    "Certified Kubernetes",
]

_PREFERRED_MARKER = re.compile(
    r"(?:nice to have|preferred|bonus|a plus|good to have)s?[:\-]?\s*(.*)", re.IGNORECASE
)


class JobAnalyzer:
    def __init__(self, keyword_extractor: KeywordExtractor | None = None) -> None:
        self._keyword_extractor = keyword_extractor or KeywordExtractor()

    def analyze(self, job: JobPostingInput) -> JobAnalysis:
        full_text = "\n".join(
            [
                job.title,
                job.description,
                *job.requirements,
                *job.responsibilities,
                *job.preferred_skills,
            ]
        )
        keywords = self._keyword_extractor.extract(full_text)

        required_skills = self._extract_required_skills(job, keywords)
        preferred_skills = self._extract_preferred_skills(job, required_skills)

        return JobAnalysis(
            title=job.title,
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            experience_level=self._detect_experience_level(full_text),
            employment_type=self._detect_employment_type(full_text),
            keywords=keywords,
            technologies=keywords.all_technical(),
            soft_skills=list(keywords.soft_skills),
            responsibilities=list(job.responsibilities),
            education_requirements=self._extract_education(full_text),
            certificates=self._extract_certificates(full_text),
        )

    def _extract_required_skills(self, job: JobPostingInput, keywords: KeywordSet) -> list[str]:
        requirements_text = "\n".join(job.requirements) or job.description
        required = self._keyword_extractor.extract(requirements_text).all_technical()
        # Sparse/unstructured requirements: fall back to every technical
        # keyword found anywhere in the posting.
        return required or keywords.all_technical()

    def _extract_preferred_skills(
        self, job: JobPostingInput, required_skills: list[str]
    ) -> list[str]:
        candidates: list[str] = []
        if job.preferred_skills:
            candidates += self._keyword_extractor.extract(
                "\n".join(job.preferred_skills)
            ).all_technical()

        # Requirements/description sometimes bury a "nice to have" clause
        # instead of a separate field.
        for source in (job.description, *job.requirements):
            match = _PREFERRED_MARKER.search(source)
            if match:
                candidates += self._keyword_extractor.extract(match.group(1)).all_technical()

        required_lower = {skill.lower() for skill in required_skills}
        deduped: list[str] = []
        seen: set[str] = set()
        for skill in candidates:
            key = skill.lower()
            if key in required_lower or key in seen:
                continue
            seen.add(key)
            deduped.append(skill)
        return deduped

    def _detect_experience_level(self, text: str) -> ExperienceLevel | None:
        for level, pattern in _EXPERIENCE_LEVEL_PATTERNS:
            if pattern.search(text):
                return level
        return None

    def _detect_employment_type(self, text: str) -> EmploymentType | None:
        for employment_type, pattern in _EMPLOYMENT_TYPE_PATTERNS:
            if pattern.search(text):
                return employment_type
        return None

    def _extract_education(self, text: str) -> list[str]:
        return sorted({match.group(0).strip() for match in _EDUCATION_PATTERN.finditer(text)})

    def _extract_certificates(self, text: str) -> list[str]:
        return [
            cert
            for cert in _CERTIFICATE_KEYWORDS
            if re.search(re.escape(cert), text, re.IGNORECASE)
        ]
