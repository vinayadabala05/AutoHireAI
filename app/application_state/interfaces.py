"""Structural interfaces for the Application State & Recovery Engine."""

from typing import Protocol

from app.application_state.models import ApplicationState, ApplicationStatus, StateTransition

__all__ = ["HistoryStoreProtocol", "StateStoreProtocol"]


class StateStoreProtocol(Protocol):
    def save(self, state: ApplicationState) -> None: ...

    def get(self, job_id: str) -> ApplicationState | None: ...

    def list_all(self) -> list[ApplicationState]: ...

    def list_by_status(self, status: ApplicationStatus) -> list[ApplicationState]: ...

    def delete(self, job_id: str) -> None: ...


class HistoryStoreProtocol(Protocol):
    def append(self, transition: StateTransition) -> None: ...

    def query(
        self,
        job_id: str | None = None,
        status: ApplicationStatus | None = None,
        limit: int | None = None,
    ) -> list[StateTransition]: ...
