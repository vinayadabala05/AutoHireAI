"""Unit tests for `app.job_monitoring.models`."""

from datetime import UTC, datetime, timedelta

from app.job_monitoring.models import (
    MonitoringResult,
    MonitoringStatistics,
    ProcessedJob,
    ProcessingOutcome,
)


def test_monitoring_result_latency_ms_none_when_not_ended() -> None:
    result = MonitoringResult(scan_id="s1", started_at=datetime.now(UTC))
    assert result.latency_ms is None


def test_monitoring_result_latency_ms_computed() -> None:
    started = datetime(2026, 1, 1, tzinfo=UTC)
    result = MonitoringResult(
        scan_id="s1", started_at=started, ended_at=started + timedelta(milliseconds=250)
    )
    assert result.latency_ms == 250.0


def test_monitoring_statistics_record_scan_accumulates_counts() -> None:
    stats = MonitoringStatistics()
    started = datetime(2026, 1, 1, tzinfo=UTC)
    result = MonitoringResult(
        scan_id="s1",
        started_at=started,
        ended_at=started + timedelta(milliseconds=100),
        jobs_discovered=5,
        jobs_filtered_out=2,
        jobs_duplicate=1,
        jobs_submitted=1,
        jobs_skipped=1,
        jobs_failed=0,
    )
    stats.record_scan(result)
    assert stats.total_scans == 1
    assert stats.total_jobs_discovered == 5
    assert stats.total_jobs_filtered_out == 2
    assert stats.total_jobs_duplicate == 1
    assert stats.total_jobs_submitted == 1
    assert stats.total_jobs_skipped == 1
    assert stats.average_latency_ms == 100.0
    assert stats.last_scan_at == result.ended_at


def test_monitoring_statistics_average_latency_updates_incrementally() -> None:
    stats = MonitoringStatistics()
    started = datetime(2026, 1, 1, tzinfo=UTC)
    for latency_ms in (100.0, 200.0):
        result = MonitoringResult(
            scan_id="s",
            started_at=started,
            ended_at=started + timedelta(milliseconds=latency_ms),
        )
        stats.record_scan(result)
    assert stats.average_latency_ms == 150.0


def test_processed_job_serializes_round_trip() -> None:
    processed = ProcessedJob(
        content_hash="abc",
        source_url="https://example.com/job/1",
        company="Acme",
        title="Engineer",
        outcome=ProcessingOutcome.SUBMITTED,
        processed_at=datetime.now(UTC),
    )
    restored = ProcessedJob.model_validate_json(processed.model_dump_json())
    assert restored.outcome is ProcessingOutcome.SUBMITTED
    assert restored.company == "Acme"
