# scripts/

Operational scripts that don't belong in `app/` (not part of the request/
response cycle).

- `entrypoint.sh` — container entrypoint: waits for Postgres, runs Alembic
  migrations, then starts uvicorn. Not wired into the `Dockerfile` yet in
  this foundation iteration (the API currently starts with no migrations
  applied); switch the Dockerfile's `CMD` to this script once real models
  and migrations exist.
