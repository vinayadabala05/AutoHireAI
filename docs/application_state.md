# Sprint 12: Application State & Recovery Engine

`app/application_state/` gives every application a durable, restart-safe
record of its progress through the pipeline: what stage it's at, whether
it succeeded or failed, how many times it's been retried, and a
searchable log of every transition. `ApplicationStateService` is the
single entrypoint every caller should use.

## Architecture

```
app/application_state/
├── models.py           # ApplicationStatus, ApplicationState, StateTransition, RecoveryReport
├── exceptions.py        # ApplicationStateError hierarchy
├── interfaces.py         # StateStoreProtocol, HistoryStoreProtocol
├── state_store.py       # ApplicationStateStore — keyed, atomic JSON persistence
├── history.py            # ApplicationHistoryStore — searchable JSON-Lines log
├── status_tracker.py     # StatusTracker — validated lifecycle transitions
├── retry_manager.py      # RetryManager — retry-eligibility (reuses Sprint 8's RetryPolicy)
├── recovery.py           # RecoveryService — re-drives one application through the pipeline
├── service.py             # ApplicationStateService — the facade
└── __init__.py
```

Dependency direction (no upstream sprint is modified):

```
application_state
   ├── job_monitoring.service.JobMonitoringService   (Sprint 11 — process_job())
   │     └── application_planning.service            (Sprint 9)
   │           └── browser_automation.service         (Sprint 10, via JobDispatcher)
   ├── job_discovery.deduplication.content_hash       (Sprint 7 — stable job_id)
   └── graph.retry.RetryPolicy                        (Sprint 8 — backoff policies)
```

`ApplicationStateService` doesn't call `BrowserAutomationService` or
`ApplicationPlanningService` directly — it drives them exactly the way
Sprint 11 already does, through `JobMonitoringService.process_job()`. That
single call already wires planning → resume → cover letter → submission
as one pipeline; re-deriving that wiring here would duplicate Sprint
9/10/11 logic instead of reusing it.

## Lifecycle

```
Pending → Planning → Resume → Cover Letter → Submitting → Submitted
                                                   ↓
                                                 Failed → (retry) → Pending
```

`StatusTracker` enforces this whole seven-stage graph via
`ALLOWED_TRANSITIONS`. In practice, only the boundaries
`JobMonitoringService.process_job()` actually exposes are observed:
`PLANNING` is set immediately before calling it, `SUBMITTING` immediately
after (a documented fast-path transition, since resume/cover-letter
generation happen *inside* that one atomic call — Sprint 9's own
`ApplicationPackageBuilder` isn't modified to emit progress from
mid-call), and the final `SUBMITTED`/`FAILED` reflects its result. `RESUME`
and `COVER_LETTER` remain valid states in the graph for any future caller
with finer-grained hooks into the pipeline.

`SUBMITTED` is terminal — no transition leaves it. `FAILED` can only go
back to `PENDING`, and only via `retry_failed()`.

## Duplicate-submission prevention across restarts

`job_id` is `content_hash(job)` (Sprint 7's normalized `(title, company,
location)` hash) — the same job always maps to the same state record,
even across process restarts. `save_state()` is idempotent: calling it
again for a job already tracked returns the existing record, and raises
`DuplicateSubmissionError` if that record is already `SUBMITTED`, so a
restarted caller can never resubmit a successful application by accident.

## Recovery: resuming interrupted applications

`ApplicationState.is_recoverable` is true for every non-terminal status
except `FAILED` (`PENDING`, `PLANNING`, `RESUME`, `COVER_LETTER`,
`SUBMITTING`) — precisely the states a process crash could leave an
application in mid-flight. `recover_pending()` scans the store for these
and re-drives each one through `RecoveryService.run_one()`, which:

1. Transitions `PLANNING` → `SUBMITTING`.
2. Calls `JobMonitoringService.process_job(state.job, profile, blueprint)`
   — the full pipeline, re-run from scratch (cheap: it's evaluation +
   generation + submission, not a re-fetch from a job board).
3. On a `SUBMITTED` outcome, records the submission status and
   transitions to `SUBMITTED`.
4. On any other outcome — or any exception the pipeline call itself
   raises — records `last_error` and transitions to `FAILED`.

Because `ApplicationState` embeds the full originating `DiscoveredJob`,
recovery never needs to re-fetch anything from a provider.

## Retrying transient failures

`retry_failed()` looks at every `FAILED` application and asks
`RetryManager.can_retry()` — eligible only if both the state's own
`max_retries` budget and the configured `RetryPolicy`'s (Sprint 8's
`app.graph.retry`, default `ExponentialBackoffRetryPolicy(max_retries=3)`)
budget allow another attempt. Eligible applications get `retry_count`
incremented, transition `FAILED` → `PENDING`, and are re-driven through
the same `RecoveryService.run_one()` used by recovery — retry and
recovery share one execution path so they can never disagree about how a
job actually gets resubmitted.

## Configuration

```python
from app.application_state.retry_manager import RetryManager
from app.graph.retry import ExponentialBackoffRetryPolicy

retry_manager = RetryManager(
    policy=ExponentialBackoffRetryPolicy(base_delay=2.0, max_retries=5)
)
```

`ApplicationStateStore`/`ApplicationHistoryStore` default to
`data/application_state/state.json` and `data/application_state/history.jsonl`
respectively; pass an explicit `path` to either constructor to relocate
them (e.g. per-environment or per-test).

## Usage example

```python
from app.application_state.service import ApplicationStateService
from app.application_state.models import ApplicationStatus

service = ApplicationStateService(monitoring_service)

# Register a newly matched job for tracking.
state = service.save_state(discovered_job)

# ... drive it through the pipeline (e.g. via JobMonitoringService directly,
# or by re-running recovery/retry) ...

# Look up current status.
current = service.get_application(state.job_id)

# On restart: resume anything left mid-pipeline.
report = await service.recover_pending(profile, blueprint)
print(report.recovered_job_ids, report.failed_job_ids)

# Retry failures still within their retry budget.
retried = await service.retry_failed(profile, blueprint)

# Search history.
failures = service.get_history(status=ApplicationStatus.FAILED)
```

## Testing

46 tests across `models`, `state_store`, `history`, `status_tracker`,
`retry_manager`, `recovery`, `service`, and `interfaces` — 100% line
coverage on `app/application_state/`. Integration tests build a real
`JobMonitoringService` (Sprint 11) wired to real `ApplicationPlanningService`
(Sprint 9) and `BrowserAutomationService` (Sprint 10) instances against a
fake Playwright page, matching the "fake the smallest boundary object,
never mock the service under test" pattern used since Sprint 4.
