"""Template registry for the cover letter generation engine.

A cover letter has one Markdown/HTML shape (produced by `formatter.py` /
`renderer.py`) — a template is a role-specific policy for which
`ResumeDocument` (Sprint 5) sections get pulled into the `career_summary`
context handed to the LLM, and in what priority order. This mirrors
`app.resume.templates.TemplateSpec`, applied one layer up: instead of
ordering the cover letter's own sections (there are only ever four, in a
fixed order), a template decides which parts of an *already-generated
resume* are worth summarizing for this role.
"""

from dataclasses import dataclass

from app.cover_letter.models import CoverLetterTemplate
from app.resume.models import ResumeSectionType

_DEFAULT_EMPHASIS = (
    ResumeSectionType.SUMMARY,
    ResumeSectionType.EXPERIENCE,
    ResumeSectionType.PROJECTS,
    ResumeSectionType.SKILLS,
)


@dataclass(frozen=True)
class TemplateSpec:
    """Immutable configuration for one cover letter template."""

    template: CoverLetterTemplate
    display_name: str
    emphasize_resume_sections: tuple[ResumeSectionType, ...]
    closing_phrase: str


_TEMPLATE_SPECS: dict[CoverLetterTemplate, TemplateSpec] = {
    CoverLetterTemplate.SOFTWARE_ENGINEER: TemplateSpec(
        template=CoverLetterTemplate.SOFTWARE_ENGINEER,
        display_name="Software Engineer",
        emphasize_resume_sections=_DEFAULT_EMPHASIS,
        closing_phrase="Sincerely,",
    ),
    CoverLetterTemplate.AI_ENGINEER: TemplateSpec(
        template=CoverLetterTemplate.AI_ENGINEER,
        display_name="AI Engineer",
        emphasize_resume_sections=(
            ResumeSectionType.SUMMARY,
            ResumeSectionType.PROJECTS,
            ResumeSectionType.SKILLS,
            ResumeSectionType.EXPERIENCE,
        ),
        closing_phrase="Sincerely,",
    ),
    CoverLetterTemplate.BACKEND_ENGINEER: TemplateSpec(
        template=CoverLetterTemplate.BACKEND_ENGINEER,
        display_name="Backend Engineer",
        emphasize_resume_sections=(
            ResumeSectionType.SUMMARY,
            ResumeSectionType.EXPERIENCE,
            ResumeSectionType.SKILLS,
            ResumeSectionType.PROJECTS,
        ),
        closing_phrase="Sincerely,",
    ),
    CoverLetterTemplate.RESEARCH_ENGINEER: TemplateSpec(
        template=CoverLetterTemplate.RESEARCH_ENGINEER,
        display_name="Research Engineer",
        emphasize_resume_sections=(
            ResumeSectionType.SUMMARY,
            ResumeSectionType.PROJECTS,
            ResumeSectionType.EDUCATION,
            ResumeSectionType.EXPERIENCE,
        ),
        closing_phrase="Respectfully,",
    ),
}


def get_template_spec(template: CoverLetterTemplate) -> TemplateSpec:
    """Look up the immutable spec for a template. Every enum member is registered."""
    return _TEMPLATE_SPECS[template]


def all_templates() -> list[CoverLetterTemplate]:
    return list(_TEMPLATE_SPECS.keys())
