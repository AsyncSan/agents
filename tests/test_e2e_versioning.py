"""E2E tests for agent versioning."""

import secrets as stdlib_secrets

import pytest
from httpx import AsyncClient


def _uid():
    return stdlib_secrets.token_hex(6)


def _agent_payload(suffix):
    return {
        "id": f"ver-agent-{suffix}",
        "name": "Versioned Agent",
        "description": "Agent for version tests",
        "domain": "testing",
        "tags": ["test"],
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
        "instructions": "Original instructions v1",
    }


class TestAgentVersioning:
    @pytest.mark.asyncio
    async def test_new_agent_starts_at_v1(self, client: AsyncClient, provider_key):
        api_key, _ = provider_key
        suffix = _uid()
        payload = _agent_payload(suffix)
        resp = await client.post(
            "/v1/agents", headers={"X-API-Key": api_key}, json=payload
        )
        assert resp.status_code == 201
        assert resp.json()["version"] == 1

    @pytest.mark.asyncio
    async def test_update_increments_version(self, client: AsyncClient, provider_key):
        api_key, _ = provider_key
        suffix = _uid()
        payload = _agent_payload(suffix)

        # Create v1
        resp = await client.post(
            "/v1/agents", headers={"X-API-Key": api_key}, json=payload
        )
        assert resp.status_code == 201
        assert resp.json()["version"] == 1

        # Update to v2
        payload["name"] = "Updated Agent v2"
        payload["instructions"] = "Updated instructions v2"
        resp = await client.put(
            f"/v1/agents/{payload['id']}",
            headers={"X-API-Key": api_key},
            json=payload,
        )
        assert resp.status_code == 200
        assert resp.json()["version"] == 2
        assert resp.json()["name"] == "Updated Agent v2"

    @pytest.mark.asyncio
    async def test_update_archives_old_version(self, client: AsyncClient, provider_key):
        api_key, _ = provider_key
        suffix = _uid()
        payload = _agent_payload(suffix)

        # Create v1
        await client.post(
            "/v1/agents", headers={"X-API-Key": api_key}, json=payload
        )

        # Update to v2
        payload["name"] = "V2 Name"
        payload["instructions"] = "V2 instructions"
        await client.put(
            f"/v1/agents/{payload['id']}",
            headers={"X-API-Key": api_key},
            json=payload,
        )

        # Check version history
        resp = await client.get(f"/v1/agents/{payload['id']}/versions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_version"] == 2
        assert len(data["versions"]) == 1  # v1 archived
        assert data["versions"][0]["version"] == 1

    @pytest.mark.asyncio
    async def test_multiple_updates_archive_all(self, client: AsyncClient, provider_key):
        api_key, _ = provider_key
        suffix = _uid()
        payload = _agent_payload(suffix)

        # Create v1
        await client.post(
            "/v1/agents", headers={"X-API-Key": api_key}, json=payload
        )
        # v2
        payload["instructions"] = "v2"
        await client.put(
            f"/v1/agents/{payload['id']}",
            headers={"X-API-Key": api_key},
            json=payload,
        )
        # v3
        payload["instructions"] = "v3"
        await client.put(
            f"/v1/agents/{payload['id']}",
            headers={"X-API-Key": api_key},
            json=payload,
        )

        resp = await client.get(f"/v1/agents/{payload['id']}/versions")
        data = resp.json()
        assert data["current_version"] == 3
        assert len(data["versions"]) == 2  # v1 and v2 archived
        versions = sorted([v["version"] for v in data["versions"]])
        assert versions == [1, 2]

    @pytest.mark.asyncio
    async def test_versions_not_found(self, client: AsyncClient):
        resp = await client.get("/v1/agents/nonexistent/versions")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_versions_empty_for_new_agent(
        self, client: AsyncClient, provider_key
    ):
        api_key, _ = provider_key
        suffix = _uid()
        payload = _agent_payload(suffix)
        await client.post(
            "/v1/agents", headers={"X-API-Key": api_key}, json=payload
        )

        resp = await client.get(f"/v1/agents/{payload['id']}/versions")
        data = resp.json()
        assert data["current_version"] == 1
        assert data["versions"] == []

    @pytest.mark.asyncio
    async def test_archived_version_has_old_card(
        self, client: AsyncClient, provider_key
    ):
        api_key, _ = provider_key
        suffix = _uid()
        payload = _agent_payload(suffix)

        await client.post(
            "/v1/agents", headers={"X-API-Key": api_key}, json=payload
        )
        # Update with different domain
        payload["domain"] = "updated-domain"
        payload["instructions"] = "updated"
        await client.put(
            f"/v1/agents/{payload['id']}",
            headers={"X-API-Key": api_key},
            json=payload,
        )

        resp = await client.get(f"/v1/agents/{payload['id']}/versions")
        v1_card = resp.json()["versions"][0]["card"]
        assert v1_card["capabilities"]["domain"] == "testing"  # original domain

    @pytest.mark.asyncio
    async def test_card_version_field_matches(self, client: AsyncClient, provider_key):
        api_key, _ = provider_key
        suffix = _uid()
        payload = _agent_payload(suffix)

        await client.post(
            "/v1/agents", headers={"X-API-Key": api_key}, json=payload
        )
        payload["instructions"] = "v2"
        resp = await client.put(
            f"/v1/agents/{payload['id']}",
            headers={"X-API-Key": api_key},
            json=payload,
        )
        # Card's internal version field should match agent version
        assert resp.json()["card"]["version"] == 2
