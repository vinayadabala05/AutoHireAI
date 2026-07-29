"""Unit tests for `app.graph.service.GraphService`."""

import pytest

from app.graph.checkpoint import InMemoryCheckpointStore
from app.graph.exceptions import GraphExecutionError
from app.graph.executor import ExecutionMode
from app.graph.graph import Graph
from app.graph.service import GraphService
from app.graph.state import ExecutionStatus
from tests.graph_fixtures import EchoNode, FailingNode


def _linear_graph() -> Graph:
    graph = Graph("g")
    graph.add_node(EchoNode("a"))
    graph.add_node(EchoNode("b", dependencies=["a"]))
    return graph


async def test_run_graph_executes_successfully() -> None:
    service = GraphService()
    state = await service.run_graph(_linear_graph())
    assert state.status is ExecutionStatus.SUCCEEDED


async def test_run_graph_supports_sequential_mode() -> None:
    service = GraphService()
    state = await service.run_graph(_linear_graph(), mode=ExecutionMode.SEQUENTIAL)
    assert state.status is ExecutionStatus.SUCCEEDED


def test_validate_graph_returns_valid_result_for_good_graph() -> None:
    service = GraphService()
    result = service.validate_graph(_linear_graph())
    assert result.is_valid is True
    assert result.errors == []


def test_validate_graph_returns_invalid_result_for_bad_graph() -> None:
    graph = Graph("g")
    graph.add_node(EchoNode("a", dependencies=["missing"]))
    service = GraphService()
    result = service.validate_graph(graph)
    assert result.is_valid is False
    assert len(result.errors) == 1


def test_plan_graph_returns_waves() -> None:
    service = GraphService()
    waves = service.plan_graph(_linear_graph())
    assert waves == [["a"], ["b"]]


def test_visualize_graph_mermaid() -> None:
    service = GraphService()
    output = service.visualize_graph(_linear_graph(), output_format="mermaid")
    assert "flowchart TD" in output


def test_visualize_graph_ascii() -> None:
    service = GraphService()
    output = service.visualize_graph(_linear_graph(), output_format="ascii")
    assert "[a]" in output


def test_visualize_graph_dependency_graph() -> None:
    service = GraphService()
    output = service.visualize_graph(_linear_graph(), output_format="dependency_graph")
    assert output == {"a": [], "b": ["a"]}


async def test_visualize_graph_execution_tree_requires_state() -> None:
    service = GraphService()
    with pytest.raises(ValueError, match="requires an ExecutionState"):
        service.visualize_graph(_linear_graph(), output_format="execution_tree")


async def test_visualize_graph_execution_tree_with_state() -> None:
    service = GraphService()
    graph = _linear_graph()
    state = await service.run_graph(graph)
    output = service.visualize_graph(graph, state=state, output_format="execution_tree")
    assert "succeeded" in output


def test_visualize_graph_unknown_format_raises() -> None:
    service = GraphService()
    with pytest.raises(ValueError, match="Unknown visualization output_format"):
        service.visualize_graph(_linear_graph(), output_format="svg")


async def test_resume_graph_via_service() -> None:
    service = GraphService()
    graph = Graph("g")
    graph.add_node(FailingNode("a"))
    with pytest.raises(GraphExecutionError) as exc_info:
        await service.run_graph(graph)
    fixed_graph = Graph("g")
    fixed_graph.add_node(EchoNode("a"))
    state = exc_info.value.state
    state.record_for("a").status = ExecutionStatus.PENDING
    resumed = await service.resume_graph(fixed_graph, state)
    assert resumed.status is ExecutionStatus.SUCCEEDED


async def test_checkpoint_store_integration() -> None:
    store = InMemoryCheckpointStore()
    service = GraphService(checkpoint_store=store)
    graph = _linear_graph()
    state = await service.run_graph(graph, checkpoint=True)
    assert store.list_checkpoints(graph.id) == [f"{graph.id}:{state.run_id}"]


def test_registry_is_accessible_and_usable() -> None:
    service = GraphService()
    service.registry.register_node("echo", EchoNode)
    assert service.registry.is_registered("echo") is True
