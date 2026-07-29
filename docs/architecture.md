# Architecture

AutoHire AI's backend follows **Clean Architecture**: dependencies point
inward, toward domain logic, and outward-facing concerns (HTTP, the
database, third-party APIs) are kept at the edges and swappable.

```
Request → api/ (routers) → services/ (business logic) → repositories/ (data access) → database/
                                     ↓
                            agents/, browser/, prompts/  (future: AI + automation)
```

## Layers

| Layer          | Responsibility                                              | Depends on                     |
|----------------|--------------------------------------------------------------|---------------------------------|
| `api/`         | HTTP routing, request/response marshalling                  | `schemas/`, `services/`         |
| `schemas/`     | Pydantic request/response DTOs                              | nothing (pure data)             |
| `services/`    | Business/domain logic, orchestrates use cases                | `repositories/`, `agents/`      |
| `repositories/`| Data access, encapsulates all ORM queries                   | `models/`, `database/`          |
| `models/`      | SQLAlchemy ORM table definitions                             | `database/base.py`              |
| `database/`    | Engine, session factory, declarative base                   | `core/settings.py`              |
| `agents/`      | Multi-agent orchestration (future)                           | `prompts/`, `services/`         |
| `browser/`     | Browser automation (future)                                  | `services/`                     |
| `prompts/`     | LLM prompt templates (future)                                | nothing                         |
| `core/`        | Cross-cutting: settings, logging, security, exceptions       | nothing (foundation layer)      |
| `utils/`       | Stateless helpers with no business meaning                   | nothing                         |

## Why this shape

- **Routers stay thin.** `api/health.py` has zero logic beyond calling into
  the domain — this is the pattern every future endpoint follows, so
  business rules live in one place (`services/`) instead of being
  duplicated across HTTP handlers, CLI scripts, and background jobs.
- **Repositories isolate persistence.** Services never import
  `AsyncSession` or write queries directly. This means: (1) the ORM can be
  swapped without touching business logic, and (2) services are unit
  testable against an in-memory fake repository, without a real Postgres.
- **`schemas/` vs `models/` are deliberately separate.** An API response
  shape and a database table shape drift over time for good reasons
  (hiding internal columns, renaming for the client, versioning). Coupling
  them forces every migration to also be an API change.
- **`agents/`, `browser/`, `prompts/` exist now, empty, on purpose.** The
  roadmap requires them; carving out the boundary today means the future
  multi-agent orchestration code has an obvious home and doesn't get bolted
  onto `services/` as an afterthought.
- **`core/` has no dependencies on the rest of the app.** Settings,
  logging, security primitives, and exceptions are the foundation every
  other layer sits on — if `core/` depended on `services/` or `models/`,
  every layer would end up circularly coupled.

## Request lifecycle (today)

1. `app/main.py` builds the FastAPI app via `create_app()`, registers
   exception handlers, and mounts `api_router`.
2. A request to `GET /health` hits `app/api/health.py`, which returns
   `{"status": "ok"}` with no dependencies — a cheap liveness probe for
   Docker/k8s.
3. Uncaught exceptions anywhere in the app are caught by the handlers in
   `app/core/exceptions.py`, logged via Loguru, and converted to a JSON
   error response instead of leaking a stack trace.

## What's intentionally NOT here yet

Per this iteration's scope: no job discovery, no resume/cover-letter
generation, no browser automation, no agent implementations. The database
layer (models, migrations, repositories, Pydantic schemas) was built in
Sprint 2 — see [docs/schema.md](docs/schema.md) for the full Career
Intelligence schema, ER diagram, and rationale. `services/`, `agents/`,
`browser/`, and `prompts/` remain empty, waiting on later sprints.
