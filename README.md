# AutoHire AI

An autonomous AI career platform. This repository contains the
**project foundation** (Clean Architecture FastAPI skeleton) plus the
**Career Intelligence data layer** (Sprint 2) — the full relational schema
(19 models), repositories, and Pydantic schemas that will be the single
source of truth for every future feature (job discovery, resume
intelligence, cover letter generation, browser automation, analytics,
dashboard, multi-agent orchestration).

> **Scope so far:** architecture, configuration, logging, database wiring,
> Docker, testing, tooling, and the full data layer (models + migrations +
> repositories + schemas). No job-application logic, no browser automation,
> and no AI agents are implemented yet — see [docs/schema.md](docs/schema.md)
> for the data layer in depth.

## Tech stack

| Concern            | Choice                              |
|---------------------|--------------------------------------|
| Language            | Python 3.12                          |
| Web framework       | FastAPI                              |
| Validation/config   | Pydantic v2 + pydantic-settings      |
| ORM                 | SQLAlchemy 2 (async, asyncpg)        |
| Migrations          | Alembic                              |
| Database            | PostgreSQL                           |
| Cache/broker        | Redis                                |
| Logging             | Loguru (daily rotating file logs)    |
| Containerization    | Docker / Docker Compose              |
| Testing             | Pytest + pytest-asyncio + httpx      |
| Linting/formatting  | Ruff, Black, isort                   |
| Type checking       | mypy (strict)                        |
| Dependency mgmt     | Poetry                               |

## Architecture

Clean Architecture with strict inward-pointing dependencies. See
[docs/architecture.md](docs/architecture.md) for the full rationale behind
every layer boundary.

```
app/main.py → app/api/ → app/services/ → app/repositories/ → app/database/
                                 ↓
                  app/agents/, app/browser/, app/prompts/  (future)
```

## Folder structure

```
app/
├── main.py            # FastAPI app factory + entrypoint
├── api/                # Routers and HTTP endpoint handlers
│   ├── health.py        # GET /health
│   └── router.py        # Aggregates all sub-routers
├── core/               # Cross-cutting concerns, no dependency on other layers
│   ├── settings.py       # Pydantic Settings, sourced from .env
│   ├── logging.py        # Loguru configuration (daily rotation)
│   ├── security.py       # Password hashing + JWT primitives
│   ├── constants.py      # Enums and true constants
│   └── exceptions.py     # AppException hierarchy + global handlers
├── database/           # Engine, session factory, declarative base
│   ├── database.py       # Async engine + session factory
│   ├── base.py            # Base declarative class + TimestampMixin
│   └── session.py         # `get_db` FastAPI dependency
├── models/             # SQLAlchemy ORM models — the Career Intelligence schema (19 models)
├── schemas/            # Pydantic Create/Update/Response DTOs, one set per model
├── repositories/       # Data-access layer — one repository per model, shared generic CRUD base
├── services/           # Business/domain logic (empty — future)
├── agents/             # Multi-agent orchestration (empty — future)
├── browser/            # Browser automation (empty — future)
├── prompts/            # LLM prompt templates (empty — future)
└── utils/              # Stateless cross-cutting helpers (empty — future)

tests/                 # Pytest suite (test_health.py + conftest.py fixtures)
alembic/               # Migration environment (env.py wired to Base.metadata)
docker/                # Supplementary Docker assets (init scripts, future service images)
scripts/               # Operational scripts (container entrypoint, etc.)
docs/                  # Architecture documentation
logs/                  # Loguru output (gitignored, dir tracked via .gitkeep)
data/                  # Local persisted data (gitignored, dir tracked via .gitkeep)
dashboard/             # Reserved for the future frontend (not implemented yet)
```

Every folder's purpose is documented in more depth in
[docs/architecture.md](docs/architecture.md); the data layer specifically
(ER diagram, why every table exists, relationship rationale) is in
[docs/schema.md](docs/schema.md).

## Setup

### Prerequisites

- Python 3.12
- [Poetry](https://python-poetry.org/docs/#installation)
- Docker + Docker Compose (for Postgres/Redis, or the full stack)

### Local (without Docker)

```bash
poetry install
cp .env.example .env   # adjust values as needed; .env is already gitignored
```

Start Postgres and Redis (via Docker, without the API container):

```bash
docker compose up -d postgres redis
```

### Fully containerized

```bash
docker compose up --build
```

This starts the API on `http://localhost:8000`, Postgres on `5432`, and
Redis on `6379`.

## Run

```bash
poetry run uvicorn app.main:app --reload
```

Then verify:

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

## Testing

```bash
poetry run pytest
```

`tests/conftest.py` provides two fixtures: `client` (an `httpx.AsyncClient`
bound directly to the ASGI app, no live server needed) and `db_session` (a
real async Postgres session, with the full schema created fresh and torn
down around every test — requires `docker compose up -d postgres`).

- `tests/test_health.py` — the `/health` endpoint contract
- `tests/test_repositories_crud.py` — generic CRUD + entity-specific repository methods
- `tests/test_models_relationships.py` — cascades, unique constraints, soft delete, the shared `application_status` enum

## Formatting & static analysis

```bash
poetry run black .
poetry run isort .
poetry run ruff check . --fix
poetry run mypy app
```

All four are configured in [pyproject.toml](pyproject.toml) with consistent
settings (100-char line length, `py312` target, first-party import grouping
for `app`/`tests`).

## Database migrations

Alembic is wired to `app.database.base.Base.metadata`. The initial
migration (`alembic/versions/586d747bb8e6_*.py`) creates all 19 Career
Intelligence tables:

```bash
docker compose up -d postgres
poetry run alembic upgrade head
```

To generate a new migration after changing a model:

```bash
poetry run alembic revision --autogenerate -m "describe the change"
poetry run alembic check   # confirms no drift between models and migrations
```

See [docs/schema.md](docs/schema.md) for why the initial migration's
`downgrade()` includes manual `DROP TYPE` statements — Alembic's
autogenerate doesn't emit those for Postgres ENUMs on its own.

## Logging

Loguru is configured in `app/core/logging.py`:

- Console sink (colorized, level from `LOG_LEVEL`)
- `logs/app_{date}.log` — all logs, rotated daily at midnight, compressed, 14-day retention
- `logs/error_{date}.log` — ERROR+ only, with full tracebacks

Standard-library logging (uvicorn, SQLAlchemy) is intercepted and routed
through the same sinks, so nothing bypasses the rotation/retention policy.

## Configuration

All configuration is environment-driven via `app/core/settings.py`
(`pydantic-settings`, reading `.env`). See [.env.example](.env.example) for
every variable. Computed values (`DATABASE_URL`, `SYNC_DATABASE_URL`,
`REDIS_URL`) are derived from their component parts rather than duplicated.

## Roadmap

This foundation is designed to be extended, not rewritten, as each feature
lands:

- [x] Domain models (19 tables) + Alembic migrations + repositories + Pydantic schemas
- [ ] Job discovery (scraping/API integrations feeding `services/`)
- [ ] Resume intelligence (parsing, scoring)
- [ ] Cover letter generation (`prompts/` + `agents/`)
- [ ] Browser automation (`browser/`, e.g. Playwright-driven applications)
- [ ] Multi-agent orchestration (`agents/`)
- [ ] Analytics
- [ ] Dashboard (`dashboard/`)
- [ ] Authentication/authorization built on `core/security.py` primitives
