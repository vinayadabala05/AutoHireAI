"""`StatusTracker`: the only place lifecycle transitions are validated and recorded.

Defines the full seven-stage transition graph (see `models.py` for why
`RESUME`/`COVER_LETTER` are valid-but-often-skipped-over states), rejects
anything not on that graph via `InvalidTransitionError`, and — on every
valid transition — persists the updated `ApplicationState` and appends a
`StateTransition` to the searchable history in one place, so `save_state`
and `get_history` (Sprint 12's required APIs) can never disagree.
"""

from datetime import UTC, datetime

from loguru import logger

from app.application_state.exceptions import ApplicationNotFoundError, InvalidTransitionError
from app.application_state.history import ApplicationHistoryStore
from app.application_state.models import (
    ApplicationState,
    ApplicationStatus,
    StateTransition,
)
from app.application_state.state_store import ApplicationStateStore

ALLOWED_TRANSITIONS: dict[ApplicationStatus, frozenset[ApplicationStatus]] = {
    ApplicationStatus.PENDING: frozenset({ApplicationStatus.PLANNING}),
    ApplicationStatus.PLANNING: frozenset({ApplicationStatus.RESUME, ApplicationStatus.FAILED}),
    ApplicationStatus.RESUME: frozenset({ApplicationStatus.COVER_LETTER, ApplicationStatus.FAILED}),
    ApplicationStatus.COVER_LETTER: frozenset(
        {ApplicationStatus.SUBMITTING, ApplicationStatus.FAILED}
    ),
    ApplicationStatus.SUBMITTING: frozenset(
        {ApplicationStatus.SUBMITTED, ApplicationStatus.FAILED}
    ),
    ApplicationStatus.SUBMITTED: frozenset(),
    ApplicationStatus.FAILED: frozenset({ApplicationStatus.PENDING}),
}
"""`PLANNING`/`SUBMITTING` may also jump straight to each other's target on a
call that skips the intermediate observable stage (`process_job()` runs
resume + cover letter generation atomically) — see `_FAST_PATHS` below."""

_FAST_PATHS: dict[ApplicationStatus, frozenset[ApplicationStatus]] = {
    ApplicationStatus.PLANNING: frozenset({ApplicationStatus.SUBMITTING}),
}


class StatusTracker:
    def __init__(
        self,
        store: ApplicationStateStore,
        history: ApplicationHistoryStore,
    ) -> None:
        self._store = store
        self._history = history

    def transition(
        self, job_id: str, to_status: ApplicationStatus, detail: str | None = None
    ) -> ApplicationState:
        state = self._store.get(job_id)
        if state is None:
            raise ApplicationNotFoundError(job_id)

        from_status = state.status
        allowed = ALLOWED_TRANSITIONS[from_status] | _FAST_PATHS.get(from_status, frozenset())
        if to_status not in allowed:
            raise InvalidTransitionError(job_id, from_status, to_status)

        state.status = to_status
        state.updated_at = datetime.now(UTC)
        self._store.save(state)
        self._history.append(
            StateTransition(
                job_id=job_id,
                company=state.company,
                title=state.title,
                from_status=from_status,
                to_status=to_status,
                timestamp=state.updated_at,
                detail=detail,
            )
        )
        logger.bind(job_id=job_id, from_status=from_status.value, to_status=to_status.value).info(
            "Application transitioned: {} -> {}", from_status.value, to_status.value
        )
        return state
