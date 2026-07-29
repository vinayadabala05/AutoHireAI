"""Unit tests for `app.graph.registry.NodeRegistry`."""

import pytest

from app.graph.exceptions import NodeAlreadyRegisteredError, NodeNotFoundError
from app.graph.registry import NodeRegistry
from tests.graph_fixtures import EchoNode


def test_register_and_lookup_node_class() -> None:
    registry = NodeRegistry()
    registry.register_node("echo", EchoNode)
    factory = registry.lookup_node("echo")
    node = factory({"id": "a", "name": "A", "dependencies": []})
    assert isinstance(node, EchoNode)
    assert node.id == "a"


def test_register_node_with_explicit_factory() -> None:
    registry = NodeRegistry()

    def factory(definition: dict) -> EchoNode:
        return EchoNode(definition["id"], result="custom")

    registry.register_node("custom_echo", factory)
    node = registry.lookup_node("custom_echo")({"id": "x"})
    assert isinstance(node, EchoNode)


def test_register_duplicate_name_raises() -> None:
    registry = NodeRegistry()
    registry.register_node("echo", EchoNode)
    with pytest.raises(NodeAlreadyRegisteredError):
        registry.register_node("echo", EchoNode)


def test_lookup_unknown_name_raises() -> None:
    registry = NodeRegistry()
    with pytest.raises(NodeNotFoundError):
        registry.lookup_node("missing")


def test_remove_node() -> None:
    registry = NodeRegistry()
    registry.register_node("echo", EchoNode)
    registry.remove_node("echo")
    assert registry.is_registered("echo") is False


def test_remove_unknown_node_is_a_no_op() -> None:
    registry = NodeRegistry()
    registry.remove_node("missing")  # should not raise


def test_discover_nodes_returns_sorted_names() -> None:
    registry = NodeRegistry()
    registry.register_node("zeta", EchoNode)
    registry.register_node("alpha", EchoNode)
    assert registry.discover_nodes() == ["alpha", "zeta"]


def test_is_registered() -> None:
    registry = NodeRegistry()
    assert registry.is_registered("echo") is False
    registry.register_node("echo", EchoNode)
    assert registry.is_registered("echo") is True


def test_register_decorator_form() -> None:
    registry = NodeRegistry()

    @registry.register("decorated_echo")
    class DecoratedEcho(EchoNode):
        pass

    assert registry.is_registered("decorated_echo") is True
    node = registry.lookup_node("decorated_echo")({"id": "a", "name": "A"})
    assert isinstance(node, DecoratedEcho)


def test_factory_from_class_passes_through_all_base_fields() -> None:
    registry = NodeRegistry()
    registry.register_node("echo", EchoNode)
    node = registry.lookup_node("echo")(
        {
            "id": "a",
            "name": "A",
            "description": "d",
            "inputs": ["i"],
            "outputs": ["o"],
            "dependencies": ["dep"],
            "metadata": {"k": "v"},
            "timeout_seconds": 10.0,
            "optional": True,
        }
    )
    assert node.description == "d"
    assert node.inputs == ["i"]
    assert node.dependencies == ["dep"]
    assert node.optional is True
