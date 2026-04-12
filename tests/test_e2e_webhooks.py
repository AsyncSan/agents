"""E2E tests for webhook management."""

import pytest
from httpx import AsyncClient


class TestWebhookCRUD:
    @pytest.mark.asyncio
    async def test_create_webhook(self, client: AsyncClient, consumer_key):
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/me/webhooks",
            headers={"X-API-Key": api_key},
            json={
                "url": "https://example.com/webhook",
                "event_types": ["task.completed", "task.failed"],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["url"] == "https://example.com/webhook"
        assert data["event_types"] == ["task.completed", "task.failed"]
        assert data["secret"].startswith("whsec_")
        assert data["active"] is True
        assert data["total_deliveries"] == 0
        assert data["total_failures"] == 0

    @pytest.mark.asyncio
    async def test_list_webhooks(self, client: AsyncClient, consumer_key):
        api_key, _ = consumer_key
        # Create one first
        await client.post(
            "/v1/me/webhooks",
            headers={"X-API-Key": api_key},
            json={"url": "https://example.com/wh1", "event_types": ["*"]},
        )
        resp = await client.get(
            "/v1/me/webhooks",
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["webhooks"]) >= 1
        # Secret should be masked in list
        for wh in data["webhooks"]:
            assert wh["secret"] == "whsec_****"

    @pytest.mark.asyncio
    async def test_delete_webhook(self, client: AsyncClient, consumer_key):
        api_key, _ = consumer_key
        # Create
        create_resp = await client.post(
            "/v1/me/webhooks",
            headers={"X-API-Key": api_key},
            json={"url": "https://example.com/to-delete", "event_types": ["task.*"]},
        )
        wh_id = create_resp.json()["id"]
        # Delete
        del_resp = await client.delete(
            f"/v1/me/webhooks/{wh_id}",
            headers={"X-API-Key": api_key},
        )
        assert del_resp.status_code == 204
        # Verify it's deactivated
        list_resp = await client.get(
            "/v1/me/webhooks",
            headers={"X-API-Key": api_key},
        )
        webhooks = list_resp.json()["webhooks"]
        deleted_wh = next((w for w in webhooks if w["id"] == wh_id), None)
        assert deleted_wh is not None
        assert deleted_wh["active"] is False

    @pytest.mark.asyncio
    async def test_delete_webhook_not_found(self, client: AsyncClient, consumer_key):
        api_key, _ = consumer_key
        import uuid
        resp = await client.delete(
            f"/v1/me/webhooks/{uuid.uuid4()}",
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_webhook_wrong_owner(
        self, client: AsyncClient, consumer_key, provider_key
    ):
        consumer_api_key, _ = consumer_key
        provider_api_key, _ = provider_key
        # Consumer creates webhook
        create_resp = await client.post(
            "/v1/me/webhooks",
            headers={"X-API-Key": consumer_api_key},
            json={"url": "https://example.com/mine", "event_types": ["*"]},
        )
        wh_id = create_resp.json()["id"]
        # Provider tries to delete it
        resp = await client.delete(
            f"/v1/me/webhooks/{wh_id}",
            headers={"X-API-Key": provider_api_key},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_invalid_event_type_rejected(self, client: AsyncClient, consumer_key):
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/me/webhooks",
            headers={"X-API-Key": api_key},
            json={"url": "https://example.com/bad", "event_types": ["invalid.event"]},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_wildcard_event_type(self, client: AsyncClient, consumer_key):
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/me/webhooks",
            headers={"X-API-Key": api_key},
            json={"url": "https://example.com/all", "event_types": ["*"]},
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_prefix_wildcard_event_type(self, client: AsyncClient, consumer_key):
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/me/webhooks",
            headers={"X-API-Key": api_key},
            json={"url": "https://example.com/tasks", "event_types": ["task.*"]},
        )
        assert resp.status_code == 201
        assert resp.json()["event_types"] == ["task.*"]

    @pytest.mark.asyncio
    async def test_provider_can_create_webhook(self, client: AsyncClient, provider_key):
        api_key, _ = provider_key
        resp = await client.post(
            "/v1/me/webhooks",
            headers={"X-API-Key": api_key},
            json={"url": "https://example.com/provider-wh", "event_types": ["agent.*"]},
        )
        assert resp.status_code == 201
