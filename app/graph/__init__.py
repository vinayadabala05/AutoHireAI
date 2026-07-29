"""Graph Orchestration Engine.

The execution backbone for AutoHireAI: every major AI capability becomes
a `GraphNode`, wired into a `Graph` (a DAG), and run by `GraphExecutor` —
sequentially or in parallel, with retries, timeouts, cancellation,
checkpointing, and a full event trace. `GraphService` is the single
entrypoint most callers should use; `app/graph/adapters/` wraps every
existing Sprint 3–7 service as a node, unmodified.

Home-grown, dependency-free (stdlib + Pydantic only) — no LangGraph, no
external workflow engine.
"""

from app.graph.checkpoint import CheckpointStore, FileCheckpointStore, InMemoryCheckpointStore
from app.graph.context import ExecutionContext
from app.graph.edge import GraphEdge
from app.graph.events import Event, EventBus, EventType
from app.graph.exceptions import (
    CheckpointNotFoundError,
    CycleDetectedError,
    DuplicateNodeError,
    GraphCancelledError,
    GraphError,
    GraphExecutionError,
    GraphValidationError,
    NodeAlreadyRegisteredError,
    NodeExecutionError,
    NodeNotFoundError,
    NodeTimeoutError,
    UnknownNodeError,
)
from app.graph.executor import ExecutionMode, GraphExecutor
from app.graph.graph import Graph
from app.graph.memory import GraphMemory
from app.graph.metrics import GraphMetrics, MetricsCollector, NodeMetrics, compute_graph_metrics
from app.graph.node import GraphNode
from app.graph.planner import ExecutionPlanner
from app.graph.registry import NodeRegistry
from app.graph.retry import (
    ExponentialBackoffRetryPolicy,
    FixedDelayRetryPolicy,
    ImmediateRetryPolicy,
    NoRetryPolicy,
    RetryPolicy,
)
from app.graph.scheduler import GraphScheduler
from app.graph.service import GraphService, GraphValidationResult
from app.graph.state import ExecutionState, ExecutionStatus, NodeExecutionRecord
from app.graph.visualizer import GraphVisualizer

__all__ = [
    "CheckpointNotFoundError",
    "CheckpointStore",
    "CycleDetectedError",
    "DuplicateNodeError",
    "Event",
    "EventBus",
    "EventType",
    "ExecutionContext",
    "ExecutionMode",
    "ExecutionPlanner",
    "ExecutionState",
    "ExecutionStatus",
    "ExponentialBackoffRetryPolicy",
    "FileCheckpointStore",
    "FixedDelayRetryPolicy",
    "Graph",
    "GraphCancelledError",
    "GraphEdge",
    "GraphError",
    "GraphExecutionError",
    "GraphExecutor",
    "GraphMemory",
    "GraphMetrics",
    "GraphNode",
    "GraphScheduler",
    "GraphService",
    "GraphValidationError",
    "GraphValidationResult",
    "GraphVisualizer",
    "ImmediateRetryPolicy",
    "InMemoryCheckpointStore",
    "MetricsCollector",
    "NodeAlreadyRegisteredError",
    "NodeExecutionError",
    "NodeExecutionRecord",
    "NodeMetrics",
    "NodeNotFoundError",
    "NodeRegistry",
    "NodeTimeoutError",
    "NoRetryPolicy",
    "RetryPolicy",
    "UnknownNodeError",
    "compute_graph_metrics",
]
