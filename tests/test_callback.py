"""Tests for callback delivery after task completion."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentforge.dispatch.worker import _send_callback


@pytest.fixture
def mock_task():
    task = MagicMock()
    task.id = "tc-test-001"
    task.agent_id = "deep-research"
    task.callback_url = "https://example.com/webhook"
    return task


@pytest.fixture
def mock_task_no_url():
    task = MagicMock()
    task.id = "tc-test-002"
    task.agent_id = "deep-research"
    task.callback_url = None
    return task


class TestSendCallback:
    @pytest.mark.asyncio
    async def test_sends_post_on_success(self, mock_task):
        mock_response = MagicMock()
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("agentforge.dispatch.worker.httpx.AsyncClient", return_value=mock_client):
            await _send_callback(mock_task, "run-001", "completed", 120)

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://example.com/webhook"
        payload = call_args[1]["json"]
        assert payload["task_id"] == "tc-test-001"
        assert payload["status"] == "completed"
        assert payload["execution_id"] == "run-001"
        assert payload["elapsed_seconds"] == 120

    @pytest.mark.asyncio
    async def test_sends_post_on_failure(self, mock_task):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("agentforge.dispatch.worker.httpx.AsyncClient", return_value=mock_client):
            await _send_callback(mock_task, "run-001", "failed")

        payload = mock_client.post.call_args[1]["json"]
        assert payload["status"] == "failed"
        assert payload["elapsed_seconds"] is None

    @pytest.mark.asyncio
    async def test_skips_when_no_url(self, mock_task_no_url):
        with patch("agentforge.dispatch.worker.httpx.AsyncClient") as mock_cls:
            await _send_callback(mock_task_no_url, "run-001", "completed")
            mock_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_logs_on_timeout(self, mock_task):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("Connection timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("agentforge.dispatch.worker.httpx.AsyncClient", return_value=mock_client):
            # Should not raise, just log
            await _send_callback(mock_task, "run-001", "completed", 120)
