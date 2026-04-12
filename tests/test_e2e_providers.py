"""E2E tests for provider profile endpoint."""

import secrets as stdlib_secrets

import pytest
from httpx import AsyncClient


def _uid():
    return stdlib_secrets.token_hex(6)


class TestProviderProfile:
    @pytest.mark.asyncio
    async def test_provider_profile(self, client: AsyncClient, provider_key, seed_agent):
        """Provider profile returns agents and stats."""
        _, provider_data = provider_key
        resp = await client.get(f"/v1/providers/{provider_data['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == provider_data["id"]
        assert data["name"] == "Test Provider"
        assert data["total_agents"] >= 1
        assert data["active_agents"] >= 1
        assert isinstance(data["agents"], list)
        assert len(data["agents"]) >= 1
        assert data["created_at"] is not None

    @pytest.mark.asyncio
    async def test_provider_not_found(self, client: AsyncClient):
        import uuid
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/v1/providers/{fake_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_provider_has_signing_key(self, client: AsyncClient, provider_key, seed_agent):
        _, provider_data = provider_key
        resp = await client.get(f"/v1/providers/{provider_data['id']}")
        data = resp.json()
        assert data["signing_public_key"] is not None
        assert len(data["signing_public_key"]) == 64

    @pytest.mark.asyncio
    async def test_provider_aggregated_stats(self, client: AsyncClient, provider_key, seed_agent):
        _, provider_data = provider_key
        resp = await client.get(f"/v1/providers/{provider_data['id']}")
        data = resp.json()
        assert data["total_executions"] == 0
        assert data["total_success"] == 0

    @pytest.mark.asyncio
    async def test_deprecated_agent_excluded_from_profile(
        self, client: AsyncClient, provider_key, seed_agent
    ):
        """Deprecated agents should not appear in public profile."""
        api_key, provider_data = provider_key
        # Delete the agent (soft-delete)
        await client.delete(
            f"/v1/agents/{seed_agent['id']}",
            headers={"X-API-Key": api_key},
        )
        resp = await client.get(f"/v1/providers/{provider_data['id']}")
        data = resp.json()
        agent_ids = [a["id"] for a in data["agents"]]
        assert seed_agent["id"] not in agent_ids
