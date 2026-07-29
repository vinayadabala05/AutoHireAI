"""Template registry for the resume generation engine.

A "template" in Sprint 5 is not a layout/typography concern (there is only
one Markdown/HTML shape, produced by `formatter.py`/`renderer.py`) — it is a
role-specific *section ordering and emphasis* policy. `ResumeBlueprint`
(Sprint 3) already computes an optimal section order for a specific job via
`SectionOptimizer`; a template only supplies the fallback used when the
blueprint didn't specify one, plus the human-facing display name and which
sections that role should emphasize (used by `generator.py` to decide which
sections are worth an LLM rewrite pass vs. deterministic formatting).
"""

from dataclasses import dataclass

from app.resume.models import ResumeSectionType, ResumeTemplate

_DEFAULT_ORDER = (
    ResumeSectionType.SUMMARY,
    ResumeSectionType.EXPERIENCE,
    ResumeSectionType.PROJECTS,
    ResumeSectionType.SKILLS,
    ResumeSectionType.EDUCATION,
    ResumeSectionType.CERTIFICATES,
)


@dataclass(frozen=True)
class TemplateSpec:
    """Immutable configuration for one resume template."""

    template: ResumeTemplate
    display_name: str
    default_section_order: tuple[ResumeSectionType, ...]
    emphasize_sections: tuple[ResumeSectionType, ...]


_TEMPLATE_SPECS: dict[ResumeTemplate, TemplateSpec] = {
    ResumeTemplate.SOFTWARE_ENGINEER: TemplateSpec(
        template=ResumeTemplate.SOFTWARE_ENGINEER,
        display_name="Software Engineer",
        default_section_order=_DEFAULT_ORDER,
        emphasize_sections=(ResumeSectionType.EXPERIENCE, ResumeSectionType.PROJECTS),
    ),
    ResumeTemplate.AI_ENGINEER: TemplateSpec(
        template=ResumeTemplate.AI_ENGINEER,
        display_name="AI Engineer",
        default_section_order=(
            ResumeSectionType.SUMMARY,
            ResumeSectionType.SKILLS,
            ResumeSectionType.PROJECTS,
            ResumeSectionType.EXPERIENCE,
            ResumeSectionType.EDUCATION,
            ResumeSectionType.CERTIFICATES,
        ),
        emphasize_sections=(ResumeSectionType.SKILLS, ResumeSectionType.PROJECTS),
    ),
    ResumeTemplate.BACKEND_ENGINEER: TemplateSpec(
        template=ResumeTemplate.BACKEND_ENGINEER,
        display_name="Backend Engineer",
        default_section_order=_DEFAULT_ORDER,
        emphasize_sections=(ResumeSectionType.EXPERIENCE,),
    ),
    ResumeTemplate.RESEARCH_ENGINEER: TemplateSpec(
        template=ResumeTemplate.RESEARCH_ENGINEER,
        display_name="Research Engineer",
        default_section_order=(
            ResumeSectionType.SUMMARY,
            ResumeSectionType.PROJECTS,
            ResumeSectionType.EXPERIENCE,
            ResumeSectionType.SKILLS,
            ResumeSectionType.EDUCATION,
            ResumeSectionType.CERTIFICATES,
        ),
        emphasize_sections=(ResumeSectionType.PROJECTS, ResumeSectionType.EDUCATION),
    ),
}


def get_template_spec(template: ResumeTemplate) -> TemplateSpec:
    """Look up the immutable spec for a template. Every enum member is registered."""
    return _TEMPLATE_SPECS[template]


def resolve_section_order(
    template: ResumeTemplate, blueprint_sections: list[str]
) -> list[ResumeSectionType]:
    """Prefer the blueprint's own section order, falling back to the template default.

    `blueprint_sections` is `ResumeBlueprint.resume_sections` verbatim — plain
    strings computed by Sprint 3's `SectionOptimizer` for this specific job.
    Unknown/unparseable entries are dropped rather than raised on, since a
    future Sprint 3 change to add a new section name shouldn't break Sprint 5.
    """
    resolved: list[ResumeSectionType] = []
    for name in blueprint_sections:
        try:
            resolved.append(ResumeSectionType(name))
        except ValueError:
            continue
    if resolved:
        return resolved
    return list(get_template_spec(template).default_section_order)


def all_templates() -> list[ResumeTemplate]:
    return list(_TEMPLATE_SPECS.keys())
