"""Unit tests for `app.graph.checkpoint`."""

from pathlib import Path

import pytest

from app.graph.checkpoint import FileCheckpointStore, InMemoryCheckpointStore, checkpoint_id_for
from app.graph.exceptions import CheckpointNotFoundError
from app.graph.state import ExecutionState, ExecutionStatus


def _state(graph_id: str = "g1", run_id: str = "r1") -> ExecutionState:
    state = ExecutionState(run_id=run_id, graph_id=graph_id)
    state.record_for("a").status = ExecutionStatus.SUCCEEDED
    return state


def test_checkpoint_id_for_format() -> None:
    assert checkpoint_id_for(_state()) == "g1:r1"


def test_in_memory_store_save_and_load() -> None:
    store = InMemoryCheckpointStore()
    checkpoint_id = store.save(_state())
    loaded = store.load(checkpoint_id)
    assert loaded.run_id == "r1"
    assert loaded.node_records["a"].status is ExecutionStatus.SUCCEEDED


def test_in_memory_store_load_missing_raises() -> None:
    store = InMemoryCheckpointStore()
    with pytest.raises(CheckpointNotFoundError):
        store.load("nope:nope")


def test_in_memory_store_returns_a_deep_copy() -> None:
    store = InMemoryCheckpointStore()
    state = _state()
    checkpoint_id = store.save(state)
    loaded = store.load(checkpoint_id)
    loaded.record_for("a").status = ExecutionStatus.FAILED
    assert store.load(checkpoint_id).node_records["a"].status is ExecutionStatus.SUCCEEDED


def test_in_memory_store_list_checkpoints_filters_by_graph() -> None:
    store = InMemoryCheckpointStore()
    store.save(_state(graph_id="g1", run_id="r1"))
    store.save(_state(graph_id="g2", run_id="r2"))
    assert store.list_checkpoints("g1") == ["g1:r1"]
    assert set(store.list_checkpoints()) == {"g1:r1", "g2:r2"}


def test_in_memory_store_delete() -> None:
    store = InMemoryCheckpointStore()
    checkpoint_id = store.save(_state())
    store.delete(checkpoint_id)
    assert store.list_checkpoints() == []


def test_in_memory_store_delete_unknown_is_a_no_op() -> None:
    store = InMemoryCheckpointStore()
    store.delete("nope:nope")  # should not raise


def test_file_store_save_and_load(tmp_path: Path) -> None:
    store = FileCheckpointStore(directory=tmp_path)
    checkpoint_id = store.save(_state())
    loaded = store.load(checkpoint_id)
    assert loaded.run_id == "r1"
    assert loaded.node_records["a"].status is ExecutionStatus.SUCCEEDED


def test_file_store_writes_json_file_at_expected_path(tmp_path: Path) -> None:
    store = FileCheckpointStore(directory=tmp_path)
    store.save(_state())
    assert (tmp_path / "g1" / "r1.json").exists()


def test_file_store_load_missing_raises(tmp_path: Path) -> None:
    store = FileCheckpointStore(directory=tmp_path)
    with pytest.raises(CheckpointNotFoundError):
        store.load("g1:missing")


def test_file_store_list_checkpoints_empty_when_directory_absent(tmp_path: Path) -> None:
    store = FileCheckpointStore(directory=tmp_path / "does_not_exist")
    assert store.list_checkpoints() == []


def test_file_store_list_checkpoints_for_nonexistent_graph_id_is_empty(tmp_path: Path) -> None:
    store = FileCheckpointStore(directory=tmp_path)
    store.save(_state(graph_id="g1", run_id="r1"))
    assert store.list_checkpoints("no-such-graph") == []


def test_file_store_list_checkpoints_skips_stray_non_directory_entries(tmp_path: Path) -> None:
    store = FileCheckpointStore(directory=tmp_path)
    store.save(_state(graph_id="g1", run_id="r1"))
    (tmp_path / "stray_file.txt").write_text("not a graph directory", encoding="utf-8")
    assert store.list_checkpoints() == ["g1:r1"]


def test_file_store_list_checkpoints_filters_by_graph(tmp_path: Path) -> None:
    store = FileCheckpointStore(directory=tmp_path)
    store.save(_state(graph_id="g1", run_id="r1"))
    store.save(_state(graph_id="g2", run_id="r2"))
    assert store.list_checkpoints("g1") == ["g1:r1"]
    assert set(store.list_checkpoints()) == {"g1:r1", "g2:r2"}


def test_file_store_delete(tmp_path: Path) -> None:
    store = FileCheckpointStore(directory=tmp_path)
    checkpoint_id = store.save(_state())
    store.delete(checkpoint_id)
    assert store.list_checkpoints() == []


def test_file_store_delete_missing_is_a_no_op(tmp_path: Path) -> None:
    store = FileCheckpointStore(directory=tmp_path)
    store.delete("g1:missing")  # should not raise
