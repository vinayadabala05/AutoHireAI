"""Unit tests for `app.graph.state`."""

from datetime import UTC, datetime

from app.graph.state import ExecutionState, ExecutionStatus, NodeExecutionRecord


def test_execution_status_is_terminal_for_end_states() -> None:
    assert ExecutionStatus.SUCCEEDED.is_terminal is True
    assert ExecutionStatus.FAILED.is_terminal is True
    assert ExecutionStatus.SKIPPED.is_terminal is True
    assert ExecutionStatus.CANCELLED.is_terminal is True


def test_execution_status_is_not_terminal_for_active_states() -> None:
    assert ExecutionStatus.PENDING.is_terminal is False
    assert ExecutionStatus.READY.is_terminal is False
    assert ExecutionStatus.RUNNING.is_terminal is False
    assert ExecutionStatus.RETRYING.is_terminal is False


def test_node_execution_record_defaults() -> None:
    record = NodeExecutionRecord(node_id="a")
    assert record.status is ExecutionStatus.PENDING
    assert record.attempt == 0
    assert record.duration_ms is None


def test_node_execution_record_duration_ms_computed() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 1, 1, 0, 0, 1, 500000, tzinfo=UTC)
    record = NodeExecutionRecord(node_id="a", started_at=start, ended_at=end)
    assert record.duration_ms == 1500.0


def test_execution_state_record_for_creates_and_reuses() -> None:
    state = ExecutionState(run_id="r1", graph_id="g1")
    record_a = state.record_for("a")
    record_b = state.record_for("a")
    assert record_a is record_b
    assert "a" in state.node_records


def test_execution_state_mark_started_and_finished() -> None:
    state = ExecutionState(run_id="r1", graph_id="g1")
    state.mark_started()
    assert state.status is ExecutionStatus.RUNNING
    assert state.started_at is not None
    state.mark_finished(ExecutionStatus.SUCCEEDED)
    assert state.status is ExecutionStatus.SUCCEEDED
    assert state.ended_at is not None
    assert state.is_complete is True


def test_execution_state_succeeded_and_failed_node_ids() -> None:
    state = ExecutionState(run_id="r1", graph_id="g1")
    state.record_for("a").status = ExecutionStatus.SUCCEEDED
    state.record_for("b").status = ExecutionStatus.FAILED
    state.record_for("c").status = ExecutionStatus.SKIPPED
    assert state.succeeded_node_ids == ["a"]
    assert state.failed_node_ids == ["b"]


def test_execution_state_is_complete_false_when_pending() -> None:
    state = ExecutionState(run_id="r1", graph_id="g1")
    assert state.is_complete is False


def test_execution_state_serializes_to_json_and_back() -> None:
    state = ExecutionState(run_id="r1", graph_id="g1")
    state.record_for("a").status = ExecutionStatus.SUCCEEDED
    dumped = state.model_dump_json()
    restored = ExecutionState.model_validate_json(dumped)
    assert restored.run_id == "r1"
    assert restored.node_records["a"].status is ExecutionStatus.SUCCEEDED
