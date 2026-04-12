"""E2E tests for execution dashboard and compliance export."""

import pytest
from httpx import AsyncClient


class TestDashboard:
    @pytest.mark.asyncio
    async def test_consumer_dashboard(self, client: AsyncClient, consumer_key):
        api_key, _ = consumer_key
        resp = await client.get(
            "/v1/me/dashboard",
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["period_days"] == 30
        assert data["total_executions"] >= 0
        assert data["total_success"] >= 0
        assert data["total_failed"] >= 0
        assert data["total_cost_cents"] >= 0
        assert isinstance(data["daily_usage"], list)
        assert isinstance(data["top_agents"], list)

    @pytest.mark.asyncio
    async def test_provider_dashboard(self, client: AsyncClient, provider_key):
        api_key, _ = provider_key
        resp = await client.get(
            "/v1/me/dashboard",
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_dashboard_custom_days(self, client: AsyncClient, consumer_key):
        api_key, _ = consumer_key
        resp = await client.get(
            "/v1/me/dashboard?days=7",
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200
        assert resp.json()["period_days"] == 7

    @pytest.mark.asyncio
    async def test_dashboard_requires_auth(self, client: AsyncClient):
        resp = await client.get("/v1/me/dashboard")
        assert resp.status_code in (401, 403)


class TestComplianceExport:
    @pytest.mark.asyncio
    async def test_export_json(
        self, client: AsyncClient, provider_key, seed_agent
    ):
        """Agent creation generates events, export should contain them."""
        api_key, _ = provider_key
        resp = await client.post(
            "/v1/me/compliance/export",
            headers={"X-API-Key": api_key},
            json={
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
                "format": "json",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["export_type"] == "compliance_audit_log"
        assert data["total_events"] >= 1
        assert isinstance(data["events"], list)
        # Should have agent.created event
        types = [e["event_type"] for e in data["events"]]
        assert "agent.created" in types

    @pytest.mark.asyncio
    async def test_export_csv(
        self, client: AsyncClient, provider_key, seed_agent
    ):
        api_key, _ = provider_key
        resp = await client.post(
            "/v1/me/compliance/export",
            headers={"X-API-Key": api_key},
            json={
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
                "format": "csv",
            },
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "event_id" in resp.text  # CSV header
        assert "agent.created" in resp.text

    @pytest.mark.asyncio
    async def test_export_invalid_date(self, client: AsyncClient, consumer_key):
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/me/compliance/export",
            headers={"X-API-Key": api_key},
            json={
                "start_date": "not-a-date",
                "end_date": "2026-12-31",
                "format": "json",
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_export_max_range(self, client: AsyncClient, consumer_key):
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/me/compliance/export",
            headers={"X-API-Key": api_key},
            json={
                "start_date": "2024-01-01",
                "end_date": "2026-12-31",
                "format": "json",
            },
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_export_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/v1/me/compliance/export",
            json={"start_date": "2026-01-01", "end_date": "2026-12-31"},
        )
        assert resp.status_code in (401, 403)
