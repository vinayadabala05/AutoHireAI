"""Unit tests for `app.graph.scheduler.GraphScheduler`."""

from app.graph.graph import Graph
from app.graph.scheduler import GraphScheduler
from tests.graph_fixtures import EchoNode


def _diamond_graph() -> Graph:
    graph = Graph("g")
    graph.add_node(EchoNode("a"))
    graph.add_node(EchoNode("b", dependencies=["a"]))
    graph.add_node(EchoNode("c", dependencies=["a"]))
    graph.add_node(EchoNode("d", dependencies=["b", "c"]))
    return graph


def test_initially_ready_nodes_have_no_dependencies() -> None:
    scheduler = GraphScheduler(_diamond_graph())
    assert scheduler.pop_ready() == "a"
    assert scheduler.has_ready() is False


def test_completing_a_node_unlocks_dependents() -> None:
    scheduler = GraphScheduler(_diamond_graph())
    scheduler.pop_ready()  # a
    scheduler.mark_complete("a")
    ready = scheduler.pop_all_ready()
    assert set(ready) == {"b", "c"}


def test_node_not_ready_until_all_dependencies_complete() -> None:
    scheduler = GraphScheduler(_diamond_graph())
    scheduler.pop_ready()  # a
    scheduler.mark_complete("a")
    scheduler.pop_ready()  # b or c
    assert scheduler.has_ready() is True  # the other of b/c
    remaining = scheduler.pop_ready()
    scheduler.mark_complete(remaining)
    assert scheduler.has_ready() is False  # d still waiting on the first of b/c


def test_priority_ordering_pops_highest_priority_first() -> None:
    graph = Graph("g")
    graph.add_node(EchoNode("low"))
    graph.add_node(EchoNode("high"))
    scheduler = GraphScheduler(graph, priorities={"low": 1, "high": 10})
    assert scheduler.pop_ready() == "high"
    assert scheduler.pop_ready() == "low"


def test_ties_broken_by_node_id() -> None:
    graph = Graph("g")
    graph.add_node(EchoNode("b"))
    graph.add_node(EchoNode("a"))
    scheduler = GraphScheduler(graph)
    assert scheduler.pop_ready() == "a"
    assert scheduler.pop_ready() == "b"


def test_pop_ready_returns_none_when_empty() -> None:
    graph = Graph("g")
    scheduler = GraphScheduler(graph)
    assert scheduler.pop_ready() is None


def test_pop_all_ready_drains_the_queue() -> None:
    graph = Graph("g")
    graph.add_node(EchoNode("a"))
    graph.add_node(EchoNode("b"))
    scheduler = GraphScheduler(graph)
    assert set(scheduler.pop_all_ready()) == {"a", "b"}
    assert scheduler.has_ready() is False


def test_completed_count_and_total_count() -> None:
    scheduler = GraphScheduler(_diamond_graph())
    assert scheduler.total_count == 4
    assert scheduler.completed_count == 0
    scheduler.mark_complete("a")
    assert scheduler.completed_count == 1


def test_is_exhausted_true_only_when_all_complete_and_queue_empty() -> None:
    graph = Graph("g")
    graph.add_node(EchoNode("a"))
    scheduler = GraphScheduler(graph)
    assert scheduler.is_exhausted is False  # "a" is ready but not completed
    scheduler.pop_ready()
    scheduler.mark_complete("a")
    assert scheduler.is_exhausted is True


def test_scheduler_with_no_nodes_is_immediately_exhausted() -> None:
    scheduler = GraphScheduler(Graph("g"))
    assert scheduler.is_exhausted is True
    assert scheduler.total_count == 0
