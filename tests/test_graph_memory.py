"""Unit tests for `app.graph.memory.GraphMemory`."""

from app.graph.memory import GraphMemory


def test_set_and_get_output() -> None:
    memory = GraphMemory()
    memory.set_output("a", 42)
    assert memory.get_output("a") == 42


def test_get_output_default_when_absent() -> None:
    memory = GraphMemory()
    assert memory.get_output("missing", "fallback") == "fallback"
    assert memory.get_output("missing") is None


def test_has_output() -> None:
    memory = GraphMemory()
    assert memory.has_output("a") is False
    memory.set_output("a", None)
    assert memory.has_output("a") is True


def test_set_output_appends_to_history() -> None:
    memory = GraphMemory()
    memory.set_output("a", 1)
    memory.set_output("b", 2)
    assert len(memory.history) == 2
    assert "a" in memory.history[0]


def test_shared_scratch_space() -> None:
    memory = GraphMemory()
    memory.set_shared("key", "value")
    assert memory.get_shared("key") == "value"
    assert memory.get_shared("missing", "default") == "default"


def test_memory_instances_are_independent() -> None:
    memory_a = GraphMemory()
    memory_b = GraphMemory()
    memory_a.set_output("x", 1)
    assert memory_b.has_output("x") is False
