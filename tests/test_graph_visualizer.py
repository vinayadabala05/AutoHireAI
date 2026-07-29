"""Unit tests for `app.graph.visualizer.GraphVisualizer`."""

from app.graph.executor import GraphExecutor
from app.graph.graph import Graph
from app.graph.state import ExecutionState, ExecutionStatus
from app.graph.visualizer import GraphVisualizer
from tests.graph_fixtures import EchoNode


def _linear_graph() -> Graph:
    graph = Graph("g")
    graph.add_node(EchoNode("a", name="Node A"))
    graph.add_node(EchoNode("b", name="Node B", dependencies=["a"]))
    return graph


def test_dependency_graph_returns_adjacency_dict() -> None:
    visualizer = GraphVisualizer(_linear_graph())
    assert visualizer.dependency_graph() == {"a": [], "b": ["a"]}


def test_to_mermaid_includes_nodes_and_edges() -> None:
    mermaid = GraphVisualizer(_linear_graph()).to_mermaid()
    assert "flowchart TD" in mermaid
    assert 'a["Node A"]' in mermaid
    assert 'b["Node B"]' in mermaid
    assert "a --> b" in mermaid


def test_to_mermaid_escapes_double_quotes_in_names() -> None:
    graph = Graph("g")
    graph.add_node(EchoNode("a", name='Say "hi"'))
    mermaid = GraphVisualizer(graph).to_mermaid()
    assert "Say 'hi'" in mermaid


def test_to_mermaid_applies_status_styling_when_state_given() -> None:
    graph = _linear_graph()
    state = ExecutionState(run_id="r", graph_id="g")
    state.record_for("a").status = ExecutionStatus.SUCCEEDED
    state.record_for("b").status = ExecutionStatus.FAILED
    mermaid = GraphVisualizer(graph).to_mermaid(state)
    assert "style a" in mermaid
    assert "style b" in mermaid


def test_to_mermaid_without_state_has_no_style_lines() -> None:
    mermaid = GraphVisualizer(_linear_graph()).to_mermaid()
    assert "style" not in mermaid


def test_to_ascii_lists_nodes_in_topological_order_with_deps() -> None:
    ascii_output = GraphVisualizer(_linear_graph()).to_ascii()
    lines = ascii_output.splitlines()
    assert lines[0].startswith("[a]")
    assert "(deps: -)" in lines[0]
    assert "(deps: a)" in lines[1]


async def test_execution_tree_shows_depth_status_and_duration() -> None:
    graph = _linear_graph()
    state = await GraphExecutor().run(graph)
    tree = GraphVisualizer(graph).execution_tree(state)
    lines = tree.splitlines()
    assert lines[0].startswith("- a")
    assert lines[1].startswith("  - b")
    assert "succeeded" in tree


def test_execution_tree_handles_missing_record_as_pending() -> None:
    graph = _linear_graph()
    state = ExecutionState(run_id="r", graph_id="g")
    tree = GraphVisualizer(graph).execution_tree(state)
    assert "[pending]" in tree
