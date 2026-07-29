"""Unit tests for `app.graph.executor.GraphExecutor`."""

import asyncio

import pytest

from app.graph.checkpoint import InMemoryCheckpointStore
from app.graph.context import ExecutionContext
from app.graph.events import Event, EventBus, EventType
from app.graph.exceptions import GraphCancelledError, GraphExecutionError
from app.graph.executor import ExecutionMode, GraphExecutor
from app.graph.graph import Graph
from app.graph.retry import FixedDelayRetryPolicy, NoRetryPolicy
from app.graph.state import ExecutionStatus
from tests.graph_fixtures import (
    EchoNode,
    FailingNode,
    FailingRecordingNode,
    FailWithBadHooksNode,
    FlakyNode,
    RecordingNode,
    SlowNode,
)


def _diamond_graph() -> Graph:
    graph = Graph("diamond")
    graph.add_node(EchoNode("a"))
    graph.add_node(EchoNode("b", dependencies=["a"]))
    graph.add_node(EchoNode("c", dependencies=["a"]))
    graph.add_node(EchoNode("d", dependencies=["b", "c"]))
    return graph


@pytest.mark.parametrize("mode", [ExecutionMode.SEQUENTIAL, ExecutionMode.PARALLEL])
async def test_run_succeeds_for_simple_dag(mode: ExecutionMode) -> None:
    state = await GraphExecutor().run(_diamond_graph(), mode=mode)
    assert state.status is ExecutionStatus.SUCCEEDED
    assert set(state.succeeded_node_ids) == {"a", "b", "c", "d"}


async def test_run_populates_node_outputs_in_memory() -> None:
    graph = Graph("g")
    graph.add_node(EchoNode("a", result="hello"))
    executor = GraphExecutor()
    context = ExecutionContext(graph_id="g", run_id="r1")
    await executor.run(graph, context=context)
    assert context.get_output("a") == "hello"


@pytest.mark.parametrize("mode", [ExecutionMode.SEQUENTIAL, ExecutionMode.PARALLEL])
async def test_failure_skips_only_downstream_dependents(mode: ExecutionMode) -> None:
    graph = Graph("g")
    graph.add_node(EchoNode("a"))
    graph.add_node(FailingNode("b", dependencies=["a"]))
    graph.add_node(EchoNode("c", dependencies=["b"]))
    graph.add_node(EchoNode("d"))  # independent branch

    with pytest.raises(GraphExecutionError) as exc_info:
        await GraphExecutor().run(graph, mode=mode)

    state = exc_info.value.state
    assert state.node_records["a"].status is ExecutionStatus.SUCCEEDED
    assert state.node_records["b"].status is ExecutionStatus.FAILED
    assert state.node_records["c"].status is ExecutionStatus.SKIPPED
    assert state.node_records["d"].status is ExecutionStatus.SUCCEEDED


async def test_optional_node_failure_does_not_fail_the_graph() -> None:
    graph = Graph("g")
    graph.add_node(FailingNode("a", optional=True))
    graph.add_node(EchoNode("b"))
    state = await GraphExecutor().run(graph)
    assert state.status is ExecutionStatus.SUCCEEDED
    assert state.node_records["a"].status is ExecutionStatus.FAILED


async def test_graph_execution_error_lists_only_non_optional_failures() -> None:
    graph = Graph("g")
    graph.add_node(FailingNode("optional_fail", optional=True))
    graph.add_node(FailingNode("required_fail"))
    with pytest.raises(GraphExecutionError) as exc_info:
        await GraphExecutor().run(graph)
    failed_ids = {failure.node_id for failure in exc_info.value.failures}
    assert failed_ids == {"required_fail"}


async def test_retry_policy_recovers_from_transient_failure() -> None:
    graph = Graph("g")
    graph.add_node(
        FlakyNode("f", fail_times=2, retry_policy=FixedDelayRetryPolicy(0.0, max_retries=3))
    )
    state = await GraphExecutor().run(graph)
    assert state.status is ExecutionStatus.SUCCEEDED
    assert state.node_records["f"].attempt == 2


async def test_retry_exhausted_marks_node_failed() -> None:
    graph = Graph("g")
    graph.add_node(
        FlakyNode("f", fail_times=5, retry_policy=FixedDelayRetryPolicy(0.0, max_retries=2))
    )
    with pytest.raises(GraphExecutionError):
        await GraphExecutor().run(graph)


