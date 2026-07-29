"""Cover Letter Generation Engine.

Consumes `CareerProfile` (Sprint 3.5), `ResumeBlueprint` (Sprint 3),
`ResumeDocument` (Sprint 5), and `LLMService` (Sprint 4) to produce a
personalized, ATS-friendly `CoverLetterDocument`, exportable as Markdown or
HTML. `CoverLetterGenerationService` is the single entrypoint callers
should use.
"""

from app.cover_letter.models import (
    CoverLetterDocument,
    CoverLetterSection,
    CoverLetterSectionType,
    CoverLetterTemplate,
    CoverLetterValidationError,
    CoverLetterValidationIssue,
    CoverLetterValidationResult,
)
from app.cover_letter.service import CoverLetterGenerationService

__all__ = [
    "CoverLetterDocument",
    "CoverLetterGenerationService",
    "CoverLetterSection",
    "CoverLetterSectionType",
    "CoverLetterTemplate",
    "CoverLetterValidationError",
    "CoverLetterValidationIssue",
    "CoverLetterValidationResult",
]
