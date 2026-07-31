# syntax=docker/dockerfile:1
#
# Production image for the deployment layer's entrypoint
# (`deployment.startup:app`), distinct from the project-root `Dockerfile`
# (which runs `app.main:app`, the plain Sprint 1 app, for local/dev use).
# Multi-stage: dependencies are installed once in `builder` and copied
# into a slim runtime stage that never sees Poetry, a compiler, or a
# `pyproject.toml`, and runs as a non-root user.

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.8.3 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

ENV PATH="$POETRY_HOME/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl build-essential libpq-dev \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && apt-get purge -y curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/app
COPY pyproject.toml ./
RUN poetry install --no-root --only main

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/srv/app/.venv/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 autohire

WORKDIR /srv/app
COPY --from=builder /srv/app/.venv /srv/app/.venv
COPY app ./app
COPY deployment ./deployment
COPY alembic ./alembic
COPY alembic.ini ./

RUN mkdir -p logs data && chown -R autohire:autohire /srv/app

USER autohire
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/health/ready || exit 1

CMD ["uvicorn", "deployment.startup:app", "--host", "0.0.0.0", "--port", "8000"]
