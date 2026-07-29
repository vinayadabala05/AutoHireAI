"""Unit tests for `app.graph.context.ExecutionContext`."""

from app.graph.context import ExecutionContext
from app.graph.memory import GraphMemory


def test_get_input_returns_value_or_default() -> None:
    context = ExecutionContext(graph_id="g", run_id="r", inputs={"x": 1})
    assert context.get_input("x") == 1
    assert context.get_input("missing", "default") == "default"


def test_set_and_get_output_proxies_to_memory() -> None:
    context = ExecutionContext(graph_id="g", run_id="r")
    context.set_output("node_a", "value")
    assert context.get_output("node_a") == "value"
    assert context.memory.get_output("node_a") == "value"


def test_cancel_sets_is_cancelled() -> None:
    context = ExecutionContext(graph_id="g", run_id="r")
    assert context.is_cancelled is False
    context.cancel()
    assert context.is_cancelled is True


def test_context_defaults_to_empty_inputs_and_fresh_memory() -> None:
    context = ExecutionContext(graph_id="g", run_id="r")
    assert context.inputs == {}
    assert isinstance(context.memory, GraphMemory)


def test_context_can_be_constructed_with_shared_memory() -> None:
    memory = GraphMemory()
    memory.set_output("preexisting", 1)
    context = ExecutionContext(graph_id="g", run_id="r", memory=memory)
    assert context.get_output("preexisting") == 1


def test_context_carries_graph_and_run_id() -> None:
    context = ExecutionContext(graph_id="g1", run_id="r1")
    assert context.graph_id == "g1"
    assert context.run_id == "r1"
