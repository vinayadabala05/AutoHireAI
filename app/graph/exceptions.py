"""Exception hierarchy for the Graph Orchestration Engine.

Mirrors every prior sprint's convention (`app.llm.exceptions`,
`app.job_discovery.exceptions`): one base class, specific subclasses so
callers can catch broadly or narrowly.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.graph.state import ExecutionState


class GraphError(Exception):
    """Base class for every exception raised by `app.graph`."""


class GraphValidationError(GraphError):
    """Raised when a graph fails structural validation (e.g. before execution)."""


class CycleDetectedError(GraphValidationError):
    """Raised when a graph contains a directed cycle (violates the DAG contract)."""

    def __init__(self, cycle: list[str]) -> None:
        self.cycle = cycle
        super().__init__(f"Cycle detected in graph: {' -> '.join([*cycle, cycle[0]])}")


class UnknownNodeError(GraphValidationError):
    """Raised when an edge or dependency references a node id not in the graph."""


class DuplicateNodeError(GraphValidationError):
    """Raised when a node id is registered/added more than once."""


class NodeExecutionError(GraphError):
    """Raised when a node's `execute()` fails after exhausting its retry policy."""

    def __init__(self, node_id: str, original: BaseException) -> None:
        self.node_id = node_id
        self.original = original
        super().__init__(f"Node '{node_id}' failed: {original}")


class NodeTimeoutError(NodeExecutionError):
    """Raised when a node exceeds its configured timeout."""


class GraphExecutionError(GraphError):
    """Raised when graph execution fails and cannot continue.

    Carries every `NodeExecutionError` encountered (a graph can fail at
    multiple independent, parallel nodes in the same run) plus the final
    `ExecutionState`, so a caller can inspect exactly what ran/failed or
    hand `.state` to `GraphExecutor.resume()`.
    """

    def __init__(
        self, failures: list[NodeExecutionError], state: "ExecutionState | None" = None
    ) -> None:
        self.failures = failures
        self.state = state
        summary = "; ".join(str(failure) for failure in failures)
        super().__init__(f"Graph execution failed: {summary}")


class GraphCancelledError(GraphError):
    """Raised when execution is stopped via cancellation before completing."""

    def __init__(self, message: str, state: "ExecutionState | None" = None) -> None:
        self.state = state
        super().__init__(message)


class NodeNotFoundError(GraphError):
    """Raised by the registry when looking up an unregistered node name."""


class NodeAlreadyRegisteredError(GraphError):
    """Raised by the registry when registering a name that already exists."""


class CheckpointNotFoundError(GraphError):
    """Raised when resuming from a checkpoint id that doesn't exist in the store."""
