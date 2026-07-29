"""Execution metrics: per-node measurement + graph-level aggregation.

Memory is measured with `tracemalloc` (stdlib, cross-platform) rather than
`resource.getrusage` (POSIX-only, unavailable on Windows) — the trade-off
is that it measures Python-object allocation deltas, not full process RSS,
which is the right trade-off for a lightweight, dependency-free engine.
"""

import time
import tracemalloc
from types import TracebackType
from typing import Self

from pydantic import BaseModel, Field

from app.graph.state import ExecutionState


class NodeMetrics(BaseModel):
    """A single node's measured resource usage for one execution attempt."""

    node_id: str
    execution_time_ms: float = Field(ge=0.0)
    cpu_time_ms: float = Field(ge=0.0)
    memory_delta_bytes: int


class GraphMetrics(BaseModel):
    """Aggregate statistics for one graph execution."""

    graph_id: str
    run_id: str
    total_nodes: int = Field(ge=0)
    succeeded: int = Field(ge=0)
    failed: int = Field(ge=0)
    skipped: int = Field(ge=0)
    cancelled: int = Field(ge=0)
    total_execution_time_ms: float = Field(ge=0.0)
    node_metrics: dict[str, NodeMetrics] = Field(default_factory=dict)


class MetricsCollector:
    """Context manager measuring wall time, CPU time, and memory delta.

    Usage: `with MetricsCollector(node_id) as collector: ...`; after the
    `with` block, `collector.result` holds a populated `NodeMetrics`.
    """

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self.result: NodeMetrics | None = None
        self._wall_start = 0.0
        self._cpu_start = 0.0
        self._started_tracemalloc = False

    def __enter__(self) -> Self:
        if not tracemalloc.is_tracing():
            tracemalloc.start()
            self._started_tracemalloc = True
        self._mem_start, _ = tracemalloc.get_traced_memory()
        self._wall_start = time.perf_counter()
        self._cpu_start = time.process_time()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        wall_elapsed = (time.perf_counter() - self._wall_start) * 1000
        cpu_elapsed = (time.process_time() - self._cpu_start) * 1000
        mem_now, _ = tracemalloc.get_traced_memory()
        if self._started_tracemalloc:
            tracemalloc.stop()
        self.result = NodeMetrics(
            node_id=self.node_id,
            execution_time_ms=wall_elapsed,
            cpu_time_ms=max(0.0, cpu_elapsed),
            memory_delta_bytes=mem_now - self._mem_start,
        )


def compute_graph_metrics(state: ExecutionState) -> GraphMetrics:
    """Build a `GraphMetrics` summary from a completed (or in-flight) `ExecutionState`."""
    node_metrics: dict[str, NodeMetrics] = {}
    counts: dict[str, int] = {"succeeded": 0, "failed": 0, "skipped": 0, "cancelled": 0}
    for node_id, record in state.node_records.items():
        if record.status.value in counts:
            counts[record.status.value] += 1
        if record.execution_time_ms is not None:
            node_metrics[node_id] = NodeMetrics(
                node_id=node_id,
                execution_time_ms=record.execution_time_ms,
                cpu_time_ms=record.cpu_time_ms or 0.0,
                memory_delta_bytes=record.memory_delta_bytes or 0,
            )

    total_time = sum(m.execution_time_ms for m in node_metrics.values())
    return GraphMetrics(
        graph_id=state.graph_id,
        run_id=state.run_id,
        total_nodes=len(state.node_records),
        succeeded=counts["succeeded"],
        failed=counts["failed"],
        skipped=counts["skipped"],
        cancelled=counts["cancelled"],
        total_execution_time_ms=total_time,
        node_metrics=node_metrics,
    )
