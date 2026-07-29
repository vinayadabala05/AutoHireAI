"""The node system: `GraphNode`, the unit of work in a `Graph`.

A node *definition* is a stateless, reusable template — mirroring
`BaseLLMProvider` (Sprint 4) and `BaseJobProvider` (Sprint 7): subclass it,
implement `execute()`, and the executor drives the rest. Per-run status,
timing, retry count, and metrics live in `ExecutionState`/`NodeExecutionRecord`
(`state.py`), not on the node instance, so the same `Graph` can be executed
— even concurrently — more than once without one run's bookkeeping
clobbering another's. `last_record` is a convenience mirror the executor
updates after each attempt, for callers that want to inspect a node
directly after a single run.
"""

from abc import ABC, abstractmethod
from typing import Any

from app.graph.context import ExecutionContext
from app.graph.retry import NoRetryPolicy, RetryPolicy
from app.graph.state import NodeExecutionRecord


class GraphNode(ABC):
    """Contract every concrete graph node must implement."""

    def __init__(
        self,
        node_id: str,
        name: str,
        description: str = "",
        inputs: list[str] | None = None,
        outputs: list[str] | None = None,
        dependencies: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        retry_policy: RetryPolicy | None = None,
        timeout_seconds: float | None = None,
        optional: bool = False,
    ) -> None:
        self.id = node_id
        self.name = name
        self.description = description
        self.inputs = list(inputs or [])
        self.outputs = list(outputs or [])
        self.dependencies = list(dependencies or [])
        self.metadata = dict(metadata or {})
        self.retry_policy = retry_policy or NoRetryPolicy()
        self.timeout_seconds = timeout_seconds
        self.optional = optional
        self.last_record: NodeExecutionRecord | None = None

    async def validate(self, context: ExecutionContext) -> None:
        """Pre-flight validation. Default no-op; raise to fail fast before `execute()`."""
        return None

    async def prepare(self, context: ExecutionContext) -> None:
        """Setup before `execute()`. Default no-op."""
        return None

    @abstractmethod
    async def execute(self, context: ExecutionContext) -> Any:
        """Do the node's actual work and return its output."""

    async def cleanup(self, context: ExecutionContext) -> None:
        """Teardown, always called after `execute()` (whether it succeeded or failed)."""
        return None

    async def rollback(self, context: ExecutionContext) -> None:
        """Compensating action, called only if `execute()` ultimately (after retries) failed."""
        return None

    def to_definition_dict(self) -> dict[str, Any]:
        """Static, JSON-serializable node definition — used by `Graph.serialize()`."""
        return {
            "id": self.id,
            "type": type(self).__name__,
            "name": self.name,
            "description": self.description,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "dependencies": self.dependencies,
            "metadata": self.metadata,
            "timeout_seconds": self.timeout_seconds,
            "optional": self.optional,
        }

    def __repr__(self) -> str:
        return f"<{type(self).__name__} id={self.id!r} name={self.name!r}>"
