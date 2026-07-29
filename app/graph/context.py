"""Execution context: the object every node's lifecycle method receives.

Wraps `GraphMemory` (node outputs + shared scratch space) with per-run
identity (`run_id`, `graph_id`), the caller-supplied initial `inputs`, and
a cooperative cancellation token (`asyncio.Event`) `executor.py` checks
between nodes. Plain class, not Pydantic, for the same reason as
`GraphMemory`: it holds live, non-serializable objects (an `asyncio.Event`,
arbitrary node outputs).
"""

import asyncio
from typing import Any

from app.graph.memory import GraphMemory


class ExecutionContext:
    def __init__(
        self,
        graph_id: str,
        run_id: str,
        inputs: dict[str, Any] | None = None,
        memory: GraphMemory | None = None,
    ) -> None:
        self.graph_id = graph_id
        self.run_id = run_id
        self.inputs = inputs or {}
        self.memory = memory or GraphMemory()
        self._cancel_event = asyncio.Event()

    def get_input(self, name: str, default: Any = None) -> Any:
        return self.inputs.get(name, default)

    def get_output(self, node_id: str, default: Any = None) -> Any:
        return self.memory.get_output(node_id, default)

    def set_output(self, node_id: str, value: Any) -> None:
        self.memory.set_output(node_id, value)

    def cancel(self) -> None:
        """Request cooperative cancellation. Checked between node starts."""
        self._cancel_event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()
