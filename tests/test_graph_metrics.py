"""Unit tests for `app.graph.metrics`."""

import time

from app.graph.metrics import MetricsCollector, compute_graph_metrics
from app.graph.state import ExecutionState, ExecutionStatus


def test_metrics_collector_measures_positive_execution_time() -> None:
    with MetricsCollector("a") as collector:
        time.sleep(0.01)
    assert collector.result is not None
    assert collector.result.execution_time_ms > 0
    assert collector.result.node_id == "a"


def test_metrics_collector_measures_memory_delta_for_allocations() -> None:
    with MetricsCollector("a") as collector:
        _ = [0] * 100_000
    assert collector.result is not None
    assert isinstance(collector.result.memory_delta_bytes, int)


def test_metrics_collector_cpu_time_is_non_negative() -> None:
    with MetricsCollector("a") as collector:
        sum(range(10_000))
    assert collector.result is not None
    assert collector.result.cpu_time_ms >= 0.0


def test_nested_metrics_collectors_do_not_stop_tracing_prematurely() -> None:
    with MetricsCollector("outer") as outer:
        with MetricsCollector("inner") as inner:
            time.sleep(0.001)
        assert inner.result is not None
    assert outer.result is not None


def test_compute_graph_metrics_counts_statuses() -> None:
    state = ExecutionState(run_id="r", graph_id="g")
    state.record_for("a").status = ExecutionStatus.SUCCEEDED
    state.record_for("b").status = ExecutionStatus.FAILED
    state.record_for("c").status = ExecutionStatus.SKIPPED
    state.record_for("d").status = ExecutionStatus.CANCELLED
    metrics = compute_graph_metrics(state)
    assert metrics.total_nodes == 4
    assert metrics.succeeded == 1
    assert metrics.failed == 1
    assert metrics.skipped == 1
    assert metrics.cancelled == 1


def test_compute_graph_metrics_aggregates_execution_time() -> None:
    state = ExecutionState(run_id="r", graph_id="g")
    record_a = state.record_for("a")
    record_a.status = ExecutionStatus.SUCCEEDED
    record_a.execution_time_ms = 10.0
    record_a.cpu_time_ms = 5.0
    record_a.memory_delta_bytes = 100
    record_b = state.record_for("b")
    record_b.status = ExecutionStatus.SUCCEEDED
    record_b.execution_time_ms = 20.0
    metrics = compute_graph_metrics(state)
    assert metrics.total_execution_time_ms == 30.0
    assert metrics.node_metrics["a"].memory_delta_bytes == 100


def test_compute_graph_metrics_empty_state() -> None:
    state = ExecutionState(run_id="r", graph_id="g")
    metrics = compute_graph_metrics(state)
    assert metrics.total_nodes == 0
    assert metrics.total_execution_time_ms == 0.0
    assert metrics.node_metrics == {}
