"""Integration tests for `app.resume.service.ResumeGenerationService`.

Exercises the full blueprint -> profile -> LLM -> document -> Markdown/HTML
pipeline against a scripted (never real) LLM, across multiple job
descriptions and all four templates, and checks that Markdown/HTML export
round-trip deterministically.
"""

from pathlib import Path

import pytest

from app.intelligence.resume_planner import ResumePlanner
from app.resume.models import ResumeTemplate, ResumeValidationError
from app.resume.service import ResumeGenerationService
from tests.intelligence_fixtures import SAMPLE_JOBS, sample_career_context
from tests.resume_fixtures import make_llm_service, profile_with_no_skills, sample_career_profile


async def test_generate_document_end_to_end_for_every_template() -> None:
    blueprint = ResumePlanner().plan(SAMPLE_JOBS["backend_engineer"], sample_career_context())
    profile = sample_career_profile()
    for template in ResumeTemplate:
        service = ResumeGenerationService(make_llm_service([]))
        document = await service.generate_document(
            blueprint, profile, template=template, enhance_with_llm=False
        )
        assert document.template is template
        result = service.validate_document(document)
        assert result.is_valid is True, result.errors


@pytest.mark.parametrize("job_key", ["backend_engineer", "ai_engineer", "research_engineer"])
async def test_generate_document_across_multiple_job_descriptions(job_key: str) -> None:
    blueprint = ResumePlanner().plan(SAMPLE_JOBS[job_key], sample_career_context())
    profile = sample_career_profile()
    service = ResumeGenerationService(make_llm_service([]))
    document = await service.generate_document(blueprint, profile, enhance_with_llm=False)
    markdown = service.to_markdown(document)
    assert "# Jordan Smith" in markdown
    assert service.validate_document(document).is_valid is True


async def test_generate_document_rejects_invalid_inputs_by_default() -> None:
    blueprint = ResumePlanner().plan(SAMPLE_JOBS["backend_engineer"], sample_career_context())
    service = ResumeGenerationService(make_llm_service([]))
    with pytest.raises(ResumeValidationError):
        await service.generate_document(blueprint, profile_with_no_skills())


async def test_generate_document_allows_bypassing_input_validation() -> None:
    blueprint = ResumePlanner().plan(SAMPLE_JOBS["backend_engineer"], sample_career_context())
    service = ResumeGenerationService(make_llm_service([]))
    document = await service.generate_document(
        blueprint, profile_with_no_skills(), require_valid_inputs=False, enhance_with_llm=False
    )
    assert document.full_name == "Jordan Smith"


async def test_export_markdown_and_html_write_files(tmp_path: Path) -> None:
    blueprint = ResumePlanner().plan(SAMPLE_JOBS["backend_engineer"], sample_career_context())
    profile = sample_career_profile()
    service = ResumeGenerationService(make_llm_service([]), export_dir=tmp_path)
    document = await service.generate_document(blueprint, profile, enhance_with_llm=False)

    md_path = service.export_markdown(document)
    html_path = service.export_html(document)

    assert md_path.exists()
    assert html_path.exists()
    assert md_path.read_text(encoding="utf-8") == service.to_markdown(document)
    assert "<h1>Jordan Smith</h1>" in html_path.read_text(encoding="utf-8")


async def test_generate_document_output_is_deterministic_for_fixed_script() -> None:
    blueprint = ResumePlanner().plan(SAMPLE_JOBS["backend_engineer"], sample_career_context())
    profile = sample_career_profile()
    service_a = ResumeGenerationService(make_llm_service([]))
    service_b = ResumeGenerationService(make_llm_service([]))
    doc_a = await service_a.generate_document(blueprint, profile, enhance_with_llm=False)
    doc_b = await service_b.generate_document(blueprint, profile, enhance_with_llm=False)
    assert service_a.to_markdown(doc_a) == service_b.to_markdown(doc_b)
