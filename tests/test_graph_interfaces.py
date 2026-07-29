"""Structural tests for `app.graph.interfaces`."""

from app.graph.checkpoint import InMemoryCheckpointStore
from app.graph.graph import Graph
from app.graph.interfaces import CheckpointStoreProtocol, GraphNodeProtocol, GraphVisualizerProtocol
from app.graph.visualizer import GraphVisualizer
from tests.graph_fixtures import EchoNode

_PROTOCOL_MEMBERS: dict[type, tuple[str, ...]] = {
    GraphNodeProtocol: (
        "id",
        "name",
        "dependencies",
        "validate",
        "prepare",
        "execute",
        "cleanup",
        "rollback",
    ),
    CheckpointStoreProtocol: ("save", "load", "list_checkpoints"),
    GraphVisualizerProtocol: ("to_mermaid", "to_ascii"),
}


def _satisfies(instance: object, protocol: type) -> bool:
    return all(hasattr(instance, member) for member in _PROTOCOL_MEMBERS[protocol])


def test_graph_node_satisfies_protocol() -> None:
    assert _satisfies(EchoNode("a"), GraphNodeProtocol)


def test_in_memory_checkpoint_store_satisfies_protocol() -> None:
    assert _satisfies(InMemoryCheckpointStore(), CheckpointStoreProtocol)


def test_graph_visualizer_satisfies_protocol() -> None:
    assert _satisfies(GraphVisualizer(Graph("g")), GraphVisualizerProtocol)
