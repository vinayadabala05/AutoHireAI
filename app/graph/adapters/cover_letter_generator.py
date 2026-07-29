"""Adapter: wraps Sprint 6's `CoverLetterGenerationService` as a `GraphNode`.

Only wraps the existing service's public `generate_document()` method — no
change to `app.cover_letter` at all.
"""

from typing import Any

from app.career_profile.models import CareerProfile
from app.cover_letter.models import CoverLetterDocument, CoverLetterTemplate
from app.cover_letter.service import CoverLetterGenerationService
from app.graph.adapters._common import resolve_input
from app.graph.context import ExecutionContext
from app.graph.node import GraphNode
from app.intelligence.models import ResumeBlueprint
from app.resume.models import ResumeDocument


class CoverLetterGeneratorNode(GraphNode):
    """Produces a `CoverLetterDocument` via `CoverLetterGenerationService.generate_document()`."""

    def __init__(
        self,
        node_id: str,
        service: CoverLetterGenerationService,
        *,
        name: str = "Cover Letter Generator",
        profile_input: str = "profile",
        blueprint_input: str = "blueprint",
        resume_document_input: str = "resume_document",
        company_name_input: str = "company_name",
        job_title_input: str = "job_title",
        job_description_input: str = "job_description",
        template: CoverLetterTemplate = CoverLetterTemplate.SOFTWARE_ENGINEER,
        hiring_manager_input: str = "hiring_manager",
        enhance_with_llm: bool = True,
        require_valid_inputs: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(node_id, name=name, **kwargs)
        self._service = service
        self._profile_input = profile_input
        self._blueprint_input = blueprint_input
        self._resume_document_input = resume_document_input
        self._company_name_input = company_name_input
        self._job_title_input = job_title_input
        self._job_description_input = job_description_input
        self._template = template
        self._hiring_manager_input = hiring_manager_input
        self._enhance_with_llm = enhance_with_llm
        self._require_valid_inputs = require_valid_inputs

    async def execute(self, context: ExecutionContext) -> CoverLetterDocument:
        profile: CareerProfile = resolve_input(context, self._profile_input)
        blueprint: ResumeBlueprint = resolve_input(context, self._blueprint_input)
        resume_document: ResumeDocument = resolve_input(context, self._resume_document_input)
        company_name: str = resolve_input(context, self._company_name_input)
        job_title: str = resolve_input(context, self._job_title_input)
        job_description = resolve_input(context, self._job_description_input, required=False) or ""
        hiring_manager = resolve_input(context, self._hiring_manager_input, required=False)
        return await self._service.generate_document(
            profile,
            blueprint,
            resume_document,
            company_name,
            job_title,
            job_description=job_description,
            template=self._template,
            hiring_manager=hiring_manager,
            enhance_with_llm=self._enhance_with_llm,
            require_valid_inputs=self._require_valid_inputs,
        )
