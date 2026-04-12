"""E2E tests for pipeline creation and validation."""

import secrets as stdlib_secrets

import pytest
from httpx import AsyncClient


def _uid():
    return stdlib_secrets.token_hex(6)


class TestPipelineCreation:
    @pytest.mark.asyncio
    async def test_create_pipeline(self, client: AsyncClient, consumer_key, seed_agent):
        api_key, _ = consumer_key
        agent_id = seed_agent["id"]

        resp = await client.post(
            "/v1/pipelines",
            headers={"X-API-Key": api_key},
            json={
                "steps": [
                    {"agent_id": agent_id, "inputs": {"topic": "AI"}},
                    {"agent_id": agent_id, "output_map": {"output.md": "research"}},
                ],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"].startswith("pl-")
        assert data["status"] == "pending"
        assert len(data["steps"]) == 2
        assert data["chain_trust_score"] is not None
        assert len(data["tasks"]) == 1  # only first task created

    @pytest.mark.asyncio
    async def test_pipeline_with_callback(self, client: AsyncClient, consumer_key, seed_agent):
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/pipelines",
            headers={"X-API-Key": api_key},
            json={
                "steps": [
                    {"agent_id": seed_agent["id"], "inputs": {"topic": "test"}},
                    {"agent_id": seed_agent["id"]},
                ],
                "callback_url": "https://example.com/pipeline-done",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["callback_url"] == "https://example.com/pipeline-done"

    @pytest.mark.asyncio
    async def test_pipeline_min_two_steps(self, client: AsyncClient, consumer_key, seed_agent):
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/pipelines",
            headers={"X-API-Key": api_key},
            json={"steps": [{"agent_id": seed_agent["id"]}]},
        )
        assert resp.status_code == 422  # validation error

    @pytest.mark.asyncio
    async def test_pipeline_nonexistent_agent(self, client: AsyncClient, consumer_key, seed_agent):
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/pipelines",
            headers={"X-API-Key": api_key},
            json={
                "steps": [
                    {"agent_id": seed_agent["id"]},
                    {"agent_id": "ghost-agent"},
                ],
            },
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_pipeline_budget_enforcement(self, client: AsyncClient, consumer_key, seed_agent):
        api_key, _ = consumer_key
        # 2 steps * $1 = $2, cap at $1.50
        resp = await client.post(
            "/v1/pipelines",
            headers={"X-API-Key": api_key},
            json={
                "steps": [
                    {"agent_id": seed_agent["id"]},
                    {"agent_id": seed_agent["id"]},
                ],
                "constraints": {"max_cost_usd": 1.50},
            },
        )
        assert resp.status_code == 400
        assert "exceeds budget" in resp.json()["detail"]


class TestPipelineRetrieval:
    @pytest.mark.asyncio
    async def test_get_pipeline(self, client: AsyncClient, consumer_key, seed_agent):
        api_key, _ = consumer_key
        create_resp = await client.post(
            "/v1/pipelines",
            headers={"X-API-Key": api_key},
            json={
                "steps": [
                    {"agent_id": seed_agent["id"], "inputs": {"topic": "get-test"}},
                    {"agent_id": seed_agent["id"]},
                ],
            },
        )
        pipeline_id = create_resp.json()["id"]

        resp = await client.get(
            f"/v1/pipelines/{pipeline_id}", headers={"X-API-Key": api_key}
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == pipeline_id

    @pytest.mark.asyncio
    async def test_get_pipeline_not_found(self, client: AsyncClient, consumer_key):
        api_key, _ = consumer_key
        resp = await client.get(
            "/v1/pipelines/pl-nonexistent", headers={"X-API-Key": api_key}
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_pipelines(self, client: AsyncClient, consumer_key, seed_agent):
        api_key, _ = consumer_key
        await client.post(
            "/v1/pipelines",
            headers={"X-API-Key": api_key},
            json={
                "steps": [
                    {"agent_id": seed_agent["id"], "inputs": {"topic": "list-test"}},
                    {"agent_id": seed_agent["id"]},
                ],
            },
        )

        resp = await client.get(
            "/v1/pipelines", headers={"X-API-Key": api_key}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1


class TestPipelineIsolation:
    @pytest.mark.asyncio
    async def test_consumer_cannot_see_others_pipeline(
        self, client: AsyncClient, seed_agent
    ):
        r1 = await client.post(
            "/v1/auth/register",
            json={"name": "P1", "email": f"p1-{_uid()}@test.com", "role": "consumer"},
        )
        r2 = await client.post(
            "/v1/auth/register",
            json={"name": "P2", "email": f"p2-{_uid()}@test.com", "role": "consumer"},
        )
        key1 = r1.json()["api_key"]
        key2 = r2.json()["api_key"]

        create_resp = await client.post(
            "/v1/pipelines",
            headers={"X-API-Key": key1},
            json={
                "steps": [
                    {"agent_id": seed_agent["id"], "inputs": {"topic": "secret"}},
                    {"agent_id": seed_agent["id"]},
                ],
            },
        )
        pipeline_id = create_resp.json()["id"]

        resp = await client.get(
            f"/v1/pipelines/{pipeline_id}", headers={"X-API-Key": key2}
        )
        assert resp.status_code == 403
