"""Resume Generation Engine.

Consumes `ResumeBlueprint` (Sprint 3), `CareerProfile` (Sprint 3.5), and
`LLMService` (Sprint 4) to produce an ATS-optimized `ResumeDocument`,
exportable as Markdown or HTML. `ResumeGenerationService` is the single
entrypoint callers should use.
"""

from app.resume.models import (
    ResumeDocument,
    ResumeSection,
    ResumeSectionType,
    ResumeTemplate,
    ResumeValidationError,
    ResumeValidationIssue,
    ResumeValidationResult,
)
from app.resume.service import ResumeGenerationService

__all__ = [
    "ResumeDocument",
    "ResumeGenerationService",
    "ResumeSection",
    "ResumeSectionType",
    "ResumeTemplate",
    "ResumeValidationError",
    "ResumeValidationIssue",
    "ResumeValidationResult",
]
