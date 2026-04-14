"""Tests for agent compatibility/recommendation endpoint."""

import pytest
from httpx import AsyncClient


class TestAgentCompatibility:
    @pytest.mark.asyncio
    async def test_downstream_compatible(
        self, client: AsyncClient, provider_key
    ):
        """Find agents whose inputs match this agent's outputs."""
        api_key, _ = provider_key

        # Create source agent with markdown output
        await client.post(
            "/v1/agents",
            headers={"X-API-Key": api_key},
            json={
                "id": "compat-source",
                "name": "Source Agent",
                "description": "Produces markdown",
                "domain": "research",
                "tags": [],
                "inputs": [{"name": "topic", "type": "string"}],
                "outputs": [
                    {"name": "output.md", "type": "markdown"},
                    {"name": "output.json", "type": "json"},
                ],
                "runtime": {"estimated_duration_seconds": 60},
                "pricing": {"base_price_usd": 1.00},
                "instructions": "Research agent",
            },
        )

        # Create downstream agent that consumes markdown
        await client.post(
            "/v1/agents",
            headers={"X-API-Key": api_key},
            json={
                "id": "compat-consumer",
                "name": "Consumer Agent",
                "description": "Consumes markdown",
                "domain": "content",
                "tags": [],
                "inputs": [
                    {"name": "text", "type": "markdown"},
                    {"name": "format", "type": "string"},
                ],
                "outputs": [{"name": "output.md", "type": "markdown"}],
                "runtime": {"estimated_duration_seconds": 30},
                "pricing": {"base_price_usd": 0.50},
                "instructions": "Summarize",
            },
        )

        # Create unrelated agent
        await client.post(
            "/v1/agents",
            headers={"X-API-Key": api_key},
            json={
                "id": "compat-unrelated",
                "name": "Unrelated Agent",
                "description": "Does other stuff",
                "domain": "benchmark",
                "tags": [],
                "inputs": [{"name": "binary", "type": "binary"}],
                "outputs": [{"name": "output.json", "type": "json"}],
                "runtime": {"estimated_duration_seconds": 120},
                "pricing": {"base_price_usd": 2.00},
                "instructions": "Benchmark",
            },
        )

        resp = await client.get("/v1/agents/compat-source/compatible")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == "compat-source"
        assert data["direction"] == "downstream"

        # Consumer agent should be in results (markdown input matches)
        agent_ids = [c["agent"]["id"] for c in data["compatible"]]
        assert "compat-consumer" in agent_ids

        # Check matching fields
        consumer_match = next(
            c for c in data["compatible"]
            if c["agent"]["id"] == "compat-consumer"
        )
        assert any("markdown" in m for m in consumer_match["matching_fields"])

    @pytest.mark.asyncio
    async def test_upstream_compatible(
        self, client: AsyncClient, provider_key
    ):
        """Find agents whose outputs match this agent's inputs."""
        api_key, _ = provider_key

        # Reuse agents from previous test (already created)
        resp = await client.get(
            "/v1/agents/compat-consumer/compatible?direction=upstream"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["direction"] == "upstream"

        # Source agent produces markdown, consumer accepts markdown
        agent_ids = [c["agent"]["id"] for c in data["compatible"]]
        assert "compat-source" in agent_ids

    @pytest.mark.asyncio
    async def test_not_found(self, client: AsyncClient):
        """Returns 404 for non-existent agent."""
        resp = await client.get("/v1/agents/ghost-agent/compatible")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_same_domain_weak_match(
        self, client: AsyncClient, provider_key
    ):
        """Agents in same domain show as weak matches."""
        api_key, _ = provider_key

        await client.post(
            "/v1/agents",
            headers={"X-API-Key": api_key},
            json={
                "id": "compat-research-2",
                "name": "Research Agent 2",
                "description": "Another research agent",
                "domain": "research",
                "tags": [],
                "inputs": [{"name": "query", "type": "string"}],
                "outputs": [{"name": "output.md", "type": "markdown"}],
                "runtime": {"estimated_duration_seconds": 60},
                "pricing": {"base_price_usd": 1.00},
                "instructions": "Research",
            },
        )

        resp = await client.get("/v1/agents/compat-source/compatible")
        data = resp.json()

        # research-2 should appear (same domain or type match)
        agent_ids = [c["agent"]["id"] for c in data["compatible"]]
        assert "compat-research-2" in agent_ids

    @pytest.mark.asyncio
    async def test_limit_param(self, client: AsyncClient, provider_key):
        """Limit parameter caps results."""
        resp = await client.get(
            "/v1/agents/compat-source/compatible?limit=1"
        )
        assert resp.status_code == 200
        assert len(resp.json()["compatible"]) <= 1
