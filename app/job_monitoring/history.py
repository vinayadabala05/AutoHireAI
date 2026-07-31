"""Durable monitoring history: an append-only ledger of `ProcessedJob` records.

One JSON-Lines file (`data/job_monitoring/history.jsonl` by default) —
simpler than a JSON-array file for an append-only, ever-growing log, since
appending never requires rewriting the whole file (matching how a real
production deployment would eventually swap this for a database table
without changing `DuplicateDetector`'s contract).
"""

from pathlib import Path

from app.job_monitoring.models import ProcessedJob

_DEFAULT_HISTORY_PATH = Path("data/job_monitoring/history.jsonl")


class MonitoringHistoryStore:
    def __init__(self, path: Path | str = _DEFAULT_HISTORY_PATH) -> None:
        self._path = Path(path)

    def append(self, processed: ProcessedJob) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(processed.model_dump_json() + "\n")

    def load_all(self) -> list[ProcessedJob]:
        if not self._path.exists():
            return []
        lines = self._path.read_text(encoding="utf-8").splitlines()
        return [ProcessedJob.model_validate_json(line) for line in lines if line.strip()]

    def recent(self, limit: int = 50) -> list[ProcessedJob]:
        return self.load_all()[-limit:]
