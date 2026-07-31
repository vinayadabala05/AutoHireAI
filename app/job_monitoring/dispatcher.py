"""`JobDispatcher`: triggers the existing pipeline for one matched job.

    Job -> Application Planning -> Resume Generation -> Cover Letter Generation
        -> Browser Automation

Resume/cover-letter generation already happens *inside* Sprint 9's
`ApplicationPlanningService.build_application_package()` (itself built on
Sprint 8's graph engine — see `app.application_planning.package_builder`),
so this dispatcher only has two stages of its own to wire: Application
Planning and Browser Automation. It wires them as a two-node Sprint 8
`Graph` (`ApplicationPlanningNode -> BrowserAutomationNode`,
`app/graph/adapters/`), so the hand-off between them gets retry/timeout/
tracing for free, exactly like Sprint 9's own package builder does for its
two stages.

The APPLY/SKIP decision itself is made *before* this class is even
invoked (via `ApplicationPlanningService.evaluate_job()`, which needs no
resume/cover-letter generation) — `JobDispatcher.dispatch()` assumes the
caller already decided to apply.
"""

from loguru import logger
from playwright.async_api import Page

from app.application_planning.service import ApplicationPlanningService
from app.browser_automation.browser import BrowserSession
from app.browser_automation.models import FormFillOptions, PortalType, SubmissionStatus
from app.browser_automation.service import BrowserAutomationService
from app.career_profile.models import CareerProfile
from app.graph.adapters.application_planning import ApplicationPlanningNode
from app.graph.adapters.browser_automation import BrowserAutomationNode
from app.graph.context import ExecutionContext
from app.graph.exceptions import GraphExecutionError
from app.graph.executor import GraphExecutor
from app.graph.graph import Graph
from app.intelligence.models import ResumeBlueprint
from app.job_discovery.deduplication import content_hash
from app.job_discovery.models import DiscoveredJob
from app.job_monitoring.exceptions import DispatchError
from app.job_monitoring.models import DispatchOutcome, ProcessingOutcome

_APPLICATION_PLANNING_NODE_ID = "application_planning"
_BROWSER_AUTOMATION_NODE_ID = "browser_automation"


class JobDispatcher:
    def __init__(
        self,
        planning_service: ApplicationPlanningService,
        browser_service: BrowserAutomationService,
        browser_session: BrowserSession,
        portal: PortalType,
        graph_executor: GraphExecutor | None = None,
    ) -> None:
        self._planning_service = planning_service
        self._browser_service = browser_service
        self._browser_session = browser_session
        self._portal = portal
        self._executor = graph_executor or GraphExecutor()

    async def dispatch(
        self,
        job: DiscoveredJob,
        profile: CareerProfile,
        blueprint: ResumeBlueprint | None = None,
        options: FormFillOptions | None = None,
        job_id: str | None = None,
    ) -> DispatchOutcome:
        job_id = job_id or content_hash(job)
        graph = self._build_graph(job_id)
        page: Page = await self._browser_session.new_page()
        try:
            context = ExecutionContext(
                graph_id=graph.id,
                run_id=job_id,
                inputs={
                    "job": job,
                    "profile": profile,
                    "blueprint": blueprint,
                    "job_id": job_id,
                    "page": page,
                    "options": options,
                },
            )
            await self._executor.run(graph, context=context)
            submission = context.get_output(_BROWSER_AUTOMATION_NODE_ID)

            outcome = (
                ProcessingOutcome.SUBMITTED
                if submission.status is SubmissionStatus.SUBMITTED
                else (
                    ProcessingOutcome.SUBMITTED
                    if submission.status is SubmissionStatus.PARTIAL
                    else ProcessingOutcome.FAILED
                )
            )
            logger.bind(job_id=job_id, company=job.company).info(
                "Dispatched job: {} ({})", outcome.value, submission.status.value
            )
            return DispatchOutcome(
                outcome=outcome,
                submission_status=submission.status,
                application_url=submission.application_url,
                error_message=submission.error_message,
            )
        except GraphExecutionError as exc:
            logger.bind(job_id=job_id, company=job.company).error("Dispatch failed: {}", exc)
            raise DispatchError(job_id, exc) from exc
        finally:
            await page.close()

    def _build_graph(self, job_id: str) -> Graph:
        graph = Graph(f"job_dispatch_{job_id}")
        graph.add_node(
            ApplicationPlanningNode(_APPLICATION_PLANNING_NODE_ID, self._planning_service)
        )
        graph.add_node(
            BrowserAutomationNode(
                _BROWSER_AUTOMATION_NODE_ID,
                self._browser_service,
                self._portal,
                dependencies=[_APPLICATION_PLANNING_NODE_ID],
            )
        )
        return graph
