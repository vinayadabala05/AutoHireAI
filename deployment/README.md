# Sprint 13: Production Deployment & Operations

This layer takes the application built across Sprints 1–12 and makes it
operable in a real environment: containerized, configured entirely from
the environment, observable (health/readiness/metrics), and able to start
and stop cleanly. It is purely additive — no Sprint 1–12 file is modified.

## Why a second layer, not just the root `Dockerfile`/`docker-compose.yml`

Sprint 1 already ships a working `Dockerfile`/`docker-compose.yml` at the
project root, running `app.main:app` — that remains the right entrypoint
for local development and CI. `deployment/` adds a *production* entrypoint
(`deployment.startup:app`) on top of it, with readiness checks, metrics,
structured JSON logging, fail-fast config validation, and graceful
shutdown — the things you want in a real environment but that would only
add noise to local dev.

## Files

| File | Responsibility |
|---|---|
| `settings.py` | `DeploymentSettings` — ops-only env knobs (metrics on/off, timeouts, worker toggle) |
| `config.py` | `validate_configuration()` — fails fast on unsafe config in staging/production |
| `health.py` | `/health/ready` — checks Postgres + Redis reachability |
| `metrics.py` | `/metrics` — request counts, latency, error rate, uptime (Prometheus text format) |
| `logging.py` | `configure_production_logging()` — adds a JSON stdout sink in staging/production |
| `startup.py` | `create_production_app()` — assembles the production ASGI app |
| `shutdown.py` | `build_production_lifespan()` — graceful worker stop before DB engine disposal |
| `Dockerfile` | Multi-stage production image, non-root user, `HEALTHCHECK` |
| `docker-compose.yml` | Production stack: api + postgres + redis |

## How it reuses Sprints 1–12

- `startup.py` imports `app.api.router.api_router`, `app.core.exceptions.register_exception_handlers`,
  and `app.main.lifespan` directly — the same routes, error handling, and
  DB-engine-disposal behavior as `app.main:app`, not reimplemented.
- `health.py` reuses `app.database.database.check_database_connection`
  (Sprint 1) for the Postgres check.
- `shutdown.py`'s `StoppableWorker` protocol matches
  `JobMonitoringService` (Sprint 11) structurally — pass a running
  instance to `create_production_app(worker=...)` and its
  `stop_monitoring()` runs, within a timeout, before the DB engine is
  disposed.

## Configuration validation at startup

`create_production_app()` calls `validate_configuration()` before
constructing anything. In `staging`/`production`, it raises
`ConfigurationError` immediately (before the process binds a port) if:

- `SECRET_KEY` or `POSTGRES_PASSWORD` are still at their insecure
  Sprint-1 defaults, or
- `DEBUG=true` in production.

In `local`/`development`, the same problems are only logged as warnings —
a fresh checkout should run immediately without needing real secrets.

## Secrets

All secrets are environment variables, read from a local `.env` file
(never committed — see the project root's `.env.example` and
`.gitignore`). Neither `deployment/Dockerfile` nor
`deployment/docker-compose.yml` bakes in or hardcodes a credential;
`docker-compose.yml`'s `POSTGRES_PASSWORD` has no fallback default
(`${POSTGRES_PASSWORD:?...}`) precisely so a missing `.env` fails compose
startup instead of silently running with a guessable password.

## Endpoints

- `GET /health` — liveness (Sprint 1, unchanged): the process is alive.
- `GET /health/ready` — readiness (this sprint): Postgres and Redis are
  both reachable. Returns `503` if either check fails — use this as the
  Docker/Kubernetes readiness probe, `/health` as the liveness probe.
- `GET /metrics` — Prometheus text-format counters: `autohire_requests_total`,
  `autohire_errors_total`, `autohire_uptime_seconds`,
  `autohire_request_latency_seconds_avg`, `autohire_requests_by_path_total`.
  Disable with `METRICS_ENABLED=false`.

## Graceful shutdown

On `SIGTERM` (Docker/Kubernetes' stop signal), FastAPI's lifespan shutdown
runs `build_production_lifespan()`'s wrapped sequence:

1. If a `worker` (e.g. a running `JobMonitoringService`) was passed to
   `create_production_app()`, `stop_monitoring()` is awaited, bounded by
   `GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS` (default 30s) — a job mid-scan gets
   a chance to finish its current batch instead of being killed mid-write.
2. Sprint 1's own shutdown step then runs: the DB engine is disposed.

## Running it

```bash
cd deployment
cp ../.env.example ../.env   # fill in real values
docker compose up --build
```

Or without Docker, directly:

```bash
uvicorn deployment.startup:app --host 0.0.0.0 --port 8000
```

## Testing

35 tests across `config`, `settings`, `health`, `metrics`, `logging`,
`startup`, and `shutdown` — 100% line coverage on `deployment/`. All
external dependencies (Postgres, Redis) are faked at their boundary
(`monkeypatch`ing `check_database_connection`/`check_redis_connection`,
a fake Redis client, a fake `StoppableWorker`) — no test in this suite
requires a live database or Redis instance, matching the "fake the
smallest boundary object" convention used since Sprint 4.
