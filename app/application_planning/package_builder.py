"""Builds the resume + cover letter for a job the planner decided to APPLY to.

Reuses Sprint 8's Graph Orchestration Engine — wiring the same
`ResumeGeneratorNode`/`CoverLetterGeneratorNode` adapters Sprint 8 ships,
run through `GraphExecutor` exactly as Sprint 8's own integration test
demonstrates — rather than calling `ResumeGenerationService`/
`CoverLetterGenerationService` directly. This is a real, load-bearing use
of the graph engine (not decoration): the two-node pipeline gets retry/
timeout/tracing behavior for free, and a future third generation step
(e.g. a screening-question answerer) is one more node, not a rewrite.
"""

from datetime import UTC, datetime

from loguru import logger

from app.application_planning.exceptions import PackageBuildError
from app.application_planning.models import ApplicationPackage
from app.career_profile.models import CareerProfile
from app.cover_letter.models import CoverLetterTemplate
from app.cover_letter.service import CoverLetterGenerationService
from app.graph.adapters.cover_letter_generator import CoverLetterGeneratorNode
from app.graph.adapters.resume_generator import ResumeGeneratorNode
from app.graph.context import ExecutionContext
from app.graph.exceptions import GraphExecutionError
from app.graph.executor import GraphExecutor
from app.graph.graph import Graph
from app.intelligence.models import ResumeBlueprint
from app.job_discovery.models import DiscoveredJob
from app.resume.models import ResumeDocument, ResumeTemplate
from app.resume.service import ResumeGenerationService

_RESUME_NODE_ID = "resume"
_COVER_LETTER_NODE_ID = "cover_letter"


class ApplicationPackageBuilder:
    def __init__(
        self,
        resume_service: ResumeGenerationService,
        cover_letter_service: CoverLetterGenerationService,
        resume_template: ResumeTemplate = ResumeTemplate.SOFTWARE_ENGINEER,
        cover_letter_template: CoverLetterTemplate = CoverLetterTemplate.SOFTWARE_ENGINEER,
        enhance_with_llm: bool = True,
        executor: GraphExecutor | None = None,
    ) -> None:
        self._resume_service = resume_service
        self._cover_letter_service = cover_letter_service
        self._resume_template = resume_template
        self._cover_letter_template = cover_letter_template
        self._enhance_with_llm = enhance_with_llm
        self._executor = executor or GraphExecutor()

    async def build(
        self,
        job: DiscoveredJob,
        profile: CareerProfile,
        blueprint: ResumeBlueprint,
        job_id: str,
    ) -> ApplicationPackage:
        graph = self._build_graph(job_id)
        context = ExecutionContext(
            graph_id=graph.id,
            run_id=job_id,
            inputs={
                "blueprint": blueprint,
                "profile": profile,
                "job_title": job.title,
                "job_description": job.description,
                "company_name": job.company,
            },
        )
        try:
            await self._executor.run(graph, context=context)
        except GraphExecutionError as exc:
            logger.bind(job_id=job_id, company=job.company).error(
                "Failed to build application package: {}", exc
            )
            raise PackageBuildError(job_id, exc) from exc

        resume_document: ResumeDocument = context.get_output(_RESUME_NODE_ID)
        cover_letter_document = context.get_output(_COVER_LETTER_NODE_ID)

        package = ApplicationPackage(
            job_id=job_id,
            company=job.company,
            title=job.title,
            resume_document=resume_document,
            resume_markdown=self._resume_service.to_markdown(resume_document),
            cover_letter_document=cover_letter_document,
            cover_letter_markdown=self._cover_letter_service.to_markdown(cover_letter_document),
            application_url=job.source_url,
            generated_at=datetime.now(UTC),
        )
        logger.bind(job_id=job_id, company=job.company).info(
            "Built application package for '{}' at '{}'.", job.title, job.company
        )
        return package

    def _build_graph(self, job_id: str) -> Graph:
        graph = Graph(f"application_package_{job_id}")
        graph.add_node(
            ResumeGeneratorNode(
                _RESUME_NODE_ID,
                self._resume_service,
                template=self._resume_template,
                enhance_with_llm=self._enhance_with_llm,
            )
        )
        graph.add_node(
            CoverLetterGeneratorNode(
                _COVER_LETTER_NODE_ID,
                self._cover_letter_service,
                dependencies=[_RESUME_NODE_ID],
                resume_document_input=_RESUME_NODE_ID,
                template=self._cover_letter_template,
                enhance_with_llm=self._enhance_with_llm,
            )
        )
        return graph
