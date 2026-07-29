"""Cover Letter Generation Service: the single entrypoint every caller should use.

Orchestrates `validator.py` -> `generator.py` -> `formatter.py`/`renderer.py`,
mirroring `ResumeGenerationService` (Sprint 5) and `CareerProfileService`
(Sprint 3.5): callers only ever import `CoverLetterGenerationService`.
"""

from pathlib import Path

from app.career_profile.models import CareerProfile
from app.cover_letter.formatter import to_markdown
from app.cover_letter.generator import CoverLetterGenerator
from app.cover_letter.models import (
    CoverLetterDocument,
    CoverLetterTemplate,
    CoverLetterValidationError,
    CoverLetterValidationResult,
)
from app.cover_letter.renderer import export_html_file, export_markdown_file, to_html
from app.cover_letter.validator import CoverLetterValidator
from app.intelligence.models import ResumeBlueprint
from app.llm.service import LLMService
from app.resume.models import ResumeDocument

_DEFAULT_EXPORT_DIR = Path("data/cover_letters")


class CoverLetterGenerationService:
    def __init__(self, llm_service: LLMService, export_dir: Path | None = None) -> None:
        self._generator = CoverLetterGenerator(llm_service)
        self._validator = CoverLetterValidator()
        self._export_dir = export_dir or _DEFAULT_EXPORT_DIR

    def validate_inputs(
        self,
        profile: CareerProfile,
        blueprint: ResumeBlueprint,
        resume_document: ResumeDocument,
        company_name: str,
        job_title: str,
    ) -> CoverLetterValidationResult:
        return self._validator.validate_inputs(
            profile, blueprint, resume_document, company_name, job_title
        )

    async def generate_document(
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
        require_valid_inputs: bool = True,
    ) -> CoverLetterDocument:
        input_result = self.validate_inputs(
            profile, blueprint, resume_document, company_name, job_title
        )
        if require_valid_inputs and not input_result.is_valid:
            raise CoverLetterValidationError(input_result)
        return await self._generator.generate(
            profile,
            blueprint,
            resume_document,
            company_name,
            job_title,
            job_description=job_description,
            template=template,
            hiring_manager=hiring_manager,
            enhance_with_llm=enhance_with_llm,
        )

    def validate_document(self, document: CoverLetterDocument) -> CoverLetterValidationResult:
        return self._validator.validate_document(document)

    def to_markdown(self, document: CoverLetterDocument) -> str:
        return to_markdown(document)

    def to_html(self, document: CoverLetterDocument) -> str:
        return to_html(document, markdown=self.to_markdown(document))

    def export_markdown(self, document: CoverLetterDocument, path: Path | None = None) -> Path:
        markdown = self.to_markdown(document)
        return export_markdown_file(markdown, path or self._default_path(document, "md"))

    def export_html(self, document: CoverLetterDocument, path: Path | None = None) -> Path:
        markdown = self.to_markdown(document)
        return export_html_file(document, markdown, path or self._default_path(document, "html"))

    def _default_path(self, document: CoverLetterDocument, extension: str) -> Path:
        slug = document.full_name.strip().lower().replace(" ", "_") or "cover_letter"
        company_slug = document.company_name.strip().lower().replace(" ", "_") or "company"
        return self._export_dir / f"{slug}_{company_slug}_{document.template.value}.{extension}"
