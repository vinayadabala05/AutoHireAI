"""Unit tests for `app.graph.graph.Graph`."""

import pytest

from app.graph.exceptions import CycleDetectedError, DuplicateNodeError, UnknownNodeError
from app.graph.graph import Graph
from app.graph.registry import NodeRegistry
from tests.graph_fixtures import EchoNode


def _linear_graph() -> Graph:
    graph = Graph("g1")
    graph.add_node(EchoNode("a"))
    graph.add_node(EchoNode("b", dependencies=["a"]))
    graph.add_node(EchoNode("c", dependencies=["b"]))
    return graph


def _diamond_graph() -> Graph:
    graph = Graph("diamond")
    graph.add_node(EchoNode("a"))
    graph.add_node(EchoNode("b", dependencies=["a"]))
    graph.add_node(EchoNode("c", dependencies=["a"]))
    graph.add_node(EchoNode("d", dependencies=["b", "c"]))
    return graph


def test_add_node_and_get_node() -> None:
    graph = Graph("g1")
    node = EchoNode("a")
    graph.add_node(node)
    assert graph.get_node("a") is node
    assert graph.has_node("a") is True
    assert "a" in graph


def test_add_duplicate_node_raises() -> None:
    graph = Graph("g1")
    graph.add_node(EchoNode("a"))
    with pytest.raises(DuplicateNodeError):
        graph.add_node(EchoNode("a"))


def test_get_unknown_node_raises() -> None:
    graph = Graph("g1")
    with pytest.raises(UnknownNodeError):
        graph.get_node("missing")


def test_add_node_with_dependencies_creates_edges() -> None:
    graph = _linear_graph()
    assert len(graph.edges) == 2
    edge_pairs = {(e.source, e.target) for e in graph.edges}
    assert ("a", "b") in edge_pairs
    assert ("b", "c") in edge_pairs


def test_add_edge_between_existing_nodes() -> None:
    graph = Graph("g1")
    graph.add_node(EchoNode("a"))
    graph.add_node(EchoNode("b"))
    graph.add_edge("a", "b")
    assert "a" in graph.get_node("b").dependencies
    assert len(graph.edges) == 1


def test_add_edge_is_idempotent() -> None:
    graph = Graph("g1")
    graph.add_node(EchoNode("a"))
    graph.add_node(EchoNode("b"))
    graph.add_edge("a", "b")
    graph.add_edge("a", "b")
    assert len(graph.edges) == 1


def test_add_edge_unknown_source_raises() -> None:
    graph = Graph("g1")
    graph.add_node(EchoNode("b"))
    with pytest.raises(UnknownNodeError):
        graph.add_edge("a", "b")


def test_add_edge_unknown_target_raises() -> None:
    graph = Graph("g1")
    graph.add_node(EchoNode("a"))
    with pytest.raises(UnknownNodeError):
        graph.add_edge("a", "b")


def test_dependents_of_returns_direct_dependents_sorted() -> None:
    graph = _diamond_graph()
    assert graph.dependents_of("a") == ["b", "c"]
    assert graph.dependents_of("d") == []


def test_validate_raises_for_dangling_dependency() -> None:
    graph = Graph("g1")
    graph.add_node(EchoNode("a", dependencies=["missing"]))
    with pytest.raises(UnknownNodeError):
        graph.validate()


def test_validate_passes_for_valid_dag() -> None:
    graph = _diamond_graph()
    graph.validate()  # should not raise


def test_detect_cycle_raises_with_cycle_path() -> None:
    graph = Graph("g1")
    graph.add_node(EchoNode("a"))
    graph.add_node(EchoNode("b", dependencies=["a"]))
    graph.add_edge("b", "a")  # b -> a creates a->b->a cycle (a depends on b too now)
    graph.get_node("a").dependencies.append("b")
    with pytest.raises(CycleDetectedError) as exc_info:
        graph.detect_cycle()
    assert "a" in exc_info.value.cycle or "b" in exc_info.value.cycle


def test_detect_cycle_passes_for_dag() -> None:
    graph = _diamond_graph()
    graph.detect_cycle()  # should not raise


def test_topological_order_respects_dependencies() -> None:
    graph = _diamond_graph()
    order = graph.topological_order()
    assert order.index("a") < order.index("b")
    assert order.index("a") < order.index("c")
    assert order.index("b") < order.index("d")
    assert order.index("c") < order.index("d")


def test_topological_order_is_deterministic() -> None:
    graph = _diamond_graph()
    assert graph.topological_order() == graph.topological_order()


def test_topological_order_raises_cycle_detected_error() -> None:
    graph = Graph("g1")
    graph.add_node(EchoNode("a"))
    graph.add_node(EchoNode("b", dependencies=["a"]))
    graph.get_node("a").dependencies.append("b")
    with pytest.raises(CycleDetectedError):
        graph.topological_order()


def test_topological_order_single_node() -> None:
    graph = Graph("g1")
    graph.add_node(EchoNode("a"))
    assert graph.topological_order() == ["a"]


def test_topological_order_empty_graph() -> None:
    graph = Graph("g1")
    assert graph.topological_order() == []


def test_serialize_contains_structure() -> None:
    graph = _linear_graph()
    data = graph.serialize()
    assert data["id"] == "g1"
    assert len(data["nodes"]) == 3
    assert len(data["edges"]) == 2
    assert data["nodes"][0]["type"] == "EchoNode"


def test_serialize_deserialize_round_trip() -> None:
    graph = _linear_graph()
    data = graph.serialize()

    registry = NodeRegistry()
    registry.register_node("EchoNode", EchoNode)

    restored = Graph.deserialize(data, registry)
    assert restored.id == graph.id
    assert set(restored.nodes) == set(graph.nodes)
    assert restored.topological_order() == graph.topological_order()


def test_len_and_repr() -> None:
    graph = _linear_graph()
    assert len(graph) == 3
    assert "g1" in repr(graph)
    assert "nodes=3" in repr(graph)


def test_graph_name_defaults_to_id() -> None:
    graph = Graph("g1")
    assert graph.name == "g1"


def test_nodes_and_edges_properties_return_copies() -> None:
    graph = _linear_graph()
    nodes_copy = graph.nodes
    nodes_copy["z"] = EchoNode("z")
    assert "z" not in graph.nodes
