"""`GraphExecutor`: runs a `Graph`, producing an `ExecutionState`.

Two execution modes:

- `SEQUENTIAL` — nodes run one at a time, in topological order.
- `PARALLEL` — nodes run as soon as their dependencies finish (via
  `GraphScheduler`'s pull-based readiness queue), bounded by an optional
  `max_concurrency`.

DAG failure semantics apply to both: a failed node causes only its
*downstream dependents* to be skipped — independent branches keep running.
A node marked `optional=True` never fails the overall graph (its own
failure is still recorded), everything else does. Cancellation
(`ExecutionContext.cancel()`) is cooperative: it's checked between node
launches, and already-running nodes are cancelled via `asyncio.Task.cancel()`
in parallel mode.
"""

import asyncio
import contextlib
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from app.graph.checkpoint import CheckpointStore
from app.graph.context import ExecutionContext
from app.graph.events import Event, EventBus, EventType
from app.graph.exceptions import (
    GraphCancelledError,
    GraphExecutionError,
    NodeExecutionError,
    NodeTimeoutError,
)
from app.graph.graph import Graph
from app.graph.memory import GraphMemory
from app.graph.metrics import MetricsCollector
from app.graph.node import GraphNode
from app.graph.scheduler import GraphScheduler
from app.graph.state import ExecutionState, ExecutionStatus, NodeExecutionRecord

_ACTIVE_STATUSES = (
    ExecutionStatus.PENDING,
    ExecutionStatus.READY,
    ExecutionStatus.RUNNING,
    ExecutionStatus.RETRYING,
)


