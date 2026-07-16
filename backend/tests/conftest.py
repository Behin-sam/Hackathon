"""
Shared pytest fixtures for integration tests.

These tests exercise the real API against a real Postgres database — start
one with:

    docker compose up -d db redis

then run:

    cd backend && pytest

`DATABASE_URL` (see app/core/config.py) must point at a disposable database;
these fixtures create and drop all tables around the test session and wipe
row data between individual tests.
"""
import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db.base import Base
from app.db.seed import seed_roles_permissions, seed_super_admin, SUPER_ADMIN_EMAIL, SUPER_ADMIN_PASSWORD
from app.db.session import AsyncSessionLocal, engine
from app.main import app

# Ensure every model module is imported so Base.metadata is fully populated.
import app.models  # noqa: F401


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_schema():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        await seed_roles_permissions(db)
        await seed_super_admin(db)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _clean_user_data():
    """Wipe user-generated rows between tests, but keep seeded roles/permissions."""
    yield
    async with engine.begin() as conn:
        for table in (
            "audit_logs",
            "identity_signals",
            "identity_verification_history",
            "identity",
            "mfa",
            "refresh_tokens",
            "sessions",
            "user_roles",
            "users",
        ):
            await conn.execute(text(f'DELETE FROM "{table}"'))

    # Re-seed the super admin so role/permission-dependent tests keep working.
    async with AsyncSessionLocal() as db:
        await seed_super_admin(db)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def admin_tokens(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest_asyncio.fixture
async def admin_headers(admin_tokens):
    return {"Authorization": f"Bearer {admin_tokens['access_token']}"}
