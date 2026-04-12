"""Shared fixtures for integration and E2E tests.

Uses a real PostgreSQL test database (agentforge_test) with table
creation/teardown per session.
"""

import secrets as stdlib_secrets

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DB_URL = "postgresql+asyncpg://agentforge:changeme@localhost:5433/agentforge_test"


def _unique_suffix():
    return stdlib_secrets.token_hex(6)


@pytest.fixture(scope="session")
async def engine():
    from agentforge.models.base import Base

    eng = create_async_engine(TEST_DB_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture(scope="session")
async def session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def db_session(session_factory):
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(session_factory):
    """HTTPX async client wired to the FastAPI app with test DB override."""
    from agentforge.api.app import app
    from agentforge.db import get_db

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# --- Helper fixtures ---


@pytest.fixture
async def provider_key(client: AsyncClient) -> tuple[str, dict]:
    """Register a provider and return (api_key, response_data)."""
    suffix = _unique_suffix()
    resp = await client.post(
        "/v1/auth/register",
        json={"name": "Test Provider", "email": f"provider-{suffix}@test.com", "role": "provider"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    return data["api_key"], data


@pytest.fixture
async def consumer_key(client: AsyncClient) -> tuple[str, dict]:
    """Register a consumer and return (api_key, response_data)."""
    suffix = _unique_suffix()
    resp = await client.post(
        "/v1/auth/register",
        json={"name": "Test Consumer", "email": f"consumer-{suffix}@test.com", "role": "consumer"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    return data["api_key"], data


@pytest.fixture
async def seed_agent(client: AsyncClient, provider_key: tuple[str, dict]) -> dict:
    """Create a test agent and return the response dict."""
    api_key, _ = provider_key
    suffix = _unique_suffix()
    resp = await client.post(
        "/v1/agents",
        headers={"X-API-Key": api_key},
        json={
            "id": f"test-agent-{suffix}",
            "name": "Integration Test Agent",
            "description": "Agent for E2E tests",
            "domain": "testing",
            "tags": ["test", "integration"],
            "inputs": [{"name": "topic", "type": "string", "required": True}],
            "outputs": [{"name": "output.md", "type": "markdown", "guaranteed": True}],
            "runtime": {
                "snapshot_profile": "base",
                "server_type": "cax11",
                "model": "anthropic/claude-sonnet-4-6",
                "tools": ["shell"],
                "estimated_duration_seconds": 60,
                "estimated_cost_usd": 0.50,
            },
            "pricing": {"model": "per_execution", "base_price_usd": 1.00},
            "instructions": "You are a test agent. Output a report.",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()
