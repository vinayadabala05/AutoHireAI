"""Structural interfaces for the Graph Orchestration Engine.

Every concrete class in this package satisfies one of these `Protocol`s.
`GraphNodeProtocol` is the extension point every adapter (`adapters/`) and
every future first-class node implements — `registry.py`, `planner.py`,
and `executor.py` only ever depend on this shape, never on a concrete
node subclass.
"""

from typing import Any, Protocol

from app.graph.context import ExecutionContext
from app.graph.state import ExecutionState


class GraphNodeProtocol(Protocol):
    id: str
    name: str
    dependencies: list[str]

    async def validate(self, context: ExecutionContext) -> None: ...
    async def prepare(self, context: ExecutionContext) -> None: ...
    async def execute(self, context: ExecutionContext) -> Any: ...
    async def cleanup(self, context: ExecutionContext) -> None: ...
    async def rollback(self, context: ExecutionContext) -> None: ...


class CheckpointStoreProtocol(Protocol):
    def save(self, state: ExecutionState) -> str: ...
    def load(self, checkpoint_id: str) -> ExecutionState: ...
    def list_checkpoints(self, graph_id: str | None = None) -> list[str]: ...


class GraphVisualizerProtocol(Protocol):
    def to_mermaid(self, state: ExecutionState | None = None) -> str: ...
    def to_ascii(self) -> str: ...