async def test_retry_with_positive_delay_sleeps_between_attempts() -> None:
    graph = Graph("g")
    graph.add_node(
        FlakyNode("f", fail_times=1, retry_policy=FixedDelayRetryPolicy(0.01, max_retries=1))
    )
    state = await GraphExecutor().run(graph)
    assert state.status is ExecutionStatus.SUCCEEDED


async def test_no_retry_policy_fails_on_first_error() -> None:
    graph = Graph("g")
    node = FlakyNode("f", fail_times=1, retry_policy=NoRetryPolicy())
    graph.add_node(node)
    with pytest.raises(GraphExecutionError):
        await GraphExecutor().run(graph)
    assert node.calls == 1


async def test_timeout_fails_the_node() -> None:
    graph = Graph("g")
    graph.add_node(SlowNode("s", delay_seconds=1.0, timeout_seconds=0.02))
    with pytest.raises(GraphExecutionError) as exc_info:
        await GraphExecutor().run(graph)
    assert exc_info.value.state.node_records["s"].status is ExecutionStatus.FAILED


async def test_no_timeout_allows_slow_node_to_finish() -> None:
    graph = Graph("g")
    graph.add_node(SlowNode("s", delay_seconds=0.02))
    state = await GraphExecutor().run(graph)
    assert state.status is ExecutionStatus.SUCCEEDED


async def test_cooperative_cancellation_stops_pending_nodes() -> None:
    graph = Graph("g")
    graph.add_node(SlowNode("a", delay_seconds=0.2))
    graph.add_node(EchoNode("b", dependencies=["a"]))
    context = ExecutionContext(graph_id="g", run_id="r1")
    executor = GraphExecutor()
    task = asyncio.create_task(executor.run(graph, context=context))
    await asyncio.sleep(0.02)
    context.cancel()
    with pytest.raises(GraphCancelledError) as exc_info:
        await task
    assert exc_info.value.state.node_records["b"].status is ExecutionStatus.CANCELLED


async def test_cancellation_cancels_a_still_running_parallel_task() -> None:
    # Two independent nodes with staggered durations: the short one
    # finishes first (triggering the loop to recheck cancellation) while
    # the long one is still genuinely in flight — this exercises the
    # branch that calls `task.cancel()` on a non-empty `pending_tasks`.
    graph = Graph("g")
    graph.add_node(SlowNode("short", delay_seconds=0.02))
    graph.add_node(SlowNode("long", delay_seconds=5.0))
    context = ExecutionContext(graph_id="g", run_id="r1")
    executor = GraphExecutor()
    task = asyncio.create_task(executor.run(graph, context=context))
    await asyncio.sleep(0.005)
    context.cancel()
    with pytest.raises(GraphCancelledError) as exc_info:
        await task
    long_status = exc_info.value.state.node_records["long"].status
    assert long_status in (ExecutionStatus.CANCELLED, ExecutionStatus.RUNNING)


async def test_sequential_cancellation_stops_before_next_node() -> None:
    graph = Graph("g")
    graph.add_node(SlowNode("a", delay_seconds=0.05))
    graph.add_node(EchoNode("b", dependencies=["a"]))
    context = ExecutionContext(graph_id="g", run_id="r1")
    executor = GraphExecutor()
    task = asyncio.create_task(executor.run(graph, context=context, mode=ExecutionMode.SEQUENTIAL))
    await asyncio.sleep(0.01)
    context.cancel()
    with pytest.raises(GraphCancelledError) as exc_info:
        await task
    assert exc_info.value.state.node_records["b"].status is ExecutionStatus.CANCELLED


async def test_lifecycle_hooks_called_in_order_on_success() -> None:
    graph = Graph("g")
    node = RecordingNode("a")
    graph.add_node(node)
    await GraphExecutor().run(graph)
    assert node.calls == ["validate", "prepare", "execute", "cleanup"]


async def test_lifecycle_calls_rollback_and_cleanup_on_failure() -> None:
    graph = Graph("g")
    node = FailingRecordingNode("a")
    graph.add_node(node)
    with pytest.raises(GraphExecutionError):
        await GraphExecutor().run(graph)
    assert node.calls == ["validate", "prepare", "execute", "rollback", "cleanup"]


