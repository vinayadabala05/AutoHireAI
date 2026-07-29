"""Unit tests for `app.graph.planner.ExecutionPlanner`."""

import pytest

from app.graph.exceptions import CycleDetectedError
from app.graph.graph import Graph
from app.graph.planner import ExecutionPlanner
from tests.graph_fixtures import EchoNode


def test_plan_groups_independent_nodes_into_one_wave() -> None:
    graph = Graph("g")
    graph.add_node(EchoNode("a"))
    graph.add_node(EchoNode("b", dependencies=["a"]))
    graph.add_node(EchoNode("c", dependencies=["a"]))
    graph.add_node(EchoNode("d", dependencies=["b", "c"]))
    waves = ExecutionPlanner().plan(graph)
    assert waves == [["a"], ["b", "c"], ["d"]]


def test_plan_single_node() -> None:
    graph = Graph("g")
    graph.add_node(EchoNode("a"))
    assert ExecutionPlanner().plan(graph) == [["a"]]


def test_plan_empty_graph() -> None:
    graph = Graph("g")
    assert ExecutionPlanner().plan(graph) == []


def test_plan_fully_independent_nodes_single_wave() -> None:
    graph = Graph("g")
    graph.add_node(EchoNode("a"))
    graph.add_node(EchoNode("b"))
    graph.add_node(EchoNode("c"))
    assert ExecutionPlanner().plan(graph) == [["a", "b", "c"]]


def test_plan_raises_on_cycle() -> None:
    graph = Graph("g")
    graph.add_node(EchoNode("a"))
    graph.add_node(EchoNode("b", dependencies=["a"]))
    graph.get_node("a").dependencies.append("b")
    with pytest.raises(CycleDetectedError):
        ExecutionPlanner().plan(graph)


def test_flatten_returns_valid_topological_order() -> None:
    graph = Graph("g")
    graph.add_node(EchoNode("a"))
    graph.add_node(EchoNode("b", dependencies=["a"]))
    graph.add_node(EchoNode("c", dependencies=["a"]))
    flat = ExecutionPlanner().flatten(graph)
    assert flat.index("a") < flat.index("b")
    assert flat.index("a") < flat.index("c")
    assert set(flat) == {"a", "b", "c"}
