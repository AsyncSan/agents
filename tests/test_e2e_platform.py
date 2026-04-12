"""E2E tests for platform health and event log."""

import pytest
from httpx import AsyncClient


class TestPlatformHealth:
    @pytest.mark.asyncio
    async def test_platform_health(self, client: AsyncClient):
        resp = await client.get("/v1/platform/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("ok", "degraded", "down")
        assert data["version"] == "0.1.0"
        assert isinstance(data["components"], list)
        assert len(data["components"]) >= 3  # db, compute, payments, worker
        assert "pending_tasks" in data
        assert "total_agents" in data
        assert "total_executions_24h" in data

    @pytest.mark.asyncio
    async def test_platform_health_db_component(self, client: AsyncClient):
        resp = await client.get("/v1/platform/health")
        data = resp.json()
        db_comp = next(c for c in data["components"] if c["name"] == "database")
        assert db_comp["status"] == "ok"
        assert db_comp["latency_ms"] is not None
        assert db_comp["latency_ms"] >= 0

    @pytest.mark.asyncio
    async def test_platform_health_worker_status(self, client: AsyncClient):
        resp = await client.get("/v1/platform/health")
        data = resp.json()
        worker = next(c for c in data["components"] if c["name"] == "worker")
        # In test env, hcloud_token is empty so worker is degraded
        assert worker["status"] in ("ok", "degraded")


class TestEventLog:
    @pytest.mark.asyncio
    async def test_events_requires_auth(self, client: AsyncClient):
        resp = await client.get("/v1/events")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_events_after_agent_create(
        self, client: AsyncClient, provider_key, seed_agent
    ):
        """Creating an agent should generate an event."""
        api_key, _ = provider_key
        resp = await client.get(
            "/v1/events",
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["events"], list)
        assert data["total"] >= 1
        # Should have an agent.created event
        types = [e["event_type"] for e in data["events"]]
        assert "agent.created" in types

    @pytest.mark.asyncio
    async def test_events_filtered_by_type(
        self, client: AsyncClient, provider_key, seed_agent
    ):
        api_key, _ = provider_key
        resp = await client.get(
            "/v1/events?event_type=agent.created",
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        for event in data["events"]:
            assert event["event_type"] == "agent.created"

    @pytest.mark.asyncio
    async def test_events_filtered_by_resource(
        self, client: AsyncClient, provider_key, seed_agent
    ):
        api_key, _ = provider_key
        resp = await client.get(
            f"/v1/events?resource_id={seed_agent['id']}",
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        for event in data["events"]:
            assert event["resource_id"] == seed_agent["id"]

    @pytest.mark.asyncio
    async def test_events_pagination(self, client: AsyncClient, provider_key, seed_agent):
        api_key, _ = provider_key
        resp = await client.get(
            "/v1/events?limit=1&offset=0",
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["events"]) <= 1
