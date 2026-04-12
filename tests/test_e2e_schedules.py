"""E2E tests for scheduled/recurring agent runs."""

import secrets as stdlib_secrets

import pytest
from httpx import AsyncClient


def _uid():
    return stdlib_secrets.token_hex(6)


class TestSchedules:
    @pytest.mark.asyncio
    async def test_create_schedule(self, client: AsyncClient, consumer_key, seed_agent):
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/schedules",
            headers={"X-API-Key": api_key},
            json={
                "agent_id": seed_agent["id"],
                "name": "Weekly Report",
                "cron_expression": "0 9 * * 1",
                "inputs": {"topic": "test"},
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Weekly Report"
        assert data["cron_expression"] == "0 9 * * 1"
        assert data["active"] is True
        assert data["total_runs"] == 0
        assert data["next_run_at"] is not None

    @pytest.mark.asyncio
    async def test_list_schedules(self, client: AsyncClient, consumer_key, seed_agent):
        api_key, _ = consumer_key
        await client.post(
            "/v1/schedules",
            headers={"X-API-Key": api_key},
            json={
                "agent_id": seed_agent["id"],
                "name": "Daily Check",
                "cron_expression": "0 8 * * *",
            },
        )
        resp = await client.get(
            "/v1/schedules",
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["schedules"]) >= 1

    @pytest.mark.asyncio
    async def test_pause_resume_schedule(
        self, client: AsyncClient, consumer_key, seed_agent
    ):
        api_key, _ = consumer_key
        create_resp = await client.post(
            "/v1/schedules",
            headers={"X-API-Key": api_key},
            json={
                "agent_id": seed_agent["id"],
                "name": "Pausable",
                "cron_expression": "0 12 * * *",
            },
        )
        sid = create_resp.json()["id"]

        # Pause
        resp = await client.patch(
            f"/v1/schedules/{sid}/pause",
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200
        assert resp.json()["active"] is False

        # Resume
        resp = await client.patch(
            f"/v1/schedules/{sid}/resume",
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200
        assert resp.json()["active"] is True

    @pytest.mark.asyncio
    async def test_delete_schedule(self, client: AsyncClient, consumer_key, seed_agent):
        api_key, _ = consumer_key
        create_resp = await client.post(
            "/v1/schedules",
            headers={"X-API-Key": api_key},
            json={
                "agent_id": seed_agent["id"],
                "name": "To Delete",
                "cron_expression": "0 0 * * *",
            },
        )
        sid = create_resp.json()["id"]
        resp = await client.delete(
            f"/v1/schedules/{sid}",
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_invalid_cron_rejected(
        self, client: AsyncClient, consumer_key, seed_agent
    ):
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/schedules",
            headers={"X-API-Key": api_key},
            json={
                "agent_id": seed_agent["id"],
                "name": "Bad Cron",
                "cron_expression": "not a cron",
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_nonexistent_agent_rejected(
        self, client: AsyncClient, consumer_key
    ):
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/schedules",
            headers={"X-API-Key": api_key},
            json={
                "agent_id": "nonexistent-agent",
                "name": "Bad Agent",
                "cron_expression": "0 9 * * 1",
            },
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_provider_cannot_create_schedule(
        self, client: AsyncClient, provider_key, seed_agent
    ):
        api_key, _ = provider_key
        resp = await client.post(
            "/v1/schedules",
            headers={"X-API-Key": api_key},
            json={
                "agent_id": seed_agent["id"],
                "name": "No Access",
                "cron_expression": "0 9 * * 1",
            },
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_other_consumer_cannot_access(
        self, client: AsyncClient, consumer_key, seed_agent
    ):
        api_key, _ = consumer_key
        create_resp = await client.post(
            "/v1/schedules",
            headers={"X-API-Key": api_key},
            json={
                "agent_id": seed_agent["id"],
                "name": "Private",
                "cron_expression": "0 9 * * 1",
            },
        )
        sid = create_resp.json()["id"]

        # Other consumer
        suffix = _uid()
        reg_resp = await client.post(
            "/v1/auth/register",
            json={"name": "Other", "email": f"other-{suffix}@test.com", "role": "consumer"},
        )
        other_key = reg_resp.json()["api_key"]

        resp = await client.get(
            f"/v1/schedules/{sid}",
            headers={"X-API-Key": other_key},
        )
        assert resp.status_code == 403
