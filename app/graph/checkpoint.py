"""Checkpointing: persist `ExecutionState` so a graph run can be resumed.

Only `ExecutionState` (status/timing/retry/trace — fully JSON-serializable
Pydantic) is persisted, not `GraphMemory`'s node outputs, which may be
arbitrary non-serializable Python objects (a `CareerProfile`, a
`ResumeDocument`, ...). Resuming from a checkpoint therefore re-runs any
node whose output isn't still available in the in-process `GraphMemory` of
the resuming call — see `docs/graph_engine.md` for the full trade-off and
how `executor.py`'s `resume()` uses this.

Checkpoint ids are `"{graph_id}:{run_id}"`. `FileCheckpointStore` maps that
to `{directory}/{graph_id}/{run_id}.json` rather than a literal colon in
the filename, since `:` is not a valid filename character on Windows.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from app.graph.exceptions import CheckpointNotFoundError
from app.graph.state import ExecutionState

_DEFAULT_CHECKPOINT_DIR = Path("data/graph_checkpoints")


def checkpoint_id_for(state: ExecutionState) -> str:
    return f"{state.graph_id}:{state.run_id}"


class CheckpointStore(ABC):
    @abstractmethod
    def save(self, state: ExecutionState) -> str:
        """Persist `state`, returning its checkpoint id."""

    @abstractmethod
    def load(self, checkpoint_id: str) -> ExecutionState:
        """Load a previously saved state. Raises `CheckpointNotFoundError` if absent."""

    @abstractmethod
    def list_checkpoints(self, graph_id: str | None = None) -> list[str]:
        """List every stored checkpoint id, optionally filtered to one `graph_id`."""

    @abstractmethod
    def delete(self, checkpoint_id: str) -> None:
        """Remove a checkpoint. A no-op if it doesn't exist."""


class InMemoryCheckpointStore(CheckpointStore):
    """Process-local checkpoint store — useful for tests and short-lived runs."""

    def __init__(self) -> None:
        self._checkpoints: dict[str, ExecutionState] = {}

    def save(self, state: ExecutionState) -> str:
        checkpoint_id = checkpoint_id_for(state)
        self._checkpoints[checkpoint_id] = state.model_copy(deep=True)
        return checkpoint_id

    def load(self, checkpoint_id: str) -> ExecutionState:
        try:
            return self._checkpoints[checkpoint_id].model_copy(deep=True)
        except KeyError as exc:
            raise CheckpointNotFoundError(f"No checkpoint '{checkpoint_id}'.") from exc

    def list_checkpoints(self, graph_id: str | None = None) -> list[str]:
        ids = list(self._checkpoints)
        if graph_id is not None:
            ids = [i for i in ids if i.startswith(f"{graph_id}:")]
        return sorted(ids)

    def delete(self, checkpoint_id: str) -> None:
        self._checkpoints.pop(checkpoint_id, None)


class FileCheckpointStore(CheckpointStore):
    """Durable, file-backed checkpoint store — one JSON file per run."""

    def __init__(self, directory: Path | str = _DEFAULT_CHECKPOINT_DIR) -> None:
        self._directory = Path(directory)

    def save(self, state: ExecutionState) -> str:
        checkpoint_id = checkpoint_id_for(state)
        path = self._path_for(checkpoint_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        return checkpoint_id

    def load(self, checkpoint_id: str) -> ExecutionState:
        path = self._path_for(checkpoint_id)
        if not path.exists():
            raise CheckpointNotFoundError(f"No checkpoint '{checkpoint_id}'.")
        return ExecutionState.model_validate_json(path.read_text(encoding="utf-8"))

    def list_checkpoints(self, graph_id: str | None = None) -> list[str]:
        if not self._directory.exists():
            return []
        graph_dirs = [self._directory / graph_id] if graph_id else sorted(self._directory.iterdir())
        ids = []
        for graph_dir in graph_dirs:
            if not graph_dir.is_dir():
                continue
            for run_file in sorted(graph_dir.glob("*.json")):
                ids.append(f"{graph_dir.name}:{run_file.stem}")
        return sorted(ids)

    def delete(self, checkpoint_id: str) -> None:
        self._path_for(checkpoint_id).unlink(missing_ok=True)

    def _path_for(self, checkpoint_id: str) -> Path:
        graph_id, _, run_id = checkpoint_id.partition(":")
        return self._directory / graph_id / f"{run_id}.json"
