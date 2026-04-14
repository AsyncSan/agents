"""Tests for task cancellation endpoint."""

import pytest
from httpx import AsyncClient


class TestTaskCancellation:
    @pytest.mark.asyncio
    async def test_cancel_pending_task(self, client: AsyncClient, consumer_key, seed_agent):
        api_key, _ = consumer_key
        # Create task
        resp = await client.post(
            "/v1/tasks",
            headers={"X-API-Key": api_key},
            json={"agent_id": seed_agent["id"], "inputs": {"topic": "test"}},
        )
        task_id = resp.json()["id"]
        assert resp.json()["status"] == "pending"

        # Cancel
        resp = await client.post(
            f"/v1/tasks/{task_id}/cancel",
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_completed_task_rejected(
        self, client: AsyncClient, consumer_key, seed_agent, db_session,
    ):
        api_key, _ = consumer_key
        # Create and manually complete a task
        resp = await client.post(
            "/v1/tasks",
            headers={"X-API-Key": api_key},
            json={"agent_id": seed_agent["id"], "inputs": {"topic": "test"}},
        )
        task_id = resp.json()["id"]

        from sqlalchemy import select

        from agentforge.models.task import Task
        result = await db_session.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one()
        task.status = "completed"
        await db_session.commit()

        # Cancel should fail
        resp = await client.post(
            f"/v1/tasks/{task_id}/cancel",
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "task_not_cancellable"

    @pytest.mark.asyncio
    async def test_cancel_other_consumers_task(
        self, client: AsyncClient, consumer_key, seed_agent,
    ):
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/tasks",
            headers={"X-API-Key": api_key},
            json={"agent_id": seed_agent["id"], "inputs": {"topic": "test"}},
        )
        task_id = resp.json()["id"]

        # Register another consumer
        resp2 = await client.post(
            "/v1/auth/register",
            json={"name": "Other", "email": "other-cancel@test.com", "role": "consumer"},
        )
        other_key = resp2.json()["api_key"]

        # Other consumer tries to cancel
        resp = await client.post(
            f"/v1/tasks/{task_id}/cancel",
            headers={"X-API-Key": other_key},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_task(self, client: AsyncClient, consumer_key):
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/tasks/tc-99999999-fakefake/cancel",
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 404
