"""Structural tests for `app.application_state.interfaces`."""

from pathlib import Path

from app.application_state.history import ApplicationHistoryStore
from app.application_state.state_store import ApplicationStateStore

_PROTOCOL_MEMBERS = {
    "StateStoreProtocol": ("save", "get", "list_all", "list_by_status", "delete"),
    "HistoryStoreProtocol": ("append", "query"),
}


def _satisfies(instance: object, members: tuple[str, ...]) -> bool:
    return all(hasattr(instance, member) for member in members)


def test_application_state_store_satisfies_protocol(tmp_path: Path) -> None:
    store = ApplicationStateStore(path=tmp_path / "state.json")
    assert _satisfies(store, _PROTOCOL_MEMBERS["StateStoreProtocol"])


def test_application_history_store_satisfies_protocol(tmp_path: Path) -> None:
    history = ApplicationHistoryStore(path=tmp_path / "history.jsonl")
    assert _satisfies(history, _PROTOCOL_MEMBERS["HistoryStoreProtocol"])
