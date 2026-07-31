"""Unit tests for `app.job_monitoring.deduplication.DuplicateDetector`."""

from pathlib import Path

from app.job_monitoring.deduplication import DuplicateDetector
from app.job_monitoring.history import MonitoringHistoryStore
from app.job_monitoring.models import ProcessingOutcome
from tests.job_discovery_fixtures import sample_job


def _detector(tmp_path: Path) -> DuplicateDetector:
    return DuplicateDetector(history=MonitoringHistoryStore(path=tmp_path / "history.jsonl"))


def test_new_job_is_not_a_duplicate(tmp_path: Path) -> None:
    detector = _detector(tmp_path)
    assert detector.is_duplicate(sample_job()) is False


def test_mark_processed_makes_subsequent_check_a_duplicate(tmp_path: Path) -> None:
    detector = _detector(tmp_path)
    job = sample_job()
    detector.mark_processed(job, ProcessingOutcome.SUBMITTED)
    assert detector.is_duplicate(job) is True


def test_duplicate_detected_by_url_even_with_different_title(tmp_path: Path) -> None:
    detector = _detector(tmp_path)
    job_a = sample_job(source_url="https://x/1", title="Backend Engineer")
    detector.mark_processed(job_a, ProcessingOutcome.SUBMITTED)
    job_b = sample_job(source_url="https://x/1", title="Different Title")
    assert detector.is_duplicate(job_b) is True


def test_duplicate_detected_by_company_and_title_with_different_url(tmp_path: Path) -> None:
    detector = _detector(tmp_path)
    job_a = sample_job(source_url="https://a/1", company="Acme", title="Engineer")
    detector.mark_processed(job_a, ProcessingOutcome.SUBMITTED)
    job_b = sample_job(source_url="https://b/2", company="Acme", title="Engineer")
    assert detector.is_duplicate(job_b) is True


def test_duplicate_detected_by_content_hash(tmp_path: Path) -> None:
    detector = _detector(tmp_path)
    job_a = sample_job(source_url="https://a/1", location="San Francisco, CA")
    detector.mark_processed(job_a, ProcessingOutcome.SUBMITTED)
    job_b = sample_job(source_url="https://b/2", location="San Francisco, CA")
    assert detector.is_duplicate(job_b) is True


def test_distinct_jobs_are_not_duplicates(tmp_path: Path) -> None:
    detector = _detector(tmp_path)
    job_a = sample_job(source_url="https://a/1", company="Acme", title="Backend Engineer")
    detector.mark_processed(job_a, ProcessingOutcome.SUBMITTED)
    job_b = sample_job(source_url="https://b/2", company="Ex Corp", title="Frontend Engineer")
    assert detector.is_duplicate(job_b) is False


def test_history_is_loaded_once_and_reused_across_calls(tmp_path: Path) -> None:
    history = MonitoringHistoryStore(path=tmp_path / "history.jsonl")
    seeding_detector = DuplicateDetector(history=history)
    job = sample_job()
    seeding_detector.mark_processed(job, ProcessingOutcome.SUBMITTED)

    # A brand-new detector, same history store, should recognize the prior job.
    fresh_detector = DuplicateDetector(history=history)
    assert fresh_detector.is_duplicate(job) is True


def test_mark_processed_persists_to_history(tmp_path: Path) -> None:
    history = MonitoringHistoryStore(path=tmp_path / "history.jsonl")
    detector = DuplicateDetector(history=history)
    job = sample_job()
    detector.mark_processed(job, ProcessingOutcome.FAILED, detail="boom")
    persisted = history.load_all()
    assert len(persisted) == 1
    assert persisted[0].outcome is ProcessingOutcome.FAILED
    assert persisted[0].detail == "boom"
