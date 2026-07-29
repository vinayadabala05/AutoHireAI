"""Resume Generation Service: the single entrypoint every caller should use.

Orchestrates `validator.py` -> `generator.py` -> `formatter.py`/`renderer.py`,
mirroring the same "one facade, no reaching for internals" convention as
`CareerProfileService` (Sprint 3.5) and `LLMService` (Sprint 4). Callers only
ever import `ResumeGenerationService`.
"""

from pathlib import Path

from app.career_profile.models import CareerProfile
from app.intelligence.models import ResumeBlueprint
from app.llm.service import LLMService
from app.resume.formatter import to_markdown
from app.resume.generator import ResumeGenerator
from app.resume.models import (
    ResumeDocument,
    ResumeTemplate,
    ResumeValidationError,
    ResumeValidationResult,
)
from app.resume.renderer import export_html_file, export_markdown_file, to_html
from app.resume.validator import ResumeValidator

_DEFAULT_EXPORT_DIR = Path("data/resumes")


class ResumeGenerationService:
    def __init__(self, llm_service: LLMService, export_dir: Path | None = None) -> None:
        self._generator = ResumeGenerator(llm_service)
        self._validator = ResumeValidator()
        self._export_dir = export_dir or _DEFAULT_EXPORT_DIR

    def validate_inputs(
        self, blueprint: ResumeBlueprint, profile: CareerProfile
    ) -> ResumeValidationResult:
        return self._validator.validate_inputs(blueprint, profile)

    async def generate_document(
        self,
        blueprint: ResumeBlueprint,
        profile: CareerProfile,
        template: ResumeTemplate = ResumeTemplate.SOFTWARE_ENGINEER,
        job_title: str | None = None,
        job_description: str = "",
        enhance_with_llm: bool = True,
        require_valid_inputs: bool = True,
    ) -> ResumeDocument:
        input_result = self.validate_inputs(blueprint, profile)
        if require_valid_inputs and not input_result.is_valid:
            raise ResumeValidationError(input_result)
        return await self._generator.generate(
            blueprint,
            profile,
            template=template,
            job_title=job_title,
            job_description=job_description,
            enhance_with_llm=enhance_with_llm,
        )

    def validate_document(self, document: ResumeDocument) -> ResumeValidationResult:
        return self._validator.validate_document(document)

    def to_markdown(self, document: ResumeDocument) -> str:
        return to_markdown(document)

    def to_html(self, document: ResumeDocument) -> str:
        return to_html(document, markdown=self.to_markdown(document))

    def export_markdown(self, document: ResumeDocument, path: Path | None = None) -> Path:
        markdown = self.to_markdown(document)
        return export_markdown_file(markdown, path or self._default_path(document, "md"))

    def export_html(self, document: ResumeDocument, path: Path | None = None) -> Path:
        markdown = self.to_markdown(document)
        return export_html_file(document, markdown, path or self._default_path(document, "html"))

    def _default_path(self, document: ResumeDocument, extension: str) -> Path:
        slug = document.full_name.strip().lower().replace(" ", "_") or "resume"
        return self._export_dir / f"{slug}_{document.template.value}.{extension}"
