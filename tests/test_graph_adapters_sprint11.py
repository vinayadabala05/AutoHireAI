"""Unit tests for the Sprint 11 graph adapters: `ApplicationPlanningNode` and
`BrowserAutomationNode` (`app/graph/adapters/application_planning.py` and
`.../browser_automation.py`).
"""

from app.application_planning.package_builder import ApplicationPackageBuilder
from app.application_planning.service import ApplicationPlanningService
from app.browser_automation.models import FormFieldType, PortalType
from app.browser_automation.portal import GreenhouseAdapter
from app.browser_automation.service import BrowserAutomationService
from app.graph.adapters.application_planning import ApplicationPlanningNode
from app.graph.adapters.browser_automation import BrowserAutomationNode
from app.graph.context import ExecutionContext
from app.graph.executor import GraphExecutor
from app.graph.graph import Graph
from app.intelligence.resume_planner import ResumePlanner
from app.resume.service import ResumeGenerationService
from tests.browser_automation_fixtures import FakePage
from tests.cover_letter_fixtures import make_llm_service as make_cover_letter_llm_service
from tests.intelligence_fixtures import SAMPLE_JOBS, sample_career_context
from tests.job_discovery_fixtures import sample_job
from tests.resume_fixtures import make_llm_service, sample_career_profile


async def test_application_planning_node_produces_package() -> None:
    from app.cover_letter.service import CoverLetterGenerationService

    blueprint = ResumePlanner().plan(SAMPLE_JOBS["backend_engineer"], sample_career_context())
    builder = ApplicationPackageBuilder(
        ResumeGenerationService(make_llm_service([])),
        CoverLetterGenerationService(make_cover_letter_llm_service([])),
        enhance_with_llm=False,
    )
    service = ApplicationPlanningService(package_builder=builder)
    node = ApplicationPlanningNode("application_planning", service)

    context = ExecutionContext(
        graph_id="g",
        run_id="r",
        inputs={"job": sample_job(), "profile": sample_career_profile(), "blueprint": blueprint},
    )
    package = await node.execute(context)
    assert package.company == sample_job().company


async def test_browser_automation_node_submits_package() -> None:
    from app.cover_letter.service import CoverLetterGenerationService

    blueprint = ResumePlanner().plan(SAMPLE_JOBS["backend_engineer"], sample_career_context())
    builder = ApplicationPackageBuilder(
        ResumeGenerationService(make_llm_service([])),
        CoverLetterGenerationService(make_cover_letter_llm_service([])),
        enhance_with_llm=False,
    )
    package = await builder.build(sample_job(), sample_career_profile(), blueprint, "job-1")

    adapter = GreenhouseAdapter()
    page = FakePage()
    page.selector_counts[adapter._APPLY_BUTTON_SELECTOR] = 1  # noqa: SLF001
    page.selector_counts["text=Thank you for your interest"] = 1
    page.selector_counts[adapter.field_selectors[FormFieldType.RESUME_UPLOAD]] = 1
    page.selector_counts[adapter.field_selectors[FormFieldType.COVER_LETTER_UPLOAD]] = 1

    node = BrowserAutomationNode(
        "browser_automation", BrowserAutomationService(), PortalType.GREENHOUSE
    )
    context = ExecutionContext(
        graph_id="g",
        run_id="r",
        inputs={"application_planning": package, "page": page, "profile": sample_career_profile()},
    )
    result = await node.execute(context)
    assert result.status.value == "submitted"


async def test_two_node_dispatch_graph_runs_end_to_end() -> None:
    from app.cover_letter.service import CoverLetterGenerationService

    blueprint = ResumePlanner().plan(SAMPLE_JOBS["backend_engineer"], sample_career_context())
    builder = ApplicationPackageBuilder(
        ResumeGenerationService(make_llm_service([])),
        CoverLetterGenerationService(make_cover_letter_llm_service([])),
        enhance_with_llm=False,
    )
    planning_service = ApplicationPlanningService(package_builder=builder)

    adapter = GreenhouseAdapter()
    page = FakePage()
    page.selector_counts[adapter._APPLY_BUTTON_SELECTOR] = 1  # noqa: SLF001
    page.selector_counts["text=Thank you for your interest"] = 1
    page.selector_counts[adapter.field_selectors[FormFieldType.RESUME_UPLOAD]] = 1
    page.selector_counts[adapter.field_selectors[FormFieldType.COVER_LETTER_UPLOAD]] = 1

    graph = Graph("dispatch")
    graph.add_node(ApplicationPlanningNode("application_planning", planning_service))
    graph.add_node(
        BrowserAutomationNode(
            "browser_automation",
            BrowserAutomationService(),
            PortalType.GREENHOUSE,
            dependencies=["application_planning"],
        )
    )
    context = ExecutionContext(
        graph_id=graph.id,
        run_id="r1",
        inputs={
            "job": sample_job(),
            "profile": sample_career_profile(),
            "blueprint": blueprint,
            "page": page,
        },
    )
    state = await GraphExecutor().run(graph, context=context)
    assert state.status.value == "succeeded"
    result = context.get_output("browser_automation")
    assert result.status.value == "submitted"