async def test_finalize_failure_swallows_rollback_and_cleanup_exceptions() -> None:
    graph = Graph("g")
    graph.add_node(FailWithBadHooksNode("a"))
    with pytest.raises(GraphExecutionError) as exc_info:
        await GraphExecutor().run(graph)
    # The original execute() failure is what's recorded, not the rollback/cleanup errors.
    assert "a failed" in exc_info.value.state.node_records["a"].error


async def test_validate_failure_prevents_execute() -> None:
    class InvalidNode(RecordingNode):
        async def validate(self, context):
            self.calls.append("validate")
            raise ValueError("invalid")

    graph = Graph("g")
    node = InvalidNode("a")
    graph.add_node(node)
    with pytest.raises(GraphExecutionError):
        await GraphExecutor().run(graph)
    assert "execute" not in node.calls


async def test_events_emitted_for_full_lifecycle() -> None:
    events: list[Event] = []
    bus = EventBus()
    bus.subscribe(events.append)
    graph = Graph("g")
    graph.add_node(EchoNode("a"))
    await GraphExecutor(event_bus=bus).run(graph)
    event_types = [event.type for event in events]
    assert event_types == [
        EventType.GRAPH_STARTED,
        EventType.NODE_STARTED,
        EventType.NODE_FINISHED,
        EventType.GRAPH_COMPLETED,
    ]


async def test_events_emitted_on_node_failure() -> None:
    events: list[Event] = []
    bus = EventBus()
    bus.subscribe(events.append)
    graph = Graph("g")
    graph.add_node(FailingNode("a"))
    with pytest.raises(GraphExecutionError):
        await GraphExecutor(event_bus=bus).run(graph)
    event_types = [event.type for event in events]
    assert EventType.NODE_FAILED in event_types
    assert EventType.GRAPH_FAILED in event_types


async def test_retry_emits_node_retrying_event() -> None:
    events: list[Event] = []
    bus = EventBus()
    bus.subscribe(events.append)
    graph = Graph("g")
    graph.add_node(
        FlakyNode("f", fail_times=1, retry_policy=FixedDelayRetryPolicy(0.0, max_retries=1))
    )
    await GraphExecutor(event_bus=bus).run(graph)
    assert EventType.NODE_RETRYING in [event.type for event in events]


async def test_skip_emits_node_skipped_event() -> None:
    events: list[Event] = []
    bus = EventBus()
    bus.subscribe(events.append)
    graph = Graph("g")
    graph.add_node(FailingNode("a"))
    graph.add_node(EchoNode("b", dependencies=["a"]))
    with pytest.raises(GraphExecutionError):
        await GraphExecutor(event_bus=bus).run(graph)
    assert EventType.NODE_SKIPPED in [event.type for event in events]


async def test_state_trace_records_every_event() -> None:
    graph = Graph("g")
    graph.add_node(EchoNode("a"))
    state = await GraphExecutor().run(graph)
    assert len(state.trace) >= 3


async def test_checkpoint_saved_when_enabled() -> None:
    store = InMemoryCheckpointStore()
    graph = Graph("g")
    graph.add_node(EchoNode("a"))
    executor = GraphExecutor(checkpoint_store=store)
    state = await executor.run(graph, checkpoint=True)
    checkpoint_id = f"{state.graph_id}:{state.run_id}"
    loaded = store.load(checkpoint_id)
    assert loaded.status is ExecutionStatus.SUCCEEDED


async def test_no_checkpoint_saved_when_disabled() -> None:
    store = InMemoryCheckpointStore()
    graph = Graph("g")
    graph.add_node(EchoNode("a"))
    executor = GraphExecutor(checkpoint_store=store)
    await executor.run(graph, checkpoint=False)
    assert store.list_checkpoints() == []


async def test_resume_skips_already_succeeded_nodes() -> None:
    graph = Graph("g")
    node_a = EchoNode("a")
    node_b = EchoNode("b", dependencies=["a"])
    graph.add_node(node_a)
    graph.add_node(node_b)

    executor = GraphExecutor()
    state = await executor.run(graph)
    assert node_a.calls == 1

    # Simulate a fresh resume attempt: node "a" is already SUCCEEDED, "b" is reset.
    state.record_for("b").status = ExecutionStatus.PENDING
    resumed = await executor.resume(graph, state)
    assert resumed.status is ExecutionStatus.SUCCEEDED
    assert node_a.calls == 1  # not re-executed


