"""End-to-end integration test: a real multi-adapter pipeline as one `Graph`.

Wires `ResumeIntelligenceNode -> ResumeGeneratorNode -> CoverLetterGeneratorNode`
into a single DAG and runs it through `GraphExecutor`, proving adapters
compose via dependency-driven context plumbing exactly like any other
`GraphNode` — no special-casing needed for "real" sprint-derived nodes.
"""

from app.cover_letter.service import CoverLetterGenerationService
from app.graph.adapters.cover_letter_generator import CoverLetterGeneratorNode
from app.graph.adapters.resume_generator import ResumeGeneratorNode
from app.graph.adapters.resume_intelligence import ResumeIntelligenceNode
from app.graph.context import ExecutionContext
from app.graph.executor import ExecutionMode, GraphExecutor
from app.graph.graph import Graph
from app.graph.state import ExecutionStatus
from app.intelligence.resume_planner import ResumePlanner
from app.resume.service import ResumeGenerationService
from tests.cover_letter_fixtures import make_llm_service as make_cover_letter_llm_service
from tests.intelligence_fixtures import SAMPLE_JOBS, sample_career_context
from tests.resume_fixtures import make_llm_service, sample_career_profile


def _build_pipeline_graph() -> Graph:
    resume_service = ResumeGenerationService(make_llm_service([]))
    cover_letter_service = CoverLetterGenerationService(make_cover_letter_llm_service([]))

    graph = Graph("job_application_pipeline")
    graph.add_node(ResumeIntelligenceNode("blueprint", ResumePlanner()))
    graph.add_node(
        ResumeGeneratorNode(
            "resume", resume_service, dependencies=["blueprint"], enhance_with_llm=False
        )
    )
    graph.add_node(
        CoverLetterGeneratorNode(
            "cover_letter",
            cover_letter_service,
            dependencies=["blueprint", "resume"],
            resume_document_input="resume",
            enhance_with_llm=False,
        )
    )
    return graph


async def test_full_pipeline_executes_successfully() -> None:
    graph = _build_pipeline_graph()
    context = ExecutionContext(
        graph_id=graph.id,
        run_id="r1",
        inputs={
            "job": SAMPLE_JOBS["backend_engineer"],
            "career_context": sample_career_context(),
            "profile": sample_career_profile(),
            "company_name": "Acme Corp",
            "job_title": "Backend Engineer",
        },
    )
    state = await GraphExecutor().run(graph, context=context, mode=ExecutionMode.PARALLEL)

    assert state.status is ExecutionStatus.SUCCEEDED
    assert set(state.succeeded_node_ids) == {"blueprint", "resume", "cover_letter"}

    resume_document = context.get_output("resume")
    cover_letter_document = context.get_output("cover_letter")
    assert resume_document.full_name == "Jordan Smith"
    assert cover_letter_document.company_name == "Acme Corp"
    assert cover_letter_document.job_title == "Backend Engineer"


async def test_full_pipeline_executes_sequentially_with_same_result() -> None:
    graph = _build_pipeline_graph()
    context = ExecutionContext(
        graph_id=graph.id,
        run_id="r2",
        inputs={
            "job": SAMPLE_JOBS["ai_engineer"],
            "career_context": sample_career_context(),
            "profile": sample_career_profile(),
            "company_name": "Ex Corp",
            "job_title": "AI Engineer",
        },
    )
    state = await GraphExecutor().run(graph, context=context, mode=ExecutionMode.SEQUENTIAL)
    assert state.status is ExecutionStatus.SUCCEEDED


def test_pipeline_visualizes_as_mermaid() -> None:
    from app.graph.visualizer import GraphVisualizer

    graph = _build_pipeline_graph()
    mermaid = GraphVisualizer(graph).to_mermaid()
    assert "blueprint --> resume" in mermaid
    assert "blueprint --> cover_letter" in mermaid
    assert "resume --> cover_letter" in mermaid
