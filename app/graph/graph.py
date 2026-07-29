"""The core `Graph`: a directed acyclic graph of `GraphNode`s.

Supports dependency resolution (nodes declare `dependencies`, edges are
derived automatically — or added explicitly via `add_edge`), topological
ordering (Kahn's algorithm, deterministic via a min-heap so the same graph
always yields the same order), cycle detection (with a human-readable
cycle path in the error), structural validation, and JSON-serializable
(de)serialization of graph *structure* — see `NodeRegistry` (`registry.py`)
for how node behavior is reconstructed on deserialization.
"""

import heapq
from typing import TYPE_CHECKING, Any

from app.graph.edge import GraphEdge
from app.graph.exceptions import CycleDetectedError, DuplicateNodeError, UnknownNodeError
from app.graph.node import GraphNode

if TYPE_CHECKING:
    from app.graph.registry import NodeRegistry


class Graph:
    def __init__(self, graph_id: str, name: str = "", description: str = "") -> None:
        self.id = graph_id
        self.name = name or graph_id
        self.description = description
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []

    @property
    def nodes(self) -> dict[str, GraphNode]:
        return dict(self._nodes)

    @property
    def edges(self) -> list[GraphEdge]:
        return list(self._edges)

    def add_node(self, node: GraphNode) -> "Graph":
        if node.id in self._nodes:
            raise DuplicateNodeError(f"Node '{node.id}' already exists in graph '{self.id}'.")
        self._nodes[node.id] = node
        for dependency in node.dependencies:
            self._edges.append(GraphEdge(source=dependency, target=node.id))
        return self

    def add_edge(self, source: str, target: str) -> "Graph":
        """Add an explicit dependency edge. Both nodes must already be in the graph."""
        if source not in self._nodes:
            raise UnknownNodeError(f"Cannot add edge: unknown source node '{source}'.")
        if target not in self._nodes:
            raise UnknownNodeError(f"Cannot add edge: unknown target node '{target}'.")
        edge = GraphEdge(source=source, target=target)
        if edge not in self._edges:
            self._edges.append(edge)
        target_node = self._nodes[target]
        if source not in target_node.dependencies:
            target_node.dependencies.append(source)
        return self

    def get_node(self, node_id: str) -> GraphNode:
        try:
            return self._nodes[node_id]
        except KeyError as exc:
            raise UnknownNodeError(f"Graph '{self.id}' has no node '{node_id}'.") from exc

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    def dependents_of(self, node_id: str) -> list[str]:
        """Node ids that directly depend on `node_id`."""
        return sorted(n.id for n in self._nodes.values() if node_id in n.dependencies)

    def _children_map(self) -> dict[str, list[str]]:
        children: dict[str, list[str]] = {node_id: [] for node_id in self._nodes}
        for node in self._nodes.values():
            for dependency in node.dependencies:
                if dependency not in self._nodes:
                    raise UnknownNodeError(
                        f"Node '{node.id}' depends on unknown node '{dependency}'."
                    )
                children[dependency].append(node.id)
        return children

    def validate(self) -> None:
        """Raises `UnknownNodeError` for a dangling dependency or `CycleDetectedError`."""
        self._children_map()  # raises UnknownNodeError as a side effect
        self.detect_cycle()

    def detect_cycle(self) -> None:
        """Raises `CycleDetectedError` (with the cycle path) if the graph isn't a DAG."""
        children = self._children_map()
        WHITE, GRAY, BLACK = 0, 1, 2
        color = dict.fromkeys(self._nodes, WHITE)
        path: list[str] = []

        def visit(node_id: str) -> None:
            color[node_id] = GRAY
            path.append(node_id)
            for child in children[node_id]:
                if color[child] == GRAY:
                    cycle_start = path.index(child)
                    raise CycleDetectedError(path[cycle_start:])
                if color[child] == WHITE:
                    visit(child)
            path.pop()
            color[node_id] = BLACK

        for node_id in sorted(self._nodes):
            if color[node_id] == WHITE:
                visit(node_id)

    def topological_order(self) -> list[str]:
        """Kahn's algorithm. Deterministic (ties broken by node id) and DAG-verifying."""
        children = self._children_map()
        in_degree = {node_id: 0 for node_id in self._nodes}
        for node in self._nodes.values():
            in_degree[node.id] = len(node.dependencies)

        ready = [node_id for node_id, degree in in_degree.items() if degree == 0]
        heapq.heapify(ready)
        order: list[str] = []

        while ready:
            current = heapq.heappop(ready)
            order.append(current)
            for child in children[current]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    heapq.heappush(ready, child)

        if len(order) != len(self._nodes):
            self.detect_cycle()  # raises with a precise cycle path
            raise CycleDetectedError(order)  # pragma: no cover - detect_cycle always raises first

        return order

    def serialize(self) -> dict[str, Any]:
        """JSON-serializable graph *structure* (node definitions + edges).

        Node behavior (the concrete `execute()` logic, and any constructor
        arguments beyond `GraphNode`'s base fields, such as an adapter's
        wrapped service instance) is intentionally not serialized here —
        see `NodeRegistry`/`deserialize` for how it's reconstructed.
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "nodes": [node.to_definition_dict() for node in self._nodes.values()],
            "edges": [edge.model_dump() for edge in self._edges],
        }

    @classmethod
    def deserialize(cls, data: dict[str, Any], registry: "NodeRegistry") -> "Graph":
        """Rebuild a `Graph` from `serialize()` output using a `NodeRegistry`.

        Each node definition's `"type"` is looked up in `registry` to
        obtain a factory that reconstructs a live `GraphNode` instance from
        the definition dict.
        """
        graph = cls(
            graph_id=data["id"], name=data.get("name", ""), description=data.get("description", "")
        )
        for node_def in data["nodes"]:
            factory = registry.lookup_node(node_def["type"])
            graph.add_node(factory(node_def))
        for edge_data in data["edges"]:
            graph.add_edge(edge_data["source"], edge_data["target"])
        return graph

    def __len__(self) -> int:
        return len(self._nodes)

    def __contains__(self, node_id: str) -> bool:
        return node_id in self._nodes

    def __repr__(self) -> str:
        return f"<Graph id={self.id!r} nodes={len(self._nodes)} edges={len(self._edges)}>"
