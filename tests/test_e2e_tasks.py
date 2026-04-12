"""E2E tests for task submission, listing, and budget enforcement."""

import secrets as stdlib_secrets

import pytest
from httpx import AsyncClient


def _uid():
    return stdlib_secrets.token_hex(6)


class TestTaskSubmission:
    @pytest.mark.asyncio
    async def test_create_task(self, client: AsyncClient, consumer_key, seed_agent):
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/tasks",
            headers={"X-API-Key": api_key},
            json={
                "agent_id": seed_agent["id"],
                "inputs": {"topic": "quantum computing"},
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["agent_id"] == seed_agent["id"]
        assert data["status"] == "pending"
        assert data["id"].startswith("tc-")

    @pytest.mark.asyncio
    async def test_create_task_with_callback(self, client: AsyncClient, consumer_key, seed_agent):
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/tasks",
            headers={"X-API-Key": api_key},
            json={
                "agent_id": seed_agent["id"],
                "inputs": {"topic": "AI"},
                "callback_url": "https://example.com/webhook",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["callback_url"] == "https://example.com/webhook"

    @pytest.mark.asyncio
    async def test_create_task_nonexistent_agent(self, client: AsyncClient, consumer_key):
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/tasks",
            headers={"X-API-Key": api_key},
            json={"agent_id": "nonexistent-agent", "inputs": {}},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_budget_enforcement_rejects(self, client: AsyncClient, consumer_key, seed_agent):
        api_key, _ = consumer_key
        # seed_agent costs $1.00, cap at $0.50
        resp = await client.post(
            "/v1/tasks",
            headers={"X-API-Key": api_key},
            json={
                "agent_id": seed_agent["id"],
                "inputs": {"topic": "test"},
                "constraints": {"max_cost_usd": 0.50},
            },
        )
        assert resp.status_code == 400
        assert "exceeds budget" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_budget_enforcement_accepts(self, client: AsyncClient, consumer_key, seed_agent):
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/tasks",
            headers={"X-API-Key": api_key},
            json={
                "agent_id": seed_agent["id"],
                "inputs": {"topic": "test"},
                "constraints": {"max_cost_usd": 10.00},
            },
        )
        assert resp.status_code == 201


class TestTaskRetrieval:
    @pytest.mark.asyncio
    async def test_get_task(self, client: AsyncClient, consumer_key, seed_agent):
        api_key, _ = consumer_key
        create_resp = await client.post(
            "/v1/tasks",
            headers={"X-API-Key": api_key},
            json={"agent_id": seed_agent["id"], "inputs": {"topic": "test"}},
        )
        task_id = create_resp.json()["id"]

        resp = await client.get(
            f"/v1/tasks/{task_id}", headers={"X-API-Key": api_key}
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == task_id

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, client: AsyncClient, consumer_key):
        api_key, _ = consumer_key
        resp = await client.get(
            "/v1/tasks/tc-nonexistent", headers={"X-API-Key": api_key}
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_tasks(self, client: AsyncClient, consumer_key, seed_agent):
        api_key, _ = consumer_key
        # Create a task first
        await client.post(
            "/v1/tasks",
            headers={"X-API-Key": api_key},
            json={"agent_id": seed_agent["id"], "inputs": {"topic": "list test"}},
        )

        resp = await client.get(
            "/v1/tasks", headers={"X-API-Key": api_key}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["tasks"]) >= 1

    @pytest.mark.asyncio
    async def test_list_tasks_filter_status(self, client: AsyncClient, consumer_key, seed_agent):
        api_key, _ = consumer_key
        await client.post(
            "/v1/tasks",
            headers={"X-API-Key": api_key},
            json={"agent_id": seed_agent["id"], "inputs": {"topic": "filter test"}},
        )

        resp = await client.get(
            "/v1/tasks?status=pending", headers={"X-API-Key": api_key}
        )
        assert resp.status_code == 200
        assert all(t["status"] == "pending" for t in resp.json()["tasks"])


class TestTaskIsolation:
    @pytest.mark.asyncio
    async def test_consumer_cannot_see_others_tasks(self, client: AsyncClient, seed_agent):
        # Register two consumers
        r1 = await client.post(
            "/v1/auth/register",
            json={"name": "C1", "email": f"c1-{_uid()}@test.com", "role": "consumer"},
        )
        r2 = await client.post(
            "/v1/auth/register",
            json={"name": "C2", "email": f"c2-{_uid()}@test.com", "role": "consumer"},
        )
        key1 = r1.json()["api_key"]
        key2 = r2.json()["api_key"]

        # C1 creates a task
        create_resp = await client.post(
            "/v1/tasks",
            headers={"X-API-Key": key1},
            json={"agent_id": seed_agent["id"], "inputs": {"topic": "private"}},
        )
        task_id = create_resp.json()["id"]

        # C2 cannot see it
        resp = await client.get(
            f"/v1/tasks/{task_id}", headers={"X-API-Key": key2}
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_provider_can_see_their_agent_tasks(
        self, client: AsyncClient, provider_key, consumer_key, seed_agent
    ):
        c_key, _ = consumer_key
        p_key, _ = provider_key

        await client.post(
            "/v1/tasks",
            headers={"X-API-Key": c_key},
            json={"agent_id": seed_agent["id"], "inputs": {"topic": "visible"}},
        )

        resp = await client.get(
            "/v1/tasks", headers={"X-API-Key": p_key}
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1
