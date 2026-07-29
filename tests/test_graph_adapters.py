"""Unit tests for `app.graph.adapters` — wrapping Sprint 3-7 services as `GraphNode`s.

Each adapter is exercised against the real wrapped service class (using
existing sprint test fixtures/fakes — a scripted LLM provider, no real
network or database), proving the adapter only calls existing public
methods and correctly plumbs graph inputs/outputs.
"""

import uuid

import pytest

from app.cover_letter.service import CoverLetterGenerationService
from app.graph.adapters._common import resolve_input
from app.graph.adapters.career_profile import CareerProfileNode
from app.graph.adapters.cover_letter_generator import CoverLetterGeneratorNode
from app.graph.adapters.job_discovery import JobDiscoveryNode
from app.graph.adapters.resume_generator import ResumeGeneratorNode
from app.graph.adapters.resume_intelligence import ResumeIntelligenceNode
from app.graph.context import ExecutionContext
from app.graph.exceptions import GraphValidationError
from app.graph.executor import GraphExecutor
from app.graph.graph import Graph
from app.intelligence.resume_planner import ResumePlanner
from app.job_discovery.models import JobSearchQuery
from app.job_discovery.service import JobDiscoveryService
from app.resume.service import ResumeGenerationService
from tests.cover_letter_fixtures import make_llm_service as make_cover_letter_llm_service
from tests.cover_letter_fixtures import sample_blueprint as cover_letter_sample_blueprint
from tests.cover_letter_fixtures import sample_career_profile as cover_letter_sample_profile
from tests.cover_letter_fixtures import sample_resume_document
from tests.intelligence_fixtures import SAMPLE_JOBS, sample_career_context
from tests.resume_fixtures import make_llm_service, sample_career_profile


class _FakeCareerProfileService:
    def __init__(self) -> None:
        self.calls: list[uuid.UUID] = []

    async def build_profile(self, user_id: uuid.UUID):
        self.calls.append(user_id)
        return sample_career_profile()


def test_resolve_input_prefers_explicit_input_over_output() -> None:
    context = ExecutionContext(graph_id="g", run_id="r", inputs={"x": "input-value"})
    context.set_output("x", "output-value")
    assert resolve_input(context, "x") == "input-value"


def test_resolve_input_falls_back_to_output() -> None:
    context = ExecutionContext(graph_id="g", run_id="r")
    context.set_output("x", "output-value")
    assert resolve_input(context, "x") == "output-value"


def test_resolve_input_raises_when_required_and_missing() -> None:
    context = ExecutionContext(graph_id="g", run_id="r")
    with pytest.raises(GraphValidationError):
        resolve_input(context, "missing")


def test_resolve_input_returns_none_when_optional_and_missing() -> None:
    context = ExecutionContext(graph_id="g", run_id="r")
    assert resolve_input(context, "missing", required=False) is None


async def test_career_profile_node_calls_build_profile() -> None:
    service = _FakeCareerProfileService()
    node = CareerProfileNode("profile", service)  # type: ignore[arg-type]
    user_id = uuid.uuid4()
    context = ExecutionContext(graph_id="g", run_id="r", inputs={"user_id": str(user_id)})
    result = await node.execute(context)
    assert result.personal_info.full_name == "Jordan Smith"
    assert service.calls == [user_id]


async def test_career_profile_node_in_a_real_graph() -> None:
    service = _FakeCareerProfileService()
    graph = Graph("g")
    graph.add_node(CareerProfileNode("profile", service))  # type: ignore[arg-type]
    context = ExecutionContext(graph_id="g", run_id="r", inputs={"user_id": uuid.uuid4()})
    state = await GraphExecutor().run(graph, context=context)
    assert state.status.value == "succeeded"
    assert context.get_output("profile") is not None


async def test_resume_intelligence_node_produces_blueprint() -> None:
    node = ResumeIntelligenceNode("blueprint", ResumePlanner())
    context = ExecutionContext(
        graph_id="g",
        run_id="r",
        inputs={"job": SAMPLE_JOBS["backend_engineer"], "career_context": sample_career_context()},
    )
    blueprint = await node.execute(context)
    assert blueprint.match_score >= 0.0


async def test_resume_intelligence_node_uses_default_planner_when_none_given() -> None:
    node = ResumeIntelligenceNode("blueprint")
    context = ExecutionContext(
        graph_id="g",
        run_id="r",
        inputs={"job": SAMPLE_JOBS["ai_engineer"], "career_context": sample_career_context()},
    )
    blueprint = await node.execute(context)
    assert blueprint.resume_sections


async def test_resume_generator_node_produces_document() -> None:
    blueprint = ResumePlanner().plan(SAMPLE_JOBS["backend_engineer"], sample_career_context())
    profile = sample_career_profile()
    service = ResumeGenerationService(make_llm_service([]))
    node = ResumeGeneratorNode("resume", service, enhance_with_llm=False)
    context = ExecutionContext(
        graph_id="g", run_id="r", inputs={"blueprint": blueprint, "profile": profile}
    )
    document = await node.execute(context)
    assert document.full_name == "Jordan Smith"


async def test_resume_generator_node_reads_dependency_outputs() -> None:
    blueprint = ResumePlanner().plan(SAMPLE_JOBS["backend_engineer"], sample_career_context())
    profile = sample_career_profile()
    service = ResumeGenerationService(make_llm_service([]))

    graph = Graph("g")
    graph.add_node(ResumeGeneratorNode("resume", service, enhance_with_llm=False))
    context = ExecutionContext(graph_id="g", run_id="r")
    context.set_output("blueprint", blueprint)
    context.set_output("profile", profile)
    state = await GraphExecutor().run(graph, context=context)
    assert state.status.value == "succeeded"


async def test_cover_letter_generator_node_produces_document() -> None:
    profile = cover_letter_sample_profile()
    blueprint = cover_letter_sample_blueprint()
    resume_document = await sample_resume_document()
    service = CoverLetterGenerationService(make_cover_letter_llm_service([]))
    node = CoverLetterGeneratorNode("cover_letter", service, enhance_with_llm=False)
    context = ExecutionContext(
        graph_id="g",
        run_id="r",
        inputs={
            "profile": profile,
            "blueprint": blueprint,
            "resume_document": resume_document,
            "company_name": "Acme Corp",
            "job_title": "Backend Engineer",
        },
    )
    document = await node.execute(context)
    assert document.company_name == "Acme Corp"


async def test_job_discovery_node_returns_ranked_jobs() -> None:
    service = JobDiscoveryService(providers=[])
    node = JobDiscoveryNode("jobs", service)
    context = ExecutionContext(
        graph_id="g",
        run_id="r",
        inputs={"query": JobSearchQuery(), "profile": cover_letter_sample_profile()},
    )
    results = await node.execute(context)
    assert results == []


async def test_job_discovery_node_optional_inputs_default_to_none() -> None:
    service = JobDiscoveryService(providers=[])
    node = JobDiscoveryNode("jobs", service)
    context = ExecutionContext(
        graph_id="g",
        run_id="r",
        inputs={"query": JobSearchQuery(), "profile": cover_letter_sample_profile()},
    )
    await node.execute(context)  # should not raise despite no blueprint/criteria/preferences
