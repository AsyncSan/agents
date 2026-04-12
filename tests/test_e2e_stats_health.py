"""E2E tests for agent stats, health, and featured endpoints."""

import secrets as stdlib_secrets

import pytest
from httpx import AsyncClient


def _uid():
    return stdlib_secrets.token_hex(6)


class TestAgentStats:
    @pytest.mark.asyncio
    async def test_stats_for_agent(self, client: AsyncClient, seed_agent):
        """Stats endpoint returns valid data for an existing agent."""
        resp = await client.get(f"/v1/agents/{seed_agent['id']}/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == seed_agent["id"]
        assert data["total_executions"] == 0
        assert data["success_count"] == 0
        assert data["failure_count"] == 0
        assert data["success_rate"] == 0.0
        assert data["total_revenue_cents"] == 0
        assert isinstance(data["recent_executions"], list)

    @pytest.mark.asyncio
    async def test_stats_not_found(self, client: AsyncClient):
        resp = await client.get("/v1/agents/nonexistent-agent/stats")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_stats_trust_score_none_initially(self, client: AsyncClient, seed_agent):
        resp = await client.get(f"/v1/agents/{seed_agent['id']}/stats")
        data = resp.json()
        assert data["trust_score"] is None
        assert data["avg_duration_seconds"] is None


class TestAgentHealth:
    @pytest.mark.asyncio
    async def test_health_dormant_agent(self, client: AsyncClient, seed_agent):
        """New agent with no executions should be dormant."""
        resp = await client.get(f"/v1/agents/{seed_agent['id']}/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == seed_agent["id"]
        assert data["status"] == "dormant"
        assert data["uptime_status"] == "new"
        assert data["consecutive_failures"] == 0
        assert data["executions_24h"] == 0
        assert data["last_execution_at"] is None

    @pytest.mark.asyncio
    async def test_health_not_found(self, client: AsyncClient):
        resp = await client.get("/v1/agents/nonexistent-agent/health")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_health_response_fields(self, client: AsyncClient, seed_agent):
        resp = await client.get(f"/v1/agents/{seed_agent['id']}/health")
        data = resp.json()
        expected_fields = {
            "agent_id", "status", "last_execution_at", "consecutive_failures",
            "success_rate_24h", "avg_duration_24h", "executions_24h", "uptime_status"
        }
        assert expected_fields == set(data.keys())


class TestFeaturedAgents:
    @pytest.mark.asyncio
    async def test_featured_returns_structure(self, client: AsyncClient):
        resp = await client.get("/v1/agents/featured")
        assert resp.status_code == 200
        data = resp.json()
        assert "trending" in data
        assert "top_rated" in data
        assert "newest" in data
        assert isinstance(data["trending"], list)
        assert isinstance(data["top_rated"], list)
        assert isinstance(data["newest"], list)

    @pytest.mark.asyncio
    async def test_featured_includes_seed_in_newest(self, client: AsyncClient, seed_agent):
        resp = await client.get("/v1/agents/featured")
        data = resp.json()
        newest_ids = [a["id"] for a in data["newest"]]
        assert seed_agent["id"] in newest_ids

    @pytest.mark.asyncio
    async def test_featured_limit_param(self, client: AsyncClient, seed_agent):
        resp = await client.get("/v1/agents/featured?limit=1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["newest"]) <= 1

    @pytest.mark.asyncio
    async def test_trending_has_score(self, client: AsyncClient, seed_agent):
        """Trending entries should have a trending_score field."""
        resp = await client.get("/v1/agents/featured")
        data = resp.json()
        for entry in data["trending"]:
            assert "agent" in entry
            assert "trending_score" in entry
            assert isinstance(entry["trending_score"], (int, float))
