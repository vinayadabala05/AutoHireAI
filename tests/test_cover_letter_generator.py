"""Unit tests for `app.cover_letter.generator.CoverLetterGenerator`.

Uses a scripted fake LLM provider (see `tests.resume_fixtures`), never a
real network call, and a real `ResumeDocument` produced by Sprint 5's
`ResumeGenerator` so the career-summary extraction is exercised end-to-end.
"""

from app.cover_letter.generator import CoverLetterGenerator
from app.cover_letter.models import CoverLetterSectionType, CoverLetterTemplate
from tests.cover_letter_fixtures import (
    make_llm_service,
    sample_blueprint,
    sample_career_profile,
    sample_resume_document,
)


async def test_generate_produces_all_four_sections_in_order() -> None:
    resume_document = await sample_resume_document()
    generator = CoverLetterGenerator(make_llm_service(["A tailored cover letter body."]))
    document = await generator.generate(
        sample_career_profile(),
        sample_blueprint(),
        resume_document,
        company_name="Acme Corp",
        job_title="Backend Engineer",
    )
    assert [s.section_type for s in document.sections] == [
        CoverLetterSectionType.GREETING,
        CoverLetterSectionType.BODY,
        CoverLetterSectionType.CLOSING,
        CoverLetterSectionType.SIGNATURE,
    ]


async def test_generate_uses_llm_for_body_when_enhanced() -> None:
    resume_document = await sample_resume_document()
    generator = CoverLetterGenerator(make_llm_service(["A tailored cover letter body."]))
    document = await generator.generate(
        sample_career_profile(),
        sample_blueprint(),
        resume_document,
        company_name="Acme Corp",
        job_title="Backend Engineer",
        enhance_with_llm=True,
    )
    body = document.section(CoverLetterSectionType.BODY)
    assert body is not None
    assert body.content == "A tailored cover letter body."


async def test_generate_without_llm_uses_raw_career_summary() -> None:
    resume_document = await sample_resume_document()
    service = make_llm_service([])
    document = await CoverLetterGenerator(service).generate(
        sample_career_profile(),
        sample_blueprint(),
        resume_document,
        company_name="Acme Corp",
        job_title="Backend Engineer",
        enhance_with_llm=False,
    )
    assert service.provider.calls == 0  # type: ignore[attr-defined]
    body = document.section(CoverLetterSectionType.BODY)
    assert body is not None
    assert body.content


async def test_generate_greeting_uses_hiring_manager_when_given() -> None:
    resume_document = await sample_resume_document()
    document = await CoverLetterGenerator(make_llm_service([])).generate(
        sample_career_profile(),
        sample_blueprint(),
        resume_document,
        company_name="Acme Corp",
        job_title="Backend Engineer",
        hiring_manager="Alex Lee",
        enhance_with_llm=False,
    )
    greeting = document.section(CoverLetterSectionType.GREETING)
    assert greeting is not None
    assert greeting.content == "Dear Alex Lee,"


async def test_generate_greeting_falls_back_to_hiring_manager_generic() -> None:
    resume_document = await sample_resume_document()
    document = await CoverLetterGenerator(make_llm_service([])).generate(
        sample_career_profile(),
        sample_blueprint(),
        resume_document,
        company_name="Acme Corp",
        job_title="Backend Engineer",
        enhance_with_llm=False,
    )
    greeting = document.section(CoverLetterSectionType.GREETING)
    assert greeting is not None
    assert greeting.content == "Dear Hiring Manager,"


async def test_generate_closing_phrase_varies_by_template() -> None:
    resume_document = await sample_resume_document()
    document = await CoverLetterGenerator(make_llm_service([])).generate(
        sample_career_profile(),
        sample_blueprint(),
        resume_document,
        company_name="Acme Corp",
        job_title="Research Engineer",
        template=CoverLetterTemplate.RESEARCH_ENGINEER,
        enhance_with_llm=False,
    )
    closing = document.section(CoverLetterSectionType.CLOSING)
    assert closing is not None
    assert closing.content == "Respectfully,"


async def test_generate_signature_uses_full_name() -> None:
    resume_document = await sample_resume_document()
    document = await CoverLetterGenerator(make_llm_service([])).generate(
        sample_career_profile(),
        sample_blueprint(),
        resume_document,
        company_name="Acme Corp",
        job_title="Backend Engineer",
        enhance_with_llm=False,
    )
    signature = document.section(CoverLetterSectionType.SIGNATURE)
    assert signature is not None
    assert signature.content == "Jordan Smith"


async def test_generate_is_deterministic_given_the_same_script() -> None:
    resume_document = await sample_resume_document()
    blueprint = sample_blueprint()
    profile = sample_career_profile()
    doc_a = await CoverLetterGenerator(make_llm_service([])).generate(
        profile, blueprint, resume_document, "Acme Corp", "Backend Engineer", enhance_with_llm=False
    )
    doc_b = await CoverLetterGenerator(make_llm_service([])).generate(
        profile, blueprint, resume_document, "Acme Corp", "Backend Engineer", enhance_with_llm=False
    )
    assert [s.content for s in doc_a.sections] == [s.content for s in doc_b.sections]
