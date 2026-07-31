"""`ApplicationHistoryStore`: a searchable, append-only log of every status transition.

Same JSON-Lines shape as Sprint 11's `MonitoringHistoryStore` — appending
never requires rewriting the whole file — but this store also needs to
answer "what happened to job X" and "show me every FAILED transition",
so `query()` filters by `job_id`/`status`/`limit` over the full log.
"""

from pathlib import Path

from app.application_state.models import ApplicationStatus, StateTransition

_DEFAULT_HISTORY_PATH = Path("data/application_state/history.jsonl")


class ApplicationHistoryStore:
    def __init__(self, path: Path | str = _DEFAULT_HISTORY_PATH) -> None:
        self._path = Path(path)

    def append(self, transition: StateTransition) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(transition.model_dump_json() + "\n")

    def load_all(self) -> list[StateTransition]:
        if not self._path.exists():
            return []
        lines = self._path.read_text(encoding="utf-8").splitlines()
        return [StateTransition.model_validate_json(line) for line in lines if line.strip()]

    def query(
        self,
        job_id: str | None = None,
        status: ApplicationStatus | None = None,
        limit: int | None = None,
    ) -> list[StateTransition]:
        results = self.load_all()
        if job_id is not None:
            results = [t for t in results if t.job_id == job_id]
        if status is not None:
            results = [t for t in results if t.to_status is status]
        if limit is not None:
            results = results[-limit:]
        return results
