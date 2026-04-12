"""E2E tests for consumer ratings system."""

import secrets as stdlib_secrets

import pytest
from httpx import AsyncClient


def _uid():
    return stdlib_secrets.token_hex(6)


async def _create_completed_task(client, consumer_key, seed_agent, db_session):
    """Helper: create a task and mark it completed directly in DB."""
    from agentforge.models.task import Task

    api_key, consumer_data = consumer_key
    # Create task via API
    resp = await client.post(
        "/v1/tasks",
        headers={"X-API-Key": api_key},
        json={"agent_id": seed_agent["id"], "inputs": {"topic": "test"}},
    )
    assert resp.status_code == 201, resp.text
    task_id = resp.json()["id"]

    # Mark as completed directly (normally done by worker)
    from sqlalchemy import update
    await db_session.execute(
        update(Task).where(Task.id == task_id).values(status="completed")
    )
    await db_session.commit()
    return task_id


class TestRatings:
    @pytest.mark.asyncio
    async def test_rate_completed_task(
        self, client: AsyncClient, consumer_key, seed_agent, db_session
    ):
        task_id = await _create_completed_task(
            client, consumer_key, seed_agent, db_session
        )
        api_key, _ = consumer_key
        resp = await client.post(
            f"/v1/tasks/{task_id}/rating",
            headers={"X-API-Key": api_key},
            json={"score": 5, "comment": "Excellent work!"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["score"] == 5
        assert data["comment"] == "Excellent work!"
        assert data["task_id"] == task_id
        assert data["agent_id"] == seed_agent["id"]

    @pytest.mark.asyncio
    async def test_rate_pending_task_rejected(
        self, client: AsyncClient, consumer_key, seed_agent
    ):
        api_key, _ = consumer_key
        # Create task (stays pending)
        resp = await client.post(
            "/v1/tasks",
            headers={"X-API-Key": api_key},
            json={"agent_id": seed_agent["id"], "inputs": {"topic": "test"}},
        )
        task_id = resp.json()["id"]

        resp = await client.post(
            f"/v1/tasks/{task_id}/rating",
            headers={"X-API-Key": api_key},
            json={"score": 3},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_duplicate_rating_rejected(
        self, client: AsyncClient, consumer_key, seed_agent, db_session
    ):
        task_id = await _create_completed_task(
            client, consumer_key, seed_agent, db_session
        )
        api_key, _ = consumer_key
        # First rating
        resp = await client.post(
            f"/v1/tasks/{task_id}/rating",
            headers={"X-API-Key": api_key},
            json={"score": 4},
        )
        assert resp.status_code == 201
        # Second rating
        resp = await client.post(
            f"/v1/tasks/{task_id}/rating",
            headers={"X-API-Key": api_key},
            json={"score": 2},
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_other_consumer_cannot_rate(
        self, client: AsyncClient, consumer_key, seed_agent, db_session
    ):
        task_id = await _create_completed_task(
            client, consumer_key, seed_agent, db_session
        )
        # Register different consumer
        suffix = _uid()
        resp = await client.post(
            "/v1/auth/register",
            json={
                "name": "Other",
                "email": f"other-{suffix}@test.com",
                "role": "consumer",
            },
        )
        other_key = resp.json()["api_key"]

        resp = await client.post(
            f"/v1/tasks/{task_id}/rating",
            headers={"X-API-Key": other_key},
            json={"score": 1},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_invalid_score_rejected(
        self, client: AsyncClient, consumer_key, seed_agent, db_session
    ):
        task_id = await _create_completed_task(
            client, consumer_key, seed_agent, db_session
        )
        api_key, _ = consumer_key
        # Score too high
        resp = await client.post(
            f"/v1/tasks/{task_id}/rating",
            headers={"X-API-Key": api_key},
            json={"score": 6},
        )
        assert resp.status_code == 422
        # Score too low
        resp = await client.post(
            f"/v1/tasks/{task_id}/rating",
            headers={"X-API-Key": api_key},
            json={"score": 0},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_list_agent_ratings(
        self, client: AsyncClient, consumer_key, seed_agent, db_session
    ):
        task_id = await _create_completed_task(
            client, consumer_key, seed_agent, db_session
        )
        api_key, _ = consumer_key
        await client.post(
            f"/v1/tasks/{task_id}/rating",
            headers={"X-API-Key": api_key},
            json={"score": 4, "comment": "Good job"},
        )

        resp = await client.get(f"/v1/agents/{seed_agent['id']}/ratings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert data["average_score"] is not None
        assert data["average_score"] >= 1.0
        assert data["average_score"] <= 5.0
        assert len(data["ratings"]) >= 1

    @pytest.mark.asyncio
    async def test_list_ratings_empty(self, client: AsyncClient, seed_agent):
        resp = await client.get(f"/v1/agents/{seed_agent['id']}/ratings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["average_score"] is None
        assert data["ratings"] == []

    @pytest.mark.asyncio
    async def test_list_ratings_not_found(self, client: AsyncClient):
        resp = await client.get("/v1/agents/nonexistent/ratings")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_rating_without_comment(
        self, client: AsyncClient, consumer_key, seed_agent, db_session
    ):
        task_id = await _create_completed_task(
            client, consumer_key, seed_agent, db_session
        )
        api_key, _ = consumer_key
        resp = await client.post(
            f"/v1/tasks/{task_id}/rating",
            headers={"X-API-Key": api_key},
            json={"score": 3},
        )
        assert resp.status_code == 201
        assert resp.json()["comment"] is None

    @pytest.mark.asyncio
    async def test_provider_cannot_rate(
        self, client: AsyncClient, provider_key, consumer_key, seed_agent, db_session
    ):
        """Providers can't rate tasks (consumer role required)."""
        task_id = await _create_completed_task(
            client, consumer_key, seed_agent, db_session
        )
        api_key, _ = provider_key
        resp = await client.post(
            f"/v1/tasks/{task_id}/rating",
            headers={"X-API-Key": api_key},
            json={"score": 5},
        )
        assert resp.status_code == 403
