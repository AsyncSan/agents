"""Tests for dual compute tier: container (~100ms) vs vm (~20s)."""

from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

from agentforge.dispatch.compute import ServerInfo
from agentforge.dispatch.docker_provider import DockerProvider, _shell_quote


class TestDockerProvider:
    def test_shell_quote(self):
        assert _shell_quote("hello") == "'hello'"
        assert _shell_quote("it's") == "'it'\\''s'"

    def test_init_defaults(self):
        p = DockerProvider()
        assert p.default_image == "agentforge/runner:latest"
        assert p.cpu_limit == "2.0"
        assert p.memory_limit == "2g"
        assert "base" in p.images

    def test_init_custom(self):
        p = DockerProvider(
            default_image="custom:v1",
            cpu_limit="4.0",
            memory_limit="8g",
            docker_host="tcp://remote:2375",
        )
        assert p.default_image == "custom:v1"
        assert p.cpu_limit == "4.0"
        assert "-H tcp://remote:2375" in p._docker_opts

    def test_create_server_returns_server_info(self):
        """create_server returns proper ServerInfo with docker provider."""
        p = DockerProvider()
        with patch.object(p, "_run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="abc123def456\n", returncode=0
            )
            server = p.create_server("test-agent", "base")

        assert server.provider == "docker"
        assert server.ip == "127.0.0.1"
        assert server.status == "running"
        assert "container" in server.server_type

    def test_destroy_server(self):
        p = DockerProvider()
        server = ServerInfo(
            id="abc123",
            name="test",
            ip="127.0.0.1",
            provider="docker",
            server_type="container",
            snapshot_profile="base",
        )
        with patch.object(p, "_run"):
            p.destroy_server(server)
        assert server.status == "destroyed"

    def test_wait_for_ready_instant(self):
        p = DockerProvider()
        server = ServerInfo(
            id="abc123",
            name="test",
            ip="127.0.0.1",
            provider="docker",
            server_type="container",
            snapshot_profile="base",
        )
        with patch.object(p, "_run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = p.wait_for_ready(server)
        assert result is True
        assert server.status == "ready"


class TestComputeTierRouting:
    @pytest.mark.asyncio
    async def test_task_accepts_compute_tier(
        self, client: AsyncClient, consumer_key, seed_agent
    ):
        """Task submission accepts compute_tier field."""
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/tasks",
            headers={"X-API-Key": api_key},
            json={
                "agent_id": seed_agent["id"],
                "inputs": {"topic": "test"},
                "compute_tier": "container",
            },
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_task_rejects_invalid_tier(
        self, client: AsyncClient, consumer_key, seed_agent
    ):
        """Invalid compute_tier is rejected."""
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/tasks",
            headers={"X-API-Key": api_key},
            json={
                "agent_id": seed_agent["id"],
                "inputs": {"topic": "test"},
                "compute_tier": "quantum",
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_agent_card_has_compute_tier(
        self, client: AsyncClient, provider_key
    ):
        """Agent creation with compute_tier in runtime."""
        api_key, _ = provider_key
        resp = await client.post(
            "/v1/agents",
            headers={"X-API-Key": api_key},
            json={
                "id": "tier-test-agent",
                "name": "Tier Test",
                "description": "Tests compute tier",
                "domain": "testing",
                "tags": [],
                "inputs": [{"name": "x", "type": "string"}],
                "outputs": [{"name": "output.md", "type": "markdown"}],
                "runtime": {
                    "estimated_duration_seconds": 60,
                    "compute_tier": "vm",
                },
                "pricing": {"base_price_usd": 1.00},
                "instructions": "Test",
            },
        )
        assert resp.status_code == 201
        card = resp.json()["card"]
        assert card["runtime"]["compute_tier"] == "vm"

    @pytest.mark.asyncio
    async def test_default_compute_tier_is_container(
        self, client: AsyncClient, provider_key
    ):
        """Default compute_tier is container when not specified."""
        api_key, _ = provider_key
        resp = await client.post(
            "/v1/agents",
            headers={"X-API-Key": api_key},
            json={
                "id": "tier-default-agent",
                "name": "Default Tier",
                "description": "Tests default tier",
                "domain": "testing",
                "tags": [],
                "inputs": [{"name": "x", "type": "string"}],
                "outputs": [{"name": "output.md", "type": "markdown"}],
                "runtime": {"estimated_duration_seconds": 60},
                "pricing": {"base_price_usd": 1.00},
                "instructions": "Test",
            },
        )
        assert resp.status_code == 201
        card = resp.json()["card"]
        assert card["runtime"]["compute_tier"] == "container"

    def test_get_dispatcher_container(self):
        """get_dispatcher returns container dispatcher when tier=container."""
        from agentforge.dispatch.worker import get_dispatcher

        with patch(
            "agentforge.dispatch.worker.settings"
        ) as mock_settings:
            mock_settings.docker_enabled = True
            mock_settings.docker_default_image = "test:latest"
            mock_settings.docker_cpu_limit = "1.0"
            mock_settings.docker_memory_limit = "1g"
            mock_settings.docker_network = "bridge"
            mock_settings.docker_host = ""

            # Reset singleton
            import agentforge.dispatch.worker as w
            w._container_dispatcher = None

            d = get_dispatcher("container")
            assert isinstance(d.compute, DockerProvider)

    def test_get_dispatcher_vm(self):
        """get_dispatcher returns VM dispatcher when tier=vm."""
        from agentforge.dispatch.worker import get_dispatcher

        with patch(
            "agentforge.dispatch.worker.settings"
        ) as mock_settings:
            mock_settings.hcloud_token = "test"
            mock_settings.hcloud_ssh_key_name = "test"
            mock_settings.hcloud_ssh_key_path = ""
            mock_settings.hcloud_network_name = "test"
            mock_settings.hcloud_firewall_name = "test"
            mock_settings.hcloud_location = "nbg1"
            mock_settings.hcloud_default_server_type = "cax11"
            mock_settings.snapshot_base = "1"
            mock_settings.snapshot_gui = "2"
            mock_settings.snapshot_gui_x86 = "3"

            import agentforge.dispatch.worker as w
            from agentforge.dispatch.compute import HetznerProvider
            w._vm_dispatcher = None

            d = get_dispatcher("vm")
            assert isinstance(d.compute, HetznerProvider)
