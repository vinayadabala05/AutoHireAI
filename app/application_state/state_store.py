"""`ApplicationStateStore`: durable, keyed persistence for every application's current state.

A single JSON file (`data/application_state/state.json` by default) mapping
`job_id -> ApplicationState`, rewritten atomically on every save (write to a
temp file, then `os.replace`) so a crash mid-write never corrupts it. Unlike
`MonitoringHistoryStore`'s append-only log (Sprint 11), this is a keyed
store: `get_application()` and duplicate-submission checks both need
random access by `job_id`, not a scan of every record ever written.
"""

import json
import os
from pathlib import Path

from app.application_state.models import ApplicationState, ApplicationStatus

_DEFAULT_STATE_PATH = Path("data/application_state/state.json")


class ApplicationStateStore:
    def __init__(self, path: Path | str = _DEFAULT_STATE_PATH) -> None:
        self._path = Path(path)
        self._states: dict[str, ApplicationState] = {}
        self._loaded = False

    def save(self, state: ApplicationState) -> None:
        self._ensure_loaded()
        self._states[state.job_id] = state
        self._flush()

    def get(self, job_id: str) -> ApplicationState | None:
        self._ensure_loaded()
        return self._states.get(job_id)

    def list_all(self) -> list[ApplicationState]:
        self._ensure_loaded()
        return list(self._states.values())

    def list_by_status(self, status: ApplicationStatus) -> list[ApplicationState]:
        self._ensure_loaded()
        return [state for state in self._states.values() if state.status is status]

    def delete(self, job_id: str) -> None:
        self._ensure_loaded()
        if job_id in self._states:
            del self._states[job_id]
            self._flush()

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        if self._path.exists():
            raw = self._path.read_text(encoding="utf-8")
            if raw.strip():
                for job_id, payload in _decode(raw).items():
                    self._states[job_id] = ApplicationState.model_validate(payload)
        self._loaded = True

    def _flush(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._path.with_suffix(f"{self._path.suffix}.tmp")
        entries = ",".join(
            f"{json.dumps(job_id)}:{state.model_dump_json()}"
            for job_id, state in self._states.items()
        )
        tmp_path.write_text("{" + entries + "}", encoding="utf-8")
        os.replace(tmp_path, self._path)


def _decode(raw: str) -> dict[str, object]:
    result: dict[str, object] = json.loads(raw)
    return result