class ExecutionMode(StrEnum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


class GraphExecutor:
    def __init__(
        self,
        event_bus: EventBus | None = None,
        checkpoint_store: CheckpointStore | None = None,
        max_concurrency: int | None = None,
    ) -> None:
        self.event_bus = event_bus or EventBus()
        self.checkpoint_store = checkpoint_store
        self.max_concurrency = max_concurrency

    async def run(
        self,
        graph: Graph,
        *,
        inputs: dict[str, Any] | None = None,
        mode: ExecutionMode = ExecutionMode.PARALLEL,
        run_id: str | None = None,
        node_priorities: dict[str, int] | None = None,
        checkpoint: bool = False,
        context: ExecutionContext | None = None,
    ) -> ExecutionState:
        """Execute `graph` from scratch, returning the completed `ExecutionState`.

        Pass a pre-built `context` (rather than letting one be created
        internally) to cancel an in-flight run cooperatively from another
        task/coroutine: hold onto it, call `context.cancel()` while `run()`
        is awaited elsewhere, and execution stops between node launches.

        Raises `GraphExecutionError` if any non-optional node ultimately
        fails, or `GraphCancelledError` if the context was cancelled — both
        carry the partial `ExecutionState` as `.state` for inspection or
        `resume()`.
        """
        graph.validate()
        if context is None:
            context = ExecutionContext(
                graph_id=graph.id, run_id=run_id or str(uuid.uuid4()), inputs=inputs
            )
        state = ExecutionState(run_id=context.run_id, graph_id=graph.id)
        for node_id in graph.nodes:
            state.record_for(node_id)
        return await self._execute(graph, context, state, mode, node_priorities, checkpoint)

    async def resume(
        self,
        graph: Graph,
        state: ExecutionState,
        *,
        memory: GraphMemory | None = None,
        inputs: dict[str, Any] | None = None,
        mode: ExecutionMode = ExecutionMode.PARALLEL,
        node_priorities: dict[str, int] | None = None,
        checkpoint: bool = False,
        context: ExecutionContext | None = None,
    ) -> ExecutionState:
        """Resume a previously failed/cancelled/checkpointed run.

        Nodes already `SUCCEEDED` are not re-executed; every other node is
        reset to `PENDING` and re-attempted. Pass the original `memory`
        (same process only) to preserve already-computed node outputs for
        downstream nodes — otherwise a `SUCCEEDED` node's output is
        unavailable to its dependents and only its *status* carries over.
        """
        graph.validate()
        if context is None:
            context = ExecutionContext(
                graph_id=graph.id, run_id=state.run_id, inputs=inputs, memory=memory
            )
        already_succeeded = {
            node_id
            for node_id, record in state.node_records.items()
            if record.status is ExecutionStatus.SUCCEEDED
        }
        for node_id in graph.nodes:
            record = state.record_for(node_id)
            if record.status is not ExecutionStatus.SUCCEEDED:
                record.status = ExecutionStatus.PENDING
                record.error = None
                record.attempt = 0
        return await self._execute(
            graph, context, state, mode, node_priorities, checkpoint, already_succeeded
        )

    async def _execute(
        self,
        graph: Graph,
        context: ExecutionContext,
        state: ExecutionState,
        mode: ExecutionMode,
        node_priorities: dict[str, int] | None,
        checkpoint: bool,
        already_succeeded: frozenset[str] | set[str] = frozenset(),
    ) -> ExecutionState:
        state.mark_started()
        await self._emit(context, state, EventType.GRAPH_STARTED)

        if mode is ExecutionMode.SEQUENTIAL:
            await self._run_sequential(graph, context, state, already_succeeded)
        else:
            await self._run_parallel(graph, context, state, node_priorities, already_succeeded)

        self._checkpoint(state, checkpoint)

        if context.is_cancelled:
            state.mark_finished(ExecutionStatus.CANCELLED)
            await self._emit(context, state, EventType.GRAPH_CANCELLED)
            self._checkpoint(state, checkpoint)
            raise GraphCancelledError(
                f"Graph '{graph.id}' run '{context.run_id}' was cancelled.", state=state
            )

        failures = [
            NodeExecutionError(node_id, RuntimeError(state.node_records[node_id].error or "failed"))
            for node_id in state.failed_node_ids
            if not graph.get_node(node_id).optional
        ]
        if failures:
            state.mark_finished(ExecutionStatus.FAILED)
            await self._emit(context, state, EventType.GRAPH_FAILED)
            self._checkpoint(state, checkpoint)
            raise GraphExecutionError(failures, state=state)

        state.mark_finished(ExecutionStatus.SUCCEEDED)
        await self._emit(context, state, EventType.GRAPH_COMPLETED)
        self._checkpoint(state, checkpoint)
        return state

    def _checkpoint(self, state: ExecutionState, enabled: bool) -> None:
        if enabled and self.checkpoint_store is not None:
            self.checkpoint_store.save(state)

    async def _run_sequential(
        self,
        graph: Graph,
        context: ExecutionContext,
        state: ExecutionState,
        already_succeeded: frozenset[str] | set[str],
    ) -> None:
        order = graph.topological_order()
        failed: set[str] = set()
        skipped: set[str] = set()
        for index, node_id in enumerate(order):
            if node_id in already_succeeded:
                continue
            if context.is_cancelled:
                await self._cancel_nodes(order[index:], context, state)
                return
            node = graph.get_node(node_id)
            if any(dep in failed or dep in skipped for dep in node.dependencies):
                await self._skip_node(node, context, state)
                skipped.add(node_id)
                continue
            success = await self._run_node(node, context, state)
            if not success:
                failed.add(node_id)

    async def _run_parallel(
        self,
        graph: Graph,
        context: ExecutionContext,
        state: ExecutionState,
        node_priorities: dict[str, int] | None,
        already_succeeded: frozenset[str] | set[str],
    ) -> None:
        scheduler = GraphScheduler(graph, node_priorities)
        failed: set[str] = set()
        skipped: set[str] = set()
        semaphore = asyncio.Semaphore(self.max_concurrency) if self.max_concurrency else None
        pending_tasks: set[asyncio.Task[None]] = set()

        async def launch(node_id: str) -> None:
            if node_id in already_succeeded:
                scheduler.mark_complete(node_id)
                return
            node = graph.get_node(node_id)
            if any(dep in failed or dep in skipped for dep in node.dependencies):
                await self._skip_node(node, context, state)
                skipped.add(node_id)
            else:
                if semaphore is not None:
                    async with semaphore:
                        success = await self._run_node(node, context, state)
                else:
                    success = await self._run_node(node, context, state)
                if not success:
                    failed.add(node_id)
            scheduler.mark_complete(node_id)

        while scheduler.completed_count < scheduler.total_count:
            if context.is_cancelled:
                for task in pending_tasks:
                    task.cancel()
                if pending_tasks:
                    await asyncio.gather(*pending_tasks, return_exceptions=True)
                remaining = [
                    node_id
                    for node_id in graph.nodes
                    if state.record_for(node_id).status in _ACTIVE_STATUSES
                ]
                await self._cancel_nodes(remaining, context, state)
                return

            for node_id in scheduler.pop_all_ready():
                pending_tasks.add(asyncio.create_task(launch(node_id)))

            if not pending_tasks:
                break  # pragma: no cover - safety valve; unreachable for a validated DAG

            done, pending_tasks = await asyncio.wait(
                pending_tasks, return_when=asyncio.FIRST_COMPLETED
            )
            pending_tasks = set(pending_tasks)
            for task in done:
                task.result()

    async def _run_node(
        self, node: GraphNode, context: ExecutionContext, state: ExecutionState
    ) -> bool:
        """Run one node, including retries and timeout. Returns success/failure.

        A normal execution failure never raises out of this method — it is
        recorded on `state` and reflected in the return value. Only
        `asyncio.CancelledError` (from an external `task.cancel()`)
        propagates, so real cancellation still behaves like cancellation.
        """
        record = state.record_for(node.id)
        record.status = ExecutionStatus.RUNNING
        record.started_at = datetime.now(UTC)
        await self._emit(context, state, EventType.NODE_STARTED, node.id)

        try:
            await node.validate(context)
            await node.prepare(context)
        except Exception as exc:
            return await self._finalize_failure(node, context, state, record, exc)

        attempt_number = 0
        while True:
            record.attempt = attempt_number
            last_exc: BaseException | None = None
            try:
                with MetricsCollector(node.id) as collector:
                    if node.timeout_seconds is not None:
                        result = await asyncio.wait_for(
                            node.execute(context), timeout=node.timeout_seconds
                        )
                    else:
                        result = await node.execute(context)
                assert collector.result is not None
                record.execution_time_ms = collector.result.execution_time_ms
                record.cpu_time_ms = collector.result.cpu_time_ms
                record.memory_delta_bytes = collector.result.memory_delta_bytes
                context.set_output(node.id, result)
                record.status = ExecutionStatus.SUCCEEDED
                record.ended_at = datetime.now(UTC)
                node.last_record = record
                await node.cleanup(context)
                await self._emit(context, state, EventType.NODE_FINISHED, node.id)
                return True
            except TimeoutError as exc:
                last_exc = NodeTimeoutError(node.id, exc)
            except Exception as exc:
                last_exc = exc

            next_retry = attempt_number + 1
            if node.retry_policy.is_retryable(next_retry, last_exc):
                record.status = ExecutionStatus.RETRYING
                await self._emit(
                    context, state, EventType.NODE_RETRYING, node.id, {"attempt": next_retry}
                )
                delay = node.retry_policy.delay_seconds(next_retry)
                if delay > 0:
                    await asyncio.sleep(delay)
                attempt_number = next_retry
                continue
            return await self._finalize_failure(node, context, state, record, last_exc)

    async def _finalize_failure(
        self,
        node: GraphNode,
        context: ExecutionContext,
        state: ExecutionState,
        record: NodeExecutionRecord,
        exc: BaseException,
    ) -> bool:
        record.status = ExecutionStatus.FAILED
        record.ended_at = datetime.now(UTC)
        record.error = str(exc)
        node.last_record = record
        # rollback/cleanup are best-effort; neither may mask the original failure
        with contextlib.suppress(Exception):
            await node.rollback(context)
        with contextlib.suppress(Exception):
            await node.cleanup(context)
        await self._emit(context, state, EventType.NODE_FAILED, node.id, {"error": str(exc)})
        return False

    async def _skip_node(
        self, node: GraphNode, context: ExecutionContext, state: ExecutionState
    ) -> None:
        record = state.record_for(node.id)
        record.status = ExecutionStatus.SKIPPED
        record.ended_at = datetime.now(UTC)
        node.last_record = record
        await self._emit(context, state, EventType.NODE_SKIPPED, node.id)

    async def _cancel_nodes(
        self, node_ids: list[str], context: ExecutionContext, state: ExecutionState
    ) -> None:
        for node_id in node_ids:
            record = state.record_for(node_id)
            if record.status in _ACTIVE_STATUSES:
                record.status = ExecutionStatus.CANCELLED
                record.ended_at = datetime.now(UTC)
                await self._emit(context, state, EventType.NODE_CANCELLED, node_id)

    async def _emit(
        self,
        context: ExecutionContext,
        state: ExecutionState,
        event_type: EventType,
        node_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        event = Event(
            type=event_type,
            graph_id=context.graph_id,
            run_id=context.run_id,
            node_id=node_id,
            payload=payload or {},
        )
        state.trace.append(event.model_dump(mode="json"))
        await self.event_bus.emit(event)
