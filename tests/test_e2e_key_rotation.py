"""Tests for API key rotation endpoint."""

import pytest
from httpx import AsyncClient


class TestApiKeyRotation:
    @pytest.mark.asyncio
    async def test_rotate_key(self, client: AsyncClient, consumer_key):
        old_key, _ = consumer_key

        # Rotate
        resp = await client.post(
            "/v1/me/api-key/rotate",
            headers={"X-API-Key": old_key},
        )
        assert resp.status_code == 200
        new_key = resp.json()["api_key"]
        assert new_key.startswith("af_")
        assert new_key != old_key

        # Old key should be invalid
        resp = await client.get(
            "/v1/me",
            headers={"X-API-Key": old_key},
        )
        assert resp.status_code == 401

        # New key should work
        resp = await client.get(
            "/v1/me",
            headers={"X-API-Key": new_key},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_rotate_provider_key(self, client: AsyncClient, provider_key):
        old_key, _ = provider_key

        resp = await client.post(
            "/v1/me/api-key/rotate",
            headers={"X-API-Key": old_key},
        )
        assert resp.status_code == 200
        new_key = resp.json()["api_key"]

        # New key works
        resp = await client.get(
            "/v1/me",
            headers={"X-API-Key": new_key},
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "provider"
