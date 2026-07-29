"""Shared pytest fixtures.

`db_session` talks to a real PostgreSQL instance (configured the same way
the app is, via `app.core.settings`) rather than SQLite — the schema uses
Postgres-only types (`ARRAY`, `JSONB`, native `ENUM`), so a lighter-weight
substitute wouldn't actually exercise the same DDL. The schema is created
fresh and torn down around every test for full isolation; this trades some
speed for simplicity, which is the right call at this test-suite size.
"""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app import models as _models  # noqa: F401  registers all tables on Base.metadata
from app.core.settings import settings
from app.database.base import Base
from app.main import app


@pytest.fixture
async def client() -> AsyncClient:
    """An async HTTP client bound directly to the ASGI app (no live server)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """A fresh schema + session for a single test.

    Requires a reachable PostgreSQL instance at `settings.DATABASE_URL`
    (see `docker compose up -d postgres`). `NullPool` avoids reusing
    connections across the create/drop cycle within one test.
    """
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
