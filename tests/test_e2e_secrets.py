"""E2E tests for secret brokerage."""

import pytest
from httpx import AsyncClient


class TestSecretsCRUD:
    @pytest.mark.asyncio
    async def test_set_secrets(self, client: AsyncClient, consumer_key):
        api_key, _ = consumer_key
        resp = await client.put(
            "/v1/me/secrets",
            headers={"X-API-Key": api_key},
            json={"secrets": {"OPENAI_API_KEY": "sk-test", "GH_TOKEN": "ghp_test"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "OPENAI_API_KEY" in data["keys"]
        assert "GH_TOKEN" in data["keys"]

    @pytest.mark.asyncio
    async def test_list_secrets_shows_keys_only(self, client: AsyncClient, consumer_key):
        api_key, _ = consumer_key
        await client.put(
            "/v1/me/secrets",
            headers={"X-API-Key": api_key},
            json={"secrets": {"SECRET_KEY": "super-secret-value"}},
        )
        resp = await client.get(
            "/v1/me/secrets", headers={"X-API-Key": api_key}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "SECRET_KEY" in data["keys"]
        # Values should never be returned
        assert "super-secret-value" not in str(data)

    @pytest.mark.asyncio
    async def test_delete_secret(self, client: AsyncClient, consumer_key):
        api_key, _ = consumer_key
        await client.put(
            "/v1/me/secrets",
            headers={"X-API-Key": api_key},
            json={"secrets": {"TO_DELETE": "val"}},
        )
        resp = await client.delete(
            "/v1/me/secrets/TO_DELETE", headers={"X-API-Key": api_key}
        )
        assert resp.status_code == 204

        # Verify it's gone
        resp = await client.get(
            "/v1/me/secrets", headers={"X-API-Key": api_key}
        )
        assert "TO_DELETE" not in resp.json()["keys"]

    @pytest.mark.asyncio
    async def test_delete_nonexistent_secret(self, client: AsyncClient, consumer_key):
        api_key, _ = consumer_key
        resp = await client.delete(
            "/v1/me/secrets/DOES_NOT_EXIST", headers={"X-API-Key": api_key}
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_provider_secrets_isolated(self, client: AsyncClient, provider_key, consumer_key):
        p_key, _ = provider_key
        c_key, _ = consumer_key

        await client.put(
            "/v1/me/secrets",
            headers={"X-API-Key": p_key},
            json={"secrets": {"PROVIDER_SECRET": "pval"}},
        )
        await client.put(
            "/v1/me/secrets",
            headers={"X-API-Key": c_key},
            json={"secrets": {"CONSUMER_SECRET": "cval"}},
        )

        p_resp = await client.get("/v1/me/secrets", headers={"X-API-Key": p_key})
        c_resp = await client.get("/v1/me/secrets", headers={"X-API-Key": c_key})

        assert "PROVIDER_SECRET" in p_resp.json()["keys"]
        assert "CONSUMER_SECRET" not in p_resp.json()["keys"]
        assert "CONSUMER_SECRET" in c_resp.json()["keys"]
        assert "PROVIDER_SECRET" not in c_resp.json()["keys"]

    @pytest.mark.asyncio
    async def test_merge_secrets(self, client: AsyncClient, consumer_key):
        api_key, _ = consumer_key
        await client.put(
            "/v1/me/secrets",
            headers={"X-API-Key": api_key},
            json={"secrets": {"KEY_A": "a"}},
        )
        await client.put(
            "/v1/me/secrets",
            headers={"X-API-Key": api_key},
            json={"secrets": {"KEY_B": "b"}},
        )
        resp = await client.get("/v1/me/secrets", headers={"X-API-Key": api_key})
        keys = resp.json()["keys"]
        assert "KEY_A" in keys
        assert "KEY_B" in keys
