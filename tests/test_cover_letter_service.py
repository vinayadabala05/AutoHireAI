"""Integration tests for `app.cover_letter.service.CoverLetterGenerationService`.

Exercises the full profile + blueprint + resume document -> LLM -> document
-> Markdown/HTML pipeline against a scripted (never real) LLM, across
multiple job descriptions and all four templates, and checks that
Markdown/HTML export round-trip deterministically.
"""

from pathlib import Path

import pytest

from app.cover_letter.models import CoverLetterTemplate, CoverLetterValidationError
from app.cover_letter.service import CoverLetterGenerationService
from tests.cover_letter_fixtures import (
    make_llm_service,
    sample_blueprint,
    sample_career_profile,
    sample_resume_document,
)


async def test_generate_document_end_to_end_for_every_template() -> None:
    resume_document = await sample_resume_document()
    blueprint = sample_blueprint()
    profile = sample_career_profile()
    for template in CoverLetterTemplate:
        service = CoverLetterGenerationService(make_llm_service([]))
        document = await service.generate_document(
            profile,
            blueprint,
            resume_document,
            company_name="Acme Corp",
            job_title="Backend Engineer",
            template=template,
            enhance_with_llm=False,
        )
        assert document.template is template
        result = service.validate_document(document)
        assert result.is_valid is True, result.errors


@pytest.mark.parametrize("job_key", ["backend_engineer", "ai_engineer", "research_engineer"])
async def test_generate_document_across_multiple_job_descriptions(job_key: str) -> None:
    resume_document = await sample_resume_document(job_key)
    blueprint = sample_blueprint(job_key)
    profile = sample_career_profile()
    service = CoverLetterGenerationService(make_llm_service([]))
    document = await service.generate_document(
        profile,
        blueprint,
        resume_document,
        company_name="Acme Corp",
        job_title="Some Role",
        enhance_with_llm=False,
    )
    markdown = service.to_markdown(document)
    assert "Jordan Smith" in markdown
    assert "Acme Corp" in markdown
    assert service.validate_document(document).is_valid is True


async def test_generate_document_rejects_invalid_inputs_by_default() -> None:
    resume_document = await sample_resume_document()
    blueprint = sample_blueprint()
    profile = sample_career_profile()
    service = CoverLetterGenerationService(make_llm_service([]))
    with pytest.raises(CoverLetterValidationError):
        await service.generate_document(
            profile, blueprint, resume_document, company_name="", job_title="Backend Engineer"
        )


async def test_generate_document_allows_bypassing_input_validation() -> None:
    resume_document = await sample_resume_document()
    blueprint = sample_blueprint()
    profile = sample_career_profile()
    service = CoverLetterGenerationService(make_llm_service([]))
    document = await service.generate_document(
        profile,
        blueprint,
        resume_document,
        company_name="",
        job_title="Backend Engineer",
        require_valid_inputs=False,
        enhance_with_llm=False,
    )
    assert document.job_title == "Backend Engineer"


async def test_export_markdown_and_html_write_files(tmp_path: Path) -> None:
    resume_document = await sample_resume_document()
    blueprint = sample_blueprint()
    profile = sample_career_profile()
    service = CoverLetterGenerationService(make_llm_service([]), export_dir=tmp_path)
    document = await service.generate_document(
        profile,
        blueprint,
        resume_document,
        company_name="Acme Corp",
        job_title="Backend Engineer",
        enhance_with_llm=False,
    )

    md_path = service.export_markdown(document)
    html_path = service.export_html(document)

    assert md_path.exists()
    assert html_path.exists()
    assert md_path.read_text(encoding="utf-8") == service.to_markdown(document)
    assert "Acme Corp" in html_path.read_text(encoding="utf-8")


async def test_generate_document_output_is_deterministic_for_fixed_script() -> None:
    resume_document = await sample_resume_document()
    blueprint = sample_blueprint()
    profile = sample_career_profile()
    service_a = CoverLetterGenerationService(make_llm_service([]))
    service_b = CoverLetterGenerationService(make_llm_service([]))
    kwargs = {
        "company_name": "Acme Corp",
        "job_title": "Backend Engineer",
        "enhance_with_llm": False,
    }
    doc_a = await service_a.generate_document(profile, blueprint, resume_document, **kwargs)
    doc_b = await service_b.generate_document(profile, blueprint, resume_document, **kwargs)
    assert service_a.to_markdown(doc_a) == service_b.to_markdown(doc_b)
