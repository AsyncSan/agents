"""E2E tests for payment setup endpoints.

Note: These tests run WITHOUT Stripe configured (no STRIPE_SECRET_KEY),
so they test the graceful degradation path.
"""

import pytest
from httpx import AsyncClient


class TestPaymentSetup:
    @pytest.mark.asyncio
    async def test_payment_setup_no_stripe(self, client: AsyncClient, consumer_key):
        """Without Stripe configured, returns 503."""
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/me/payment-method",
            headers={"X-API-Key": api_key},
            json={"payment_method_id": "pm_test_fake"},
        )
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "billing_not_configured"

    @pytest.mark.asyncio
    async def test_payment_status_no_stripe(self, client: AsyncClient, consumer_key):
        """Payment status without Stripe shows no payment method."""
        api_key, _ = consumer_key
        resp = await client.get(
            "/v1/me/payment-method",
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["payment_method_attached"] is False
        assert data["default_payment_method"] is None

    @pytest.mark.asyncio
    async def test_payment_requires_consumer(self, client: AsyncClient, provider_key):
        """Providers cannot attach payment methods."""
        api_key, _ = provider_key
        resp = await client.post(
            "/v1/me/payment-method",
            headers={"X-API-Key": api_key},
            json={"payment_method_id": "pm_test_fake"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_payment_status_requires_consumer(
        self, client: AsyncClient, provider_key
    ):
        api_key, _ = provider_key
        resp = await client.get(
            "/v1/me/payment-method",
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_payment_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/v1/me/payment-method",
            json={"payment_method_id": "pm_test"},
        )
        assert resp.status_code in (401, 403)
