"""Unit tests for `app.job_monitoring.history.MonitoringHistoryStore`."""

from datetime import UTC, datetime
from pathlib import Path

from app.job_monitoring.history import MonitoringHistoryStore
from app.job_monitoring.models import ProcessedJob, ProcessingOutcome


def _processed(company: str = "Acme") -> ProcessedJob:
    return ProcessedJob(
        content_hash=f"hash-{company}",
        source_url=f"https://example.com/{company}",
        company=company,
        title="Engineer",
        outcome=ProcessingOutcome.SUBMITTED,
        processed_at=datetime.now(UTC),
    )


def test_load_all_returns_empty_list_when_file_absent(tmp_path: Path) -> None:
    store = MonitoringHistoryStore(path=tmp_path / "history.jsonl")
    assert store.load_all() == []


def test_append_and_load_all_round_trips(tmp_path: Path) -> None:
    store = MonitoringHistoryStore(path=tmp_path / "history.jsonl")
    store.append(_processed("Acme"))
    store.append(_processed("Ex Corp"))
    loaded = store.load_all()
    assert [p.company for p in loaded] == ["Acme", "Ex Corp"]


def test_append_creates_parent_directories(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "dir" / "history.jsonl"
    store = MonitoringHistoryStore(path=path)
    store.append(_processed())
    assert path.exists()


def test_recent_returns_only_the_last_n_entries(tmp_path: Path) -> None:
    store = MonitoringHistoryStore(path=tmp_path / "history.jsonl")
    for i in range(5):
        store.append(_processed(f"Company{i}"))
    recent = store.recent(limit=2)
    assert [p.company for p in recent] == ["Company3", "Company4"]


def test_load_all_skips_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "history.jsonl"
    store = MonitoringHistoryStore(path=path)
    store.append(_processed())
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n\n")
    assert len(store.load_all()) == 1
