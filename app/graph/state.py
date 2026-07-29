"""Execution state for the Graph Orchestration Engine.

`ExecutionState` is the single serializable record of "what happened" in
one graph run — every node's status, timing, retry count, and error, plus
the graph-level status and a trace of events. It is deliberately separate
from `GraphNode` (`node.py`): a node *definition* is a stateless, reusable
template (so the same `Graph` can be executed — even concurrently — more
than once), while `ExecutionState` is the per-run mutable record. This is
the same separation Airflow draws between an Operator and a TaskInstance,
and Prefect between a Task and a TaskRun.

Fully Pydantic (unlike `context.py`/`memory.py`, which hold live,
non-serializable Python objects) because this is exactly what
`checkpoint.py` persists to resume a graph later.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ExecutionStatus(StrEnum):
    """Lifecycle states for both a single node and an overall graph run."""

    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    RETRYING = "retrying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in {
            ExecutionStatus.SUCCEEDED,
            ExecutionStatus.FAILED,
            ExecutionStatus.SKIPPED,
            ExecutionStatus.CANCELLED,
        }


class NodeExecutionRecord(BaseModel):
    """One node's status, timing, retry count, and outcome for one run."""

    node_id: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    attempt: int = Field(default=0, ge=0)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    error: str | None = None
    execution_time_ms: float | None = None
    cpu_time_ms: float | None = None
    memory_delta_bytes: int | None = None

    @property
    def duration_ms(self) -> float | None:
        if self.started_at is None or self.ended_at is None:
            return None
        return (self.ended_at - self.started_at).total_seconds() * 1000


class ExecutionState(BaseModel):
    """The complete, serializable record of one graph execution."""

    run_id: str
    graph_id: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    started_at: datetime | None = None
    ended_at: datetime | None = None
    node_records: dict[str, NodeExecutionRecord] = Field(default_factory=dict)
    trace: list[dict[str, Any]] = Field(default_factory=list)

    def record_for(self, node_id: str) -> NodeExecutionRecord:
        """Get (creating if absent) the record for `node_id`."""
        if node_id not in self.node_records:
            self.node_records[node_id] = NodeExecutionRecord(node_id=node_id)
        return self.node_records[node_id]

    def mark_started(self) -> None:
        self.status = ExecutionStatus.RUNNING
        self.started_at = datetime.now(UTC)

    def mark_finished(self, status: ExecutionStatus) -> None:
        self.status = status
        self.ended_at = datetime.now(UTC)

    @property
    def is_complete(self) -> bool:
        return self.status.is_terminal

    @property
    def succeeded_node_ids(self) -> list[str]:
        return [
            node_id
            for node_id, record in self.node_records.items()
            if record.status is ExecutionStatus.SUCCEEDED
        ]

    @property
    def failed_node_ids(self) -> list[str]:
        return [
            node_id
            for node_id, record in self.node_records.items()
            if record.status is ExecutionStatus.FAILED
        ]
