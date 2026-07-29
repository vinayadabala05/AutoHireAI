"""Plugin registry for node types.

Mirrors `app.llm.registry`/`app.job_discovery.providers.base`'s
self-registration convention, generalized one step further: a registered
entry is a *factory* (`dict -> GraphNode`), not just a class, since some
nodes — notably the Sprint 8 adapters in `app/graph/adapters/`, which wrap
an already-constructed service instance — need more than the base
`GraphNode` fields to build. A plain `GraphNode` subclass with no extra
constructor requirements can be registered directly; `NodeRegistry` wraps
it in a factory automatically.
"""

from collections.abc import Callable
from typing import Any, cast

from app.graph.exceptions import NodeAlreadyRegisteredError, NodeNotFoundError
from app.graph.node import GraphNode

NodeFactory = Callable[[dict[str, Any]], GraphNode]


class NodeRegistry:
    """Register, look up, and discover node-type factories."""

    def __init__(self) -> None:
        self._factories: dict[str, NodeFactory] = {}

    def register_node(self, name: str, factory: NodeFactory | type[GraphNode]) -> None:
        """Register a factory (or a plain `GraphNode` subclass) under `name`."""
        if name in self._factories:
            raise NodeAlreadyRegisteredError(f"Node type '{name}' is already registered.")
        self._factories[name] = self._as_factory(factory)

    def remove_node(self, name: str) -> None:
        """Unregister `name`. A no-op if it was never registered."""
        self._factories.pop(name, None)

    def lookup_node(self, name: str) -> NodeFactory:
        """Look up the factory registered under `name`.

        Raises `NodeNotFoundError` if nothing is registered under that name.
        """
        try:
            return self._factories[name]
        except KeyError as exc:
            raise NodeNotFoundError(f"No node type registered under '{name}'.") from exc

    def discover_nodes(self) -> list[str]:
        """Return every currently registered node-type name, sorted."""
        return sorted(self._factories)

    def is_registered(self, name: str) -> bool:
        return name in self._factories

    def register(self, name: str) -> Callable[[type[GraphNode]], type[GraphNode]]:
        """Class decorator form: `@registry.register("my_node")`."""

        def decorator(node_cls: type[GraphNode]) -> type[GraphNode]:
            self.register_node(name, node_cls)
            return node_cls

        return decorator

    @staticmethod
    def _as_factory(factory_or_cls: NodeFactory | type[GraphNode]) -> NodeFactory:
        if isinstance(factory_or_cls, type) and issubclass(factory_or_cls, GraphNode):
            node_cls = factory_or_cls

            def factory(definition: dict[str, Any]) -> GraphNode:
                return node_cls(
                    node_id=definition["id"],
                    name=definition["name"],
                    description=definition.get("description", ""),
                    inputs=definition.get("inputs"),
                    outputs=definition.get("outputs"),
                    dependencies=definition.get("dependencies"),
                    metadata=definition.get("metadata"),
                    timeout_seconds=definition.get("timeout_seconds"),
                    optional=definition.get("optional", False),
                )

            return factory
        # `factory_or_cls` is a plain callable here — mypy can't fully narrow
        # the negation of `isinstance(..., type) and issubclass(..., GraphNode)`
        # against a `Callable` union member, so this cast just confirms what
        # the `if` branch above already established at runtime.
        return cast(NodeFactory, factory_or_cls)
