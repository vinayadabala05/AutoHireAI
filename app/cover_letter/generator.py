"""Turns (`CareerProfile`, `ResumeBlueprint`, `ResumeDocument`) + job/company
context into a `CoverLetterDocument`.

This is the only module in `app/cover_letter/` that talks to `LLMService`
(Sprint 4) — every other module here is a pure transform. Only the `Body`
section is LLM-generated (via `prompts/cover_letter/generate_cover_letter.txt`,
the one cover letter prompt Sprint 4 shipped); `Greeting`, `Closing`, and
`Signature` are built deterministically, so most of the document stays
reproducible without mocking the LLM for the whole document — the same
convention `app.resume.generator.ResumeGenerator` established.

The `career_summary` fed to the LLM is built from an already-generated
`ResumeDocument` (Sprint 5), not re-derived from `CareerProfile` — Sprint 6
is explicitly a consumer of Sprint 5's output, not a second resume
summarizer.
"""

from datetime import UTC, datetime

from app.career_profile.models import CareerProfile
from app.cover_letter.models import (
    CoverLetterDocument,
    CoverLetterSection,
    CoverLetterSectionType,
    CoverLetterTemplate,
)
from app.cover_letter.templates import get_template_spec
from app.intelligence.models import ResumeBlueprint
from app.llm.models import LLMRequest
from app.llm.service import LLMService
from app.resume.models import ResumeDocument

_MAX_SECTION_CHARS = 400


def _contact_line(profile: CareerProfile) -> str:
    info = profile.personal_info
    parts = [info.email]
    if info.phone:
        parts.append(info.phone)
    if info.location:
        parts.append(info.location)
    return " | ".join(parts)


def _career_summary(
    resume_document: ResumeDocument, blueprint: ResumeBlueprint, template: CoverLetterTemplate
) -> str:
    spec = get_template_spec(template)
    fragments: list[str] = []
    for section_type in spec.emphasize_resume_sections:
        section = resume_document.section(section_type)
        if section is None:
            continue
        content = section.content.strip()
        if not content:
            continue
        fragments.append(content[:_MAX_SECTION_CHARS])
    if blueprint.recommended_skills:
        fragments.append("Key skills: " + ", ".join(blueprint.recommended_skills))
    return "\n\n".join(fragments) if fragments else "No prior background on file."


def _greeting_content(hiring_manager: str | None) -> str:
    recipient = hiring_manager or "Hiring Manager"
    return f"Dear {recipient},"


def _closing_content(template: CoverLetterTemplate) -> str:
    return get_template_spec(template).closing_phrase


def _signature_content(profile: CareerProfile) -> str:
    return profile.personal_info.full_name


class CoverLetterGenerator:
    """Async pipeline turning (profile, blueprint, resume document, job context)
    into a `CoverLetterDocument`.
    """

    def __init__(self, llm_service: LLMService) -> None:
        self._llm = llm_service

    async def generate(
        self,
        profile: CareerProfile,
        blueprint: ResumeBlueprint,
        resume_document: ResumeDocument,
        company_name: str,
        job_title: str,
        job_description: str = "",
        template: CoverLetterTemplate = CoverLetterTemplate.SOFTWARE_ENGINEER,
        hiring_manager: str | None = None,
        enhance_with_llm: bool = True,
    ) -> CoverLetterDocument:
        career_summary = _career_summary(resume_document, blueprint, template)
        body_content = await self._body_content(
            profile, company_name, job_title, job_description, career_summary, enhance_with_llm
        )

        sections = [
            CoverLetterSection(
                section_type=CoverLetterSectionType.GREETING,
                title=CoverLetterSectionType.GREETING.value,
                content=_greeting_content(hiring_manager),
                order=0,
            ),
            CoverLetterSection(
                section_type=CoverLetterSectionType.BODY,
                title=CoverLetterSectionType.BODY.value,
                content=body_content,
                order=1,
            ),
            CoverLetterSection(
                section_type=CoverLetterSectionType.CLOSING,
                title=CoverLetterSectionType.CLOSING.value,
                content=_closing_content(template),
                order=2,
            ),
            CoverLetterSection(
                section_type=CoverLetterSectionType.SIGNATURE,
                title=CoverLetterSectionType.SIGNATURE.value,
                content=_signature_content(profile),
                order=3,
            ),
        ]

        return CoverLetterDocument(
            full_name=profile.personal_info.full_name,
            contact_line=_contact_line(profile),
            date_line=datetime.now(UTC).strftime("%B %d, %Y"),
            company_name=company_name,
            hiring_manager=hiring_manager,
            job_title=job_title,
            template=template,
            sections=sections,
            generated_at=datetime.now(UTC),
            metadata={"match_score": blueprint.match_score},
        )

    async def _body_content(
        self,
        profile: CareerProfile,
        company_name: str,
        job_title: str,
        job_description: str,
        career_summary: str,
        enhance_with_llm: bool,
    ) -> str:
        if not enhance_with_llm:
            return career_summary
        prompt_text = self._llm.render_prompt(
            "cover_letter",
            "generate_cover_letter",
            {
                "full_name": profile.personal_info.full_name,
                "job_title": job_title,
                "company_name": company_name,
                "career_summary": career_summary,
                "job_description": job_description,
            },
        )
        response = await self._llm.generate(LLMRequest(prompt=prompt_text))
        return response.content.strip()
