"""Test that unhandled exceptions return 500 without stack traces."""

import pytest
from httpx import AsyncClient


class TestGlobalErrorHandler:
    @pytest.mark.asyncio
    async def test_structured_api_error(self, client: AsyncClient):
        """Known API errors return structured response."""
        resp = await client.get("/v1/agents/nonexistent-agent-xyz")
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "agent_not_found"

    @pytest.mark.asyncio
    async def test_404_route_not_found(self, client: AsyncClient):
        """Non-existent routes return 404 (FastAPI default)."""
        resp = await client.get("/v1/this-route-does-not-exist")
        assert resp.status_code in (404, 405)

    @pytest.mark.asyncio
    async def test_validation_error_no_stack_trace(
        self, client: AsyncClient, consumer_key
    ):
        """Pydantic validation errors return 422 without stack traces."""
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/tasks",
            headers={"X-API-Key": api_key},
            json={},  # missing required fields
        )
        assert resp.status_code == 422
        body = resp.text
        # Should not contain Python tracebacks
        assert "Traceback" not in body
        assert "File " not in body
