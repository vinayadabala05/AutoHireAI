"""Adapter: wraps Sprint 5's `ResumeGenerationService` as a `GraphNode`.

Only wraps the existing service's public `generate_document()` method — no
change to `app.resume` at all.
"""

from typing import Any

from app.career_profile.models import CareerProfile
from app.graph.adapters._common import resolve_input
from app.graph.context import ExecutionContext
from app.graph.node import GraphNode
from app.intelligence.models import ResumeBlueprint
from app.resume.models import ResumeDocument, ResumeTemplate
from app.resume.service import ResumeGenerationService


class ResumeGeneratorNode(GraphNode):
    """Produces a `ResumeDocument` via `ResumeGenerationService.generate_document()`."""

    def __init__(
        self,
        node_id: str,
        service: ResumeGenerationService,
        *,
        name: str = "Resume Generator",
        blueprint_input: str = "blueprint",
        profile_input: str = "profile",
        template: ResumeTemplate = ResumeTemplate.SOFTWARE_ENGINEER,
        job_title_input: str = "job_title",
        job_description_input: str = "job_description",
        enhance_with_llm: bool = True,
        require_valid_inputs: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(node_id, name=name, **kwargs)
        self._service = service
        self._blueprint_input = blueprint_input
        self._profile_input = profile_input
        self._template = template
        self._job_title_input = job_title_input
        self._job_description_input = job_description_input
        self._enhance_with_llm = enhance_with_llm
        self._require_valid_inputs = require_valid_inputs

    async def execute(self, context: ExecutionContext) -> ResumeDocument:
        blueprint: ResumeBlueprint = resolve_input(context, self._blueprint_input)
        profile: CareerProfile = resolve_input(context, self._profile_input)
        job_title = resolve_input(context, self._job_title_input, required=False)
        job_description = resolve_input(context, self._job_description_input, required=False) or ""
        return await self._service.generate_document(
            blueprint,
            profile,
            template=self._template,
            job_title=job_title,
            job_description=job_description,
            enhance_with_llm=self._enhance_with_llm,
            require_valid_inputs=self._require_valid_inputs,
        )
