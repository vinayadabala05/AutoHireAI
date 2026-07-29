#!/usr/bin/env bash
# Container entrypoint: wait for Postgres, run migrations, then start the API.
set -euo pipefail

echo "Waiting for Postgres at ${POSTGRES_HOST}:${POSTGRES_PORT}..."
until python -c "
import socket, os, sys
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(1)
try:
    s.connect((os.environ['POSTGRES_HOST'], int(os.environ['POSTGRES_PORT'])))
except OSError:
    sys.exit(1)
"; do
  sleep 1
done

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting API..."
exec uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"
