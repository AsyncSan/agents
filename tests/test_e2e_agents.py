"""E2E tests for agent registry, discovery, and signing."""

import secrets as stdlib_secrets

import pytest
from httpx import AsyncClient


def _uid():
    return stdlib_secrets.token_hex(6)


class TestAgentCRUD:
    @pytest.mark.asyncio
    async def test_create_agent(self, client: AsyncClient, provider_key):
        api_key, _ = provider_key
        resp = await client.post(
            "/v1/agents",
            headers={"X-API-Key": api_key},
            json={
                "id": f"crud-{_uid()}",
                "name": "CRUD Test Agent",
                "description": "For testing CRUD",
                "domain": "testing",
                "tags": ["crud", "test"],
                "inputs": [{"name": "query", "type": "string"}],
                "outputs": [{"name": "output.md", "type": "markdown"}],
                "pricing": {"model": "per_execution", "base_price_usd": 2.50},
                "instructions": "Do the thing",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"].startswith("crud-")
        assert data["signature"] is not None  # should be signed
        assert data["signing_public_key"] is not None
        # Provider sees instructions
        assert "instructions" in data["card"]

    @pytest.mark.asyncio
    async def test_get_agent_public(self, client: AsyncClient, seed_agent):
        resp = await client.get(f"/v1/agents/{seed_agent['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == seed_agent["id"]
        # Public: no instructions
        assert "instructions" not in data["card"]
        assert data["trust_score"] is None  # no executions yet

    @pytest.mark.asyncio
    async def test_get_agent_not_found(self, client: AsyncClient):
        resp = await client.get("/v1/agents/nonexistent-agent-xyz")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_duplicate_agent_id_rejected(self, client: AsyncClient, provider_key):
        api_key, _ = provider_key
        agent_id = f"dup-{_uid()}"
        # Create first
        resp1 = await client.post(
            "/v1/agents",
            headers={"X-API-Key": api_key},
            json={"id": agent_id, "name": "First", "domain": "test", "instructions": "ok"},
        )
        assert resp1.status_code == 201
        # Duplicate
        resp2 = await client.post(
            "/v1/agents",
            headers={"X-API-Key": api_key},
            json={"id": agent_id, "name": "Second", "domain": "test", "instructions": "nope"},
        )
        assert resp2.status_code == 409

    @pytest.mark.asyncio
    async def test_update_agent(self, client: AsyncClient, provider_key, seed_agent):
        api_key, _ = provider_key
        resp = await client.put(
            f"/v1/agents/{seed_agent['id']}",
            headers={"X-API-Key": api_key},
            json={
                "id": seed_agent["id"],
                "name": "Updated Agent Name",
                "description": "Updated description",
                "domain": "testing",
                "tags": ["updated"],
                "pricing": {"model": "per_execution", "base_price_usd": 5.00},
                "instructions": "New instructions",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated Agent Name"
        assert data["signature"] is not None  # re-signed

    @pytest.mark.asyncio
    async def test_delete_agent(self, client: AsyncClient, provider_key):
        api_key, _ = provider_key
        agent_id = f"del-{_uid()}"
        await client.post(
            "/v1/agents",
            headers={"X-API-Key": api_key},
            json={
                "id": agent_id,
                "name": "Delete Me",
                "domain": "test",
                "instructions": "bye",
            },
        )
        resp = await client.delete(
            f"/v1/agents/{agent_id}",
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 204

        # Should not appear in active list
        resp = await client.get("/v1/agents?status=active")
        agent_ids = [a["id"] for a in resp.json()["agents"]]
        assert agent_id not in agent_ids


class TestAgentDiscovery:
    @pytest.mark.asyncio
    async def test_list_agents_default(self, client: AsyncClient, seed_agent):
        resp = await client.get("/v1/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any(a["id"] == seed_agent["id"] for a in data["agents"])

    @pytest.mark.asyncio
    async def test_search_by_text(self, client: AsyncClient, seed_agent):
        resp = await client.get("/v1/agents?q=Integration")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_filter_by_domain(self, client: AsyncClient, seed_agent):
        resp = await client.get("/v1/agents?domain=testing")
        assert resp.status_code == 200
        assert all(
            a["card"]["capabilities"]["domain"] == "testing"
            for a in resp.json()["agents"]
        )

    @pytest.mark.asyncio
    async def test_filter_by_tag(self, client: AsyncClient, seed_agent):
        resp = await client.get("/v1/agents?tag=integration")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    @pytest.mark.asyncio
    async def test_filter_by_max_price(self, client: AsyncClient, seed_agent):
        resp = await client.get("/v1/agents?max_price_usd=0.50")
        assert resp.status_code == 200
        # seed_agent is $1, should not appear
        agent_ids = [a["id"] for a in resp.json()["agents"]]
        assert seed_agent["id"] not in agent_ids

    @pytest.mark.asyncio
    async def test_sort_by_newest(self, client: AsyncClient, seed_agent):
        resp = await client.get("/v1/agents?sort_by=newest")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    @pytest.mark.asyncio
    async def test_pagination(self, client: AsyncClient, seed_agent):
        resp = await client.get("/v1/agents?limit=1&offset=0")
        assert resp.status_code == 200
        assert len(resp.json()["agents"]) <= 1

    @pytest.mark.asyncio
    async def test_categories(self, client: AsyncClient, seed_agent):
        resp = await client.get("/v1/agents/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert "domains" in data
        assert "tags" in data
        assert any(d["name"] == "testing" for d in data["domains"])


class TestAgentSigning:
    @pytest.mark.asyncio
    async def test_verify_valid_signature(self, client: AsyncClient, seed_agent):
        resp = await client.get(f"/v1/agents/{seed_agent['id']}/verify")
        assert resp.status_code == 200
        data = resp.json()
        assert data["verified"] is True
        assert data["agent_id"] == seed_agent["id"]
        assert data["signing_public_key"] is not None

    @pytest.mark.asyncio
    async def test_verify_nonexistent_agent(self, client: AsyncClient):
        resp = await client.get("/v1/agents/ghost-agent/verify")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_signature_present_in_response(self, client: AsyncClient, seed_agent):
        resp = await client.get(f"/v1/agents/{seed_agent['id']}")
        data = resp.json()
        assert data["signature"] is not None
        assert len(data["signature"]) == 128  # 64 bytes hex
