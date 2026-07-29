"""Unit tests for `app.graph.edge.GraphEdge`."""

from app.graph.edge import GraphEdge


def test_edge_default_metadata_is_empty() -> None:
    edge = GraphEdge(source="a", target="b")
    assert edge.metadata == {}


def test_edge_equality_by_value() -> None:
    assert GraphEdge(source="a", target="b") == GraphEdge(source="a", target="b")
    assert GraphEdge(source="a", target="b") != GraphEdge(source="a", target="c")


def test_edge_is_hashable_and_usable_in_sets() -> None:
    edge_a = GraphEdge(source="a", target="b")
    edge_b = GraphEdge(source="a", target="b")
    assert len({edge_a, edge_b}) == 1