async def test_resume_skips_already_succeeded_nodes_in_sequential_mode() -> None:
    graph = Graph("g")
    node_a = EchoNode("a")
    node_b = EchoNode("b", dependencies=["a"])
    graph.add_node(node_a)
    graph.add_node(node_b)

    executor = GraphExecutor()
    state = await executor.run(graph, mode=ExecutionMode.SEQUENTIAL)
    assert node_a.calls == 1

    state.record_for("b").status = ExecutionStatus.PENDING
    resumed = await executor.resume(graph, state, mode=ExecutionMode.SEQUENTIAL)
    assert resumed.status is ExecutionStatus.SUCCEEDED
    assert node_a.calls == 1  # not re-executed


async def test_resume_reruns_failed_nodes() -> None:
    graph = Graph("g")
    node = FlakyNode("f", fail_times=1)
    graph.add_node(node)
    executor = GraphExecutor()
    with pytest.raises(GraphExecutionError) as exc_info:
        await executor.run(graph)
    state = exc_info.value.state
    resumed = await executor.resume(graph, state)
    assert resumed.status is ExecutionStatus.SUCCEEDED
    assert node.calls == 2


async def test_resume_preserves_memory_when_passed() -> None:
    graph = Graph("g")
    graph.add_node(EchoNode("a", result="value-a"))
    graph.add_node(FailingNode("b", dependencies=["a"]))

    executor = GraphExecutor()
    context = ExecutionContext(graph_id="g", run_id="r1")
    with pytest.raises(GraphExecutionError) as exc_info:
        await executor.run(graph, context=context)
    state = exc_info.value.state

    # Replace "b" with a working node to simulate a fix, then resume with the same memory.
    graph_fixed = Graph("g")
    graph_fixed.add_node(EchoNode("a", result="value-a"))
    graph_fixed.add_node(EchoNode("b", dependencies=["a"]))
    state.record_for("b").status = ExecutionStatus.PENDING
    resumed = await executor.resume(graph_fixed, state, memory=context.memory)
    assert resumed.status is ExecutionStatus.SUCCEEDED
    assert context.memory.get_output("a") == "value-a"


async def test_max_concurrency_limits_simultaneous_execution() -> None:
    graph = Graph("g")
    for i in range(4):
        graph.add_node(SlowNode(f"n{i}", delay_seconds=0.05))
    executor = GraphExecutor(max_concurrency=2)
    concurrent_tracker = {"current": 0, "max_seen": 0}

    class TrackedSlow(SlowNode):
        async def execute(self, context):
            concurrent_tracker["current"] += 1
            concurrent_tracker["max_seen"] = max(
                concurrent_tracker["max_seen"], concurrent_tracker["current"]
            )
            result = await super().execute(context)
            concurrent_tracker["current"] -= 1
            return result

    graph2 = Graph("g2")
    for i in range(4):
        graph2.add_node(TrackedSlow(f"n{i}", delay_seconds=0.05))
    await executor.run(graph2)
    assert concurrent_tracker["max_seen"] <= 2


async def test_run_id_is_generated_when_not_provided() -> None:
    graph = Graph("g")
    graph.add_node(EchoNode("a"))
    state = await GraphExecutor().run(graph)
    assert state.run_id  # non-empty


async def test_explicit_run_id_is_used() -> None:
    graph = Graph("g")
    graph.add_node(EchoNode("a"))
    state = await GraphExecutor().run(graph, run_id="custom-run-id")
    assert state.run_id == "custom-run-id"


async def test_node_priorities_affect_parallel_ordering() -> None:
    order: list[str] = []

    class OrderTrackingEcho(EchoNode):
        async def execute(self, context):
            order.append(self.id)
            return await super().execute(context)

    graph = Graph("g")
    graph.add_node(OrderTrackingEcho("low"))
    graph.add_node(OrderTrackingEcho("high"))
    await GraphExecutor(max_concurrency=1).run(
        graph, mode=ExecutionMode.PARALLEL, node_priorities={"low": 1, "high": 10}
    )
    assert order == ["high", "low"]


async def test_run_validates_graph_before_executing() -> None:
    graph = Graph("g")
    graph.add_node(EchoNode("a", dependencies=["missing"]))
    from app.graph.exceptions import UnknownNodeError

    with pytest.raises(UnknownNodeError):
        await GraphExecutor().run(graph)
