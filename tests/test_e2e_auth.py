"""E2E tests for authentication and registration flow."""

import secrets as stdlib_secrets

import pytest
from httpx import AsyncClient


def _uid():
    return stdlib_secrets.token_hex(6)


class TestHealthz:
    @pytest.mark.asyncio
    async def test_healthz(self, client: AsyncClient):
        resp = await client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestRegistration:
    @pytest.mark.asyncio
    async def test_register_provider(self, client: AsyncClient):
        resp = await client.post(
            "/v1/auth/register",
            json={"name": "Alice", "email": f"alice-{_uid()}@test.com", "role": "provider"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "provider"
        assert data["api_key"].startswith("af_")
        assert data["signing_public_key"] is not None
        assert len(data["signing_public_key"]) == 64  # 32 bytes hex

    @pytest.mark.asyncio
    async def test_register_consumer(self, client: AsyncClient):
        resp = await client.post(
            "/v1/auth/register",
            json={"name": "Bob", "email": f"bob-{_uid()}@test.com", "role": "consumer"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "consumer"
        assert data["api_key"].startswith("af_")
        assert data["signing_public_key"] is None  # consumers don't get keys

    @pytest.mark.asyncio
    async def test_duplicate_email_rejected(self, client: AsyncClient):
        email = f"dup-{_uid()}@test.com"
        await client.post(
            "/v1/auth/register",
            json={"name": "First", "email": email, "role": "provider"},
        )
        resp = await client.post(
            "/v1/auth/register",
            json={"name": "Second", "email": email, "role": "provider"},
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_invalid_role_rejected(self, client: AsyncClient):
        resp = await client.post(
            "/v1/auth/register",
            json={"name": "Bad", "email": f"bad-{_uid()}@test.com", "role": "admin"},
        )
        assert resp.status_code == 422


class TestAPIKeyAuth:
    @pytest.mark.asyncio
    async def test_valid_key_accesses_endpoints(self, client: AsyncClient, consumer_key):
        api_key, _ = consumer_key
        resp = await client.get(
            "/v1/tasks", headers={"X-API-Key": api_key}
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_invalid_key_rejected(self, client: AsyncClient):
        resp = await client.get(
            "/v1/tasks", headers={"X-API-Key": "af_invalid_garbage"}
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_key_rejected(self, client: AsyncClient):
        resp = await client.get("/v1/tasks")
        assert resp.status_code in (401, 403)  # depends on FastAPI security config

    @pytest.mark.asyncio
    async def test_consumer_cannot_create_agent(self, client: AsyncClient, consumer_key):
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/agents",
            headers={"X-API-Key": api_key},
            json={
                "id": f"hack-{_uid()}",
                "name": "Hack",
                "domain": "test",
                "instructions": "nope",
            },
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_provider_cannot_create_task(self, client: AsyncClient, provider_key, seed_agent):
        api_key, _ = provider_key
        resp = await client.post(
            "/v1/tasks",
            headers={"X-API-Key": api_key},
            json={"agent_id": seed_agent["id"], "inputs": {"topic": "test"}},
        )
        assert resp.status_code == 403
