"""Tests for request ID middleware."""

import pytest
from httpx import AsyncClient


class TestRequestId:
    @pytest.mark.asyncio
    async def test_response_has_request_id(self, client: AsyncClient):
        resp = await client.get("/healthz")
        assert "X-Request-ID" in resp.headers
        assert len(resp.headers["X-Request-ID"]) > 10

    @pytest.mark.asyncio
    async def test_client_request_id_preserved(self, client: AsyncClient):
        custom_id = "test-trace-12345"
        resp = await client.get(
            "/healthz",
            headers={"X-Request-ID": custom_id},
        )
        assert resp.headers["X-Request-ID"] == custom_id

    @pytest.mark.asyncio
    async def test_error_response_has_request_id(self, client: AsyncClient):
        resp = await client.get(
            "/v1/tasks",
            headers={"X-API-Key": "af_invalid_key_12345678901234567890"},
        )
        assert resp.status_code == 401
        assert "X-Request-ID" in resp.headers
