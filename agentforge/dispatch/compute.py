"""Abstract compute provider interface and Hetzner implementation.

This is the core of AgentForge's ephemeral compute layer, extracted from
the battle-tested task-dispatcher.py (287+ successful dispatches).
"""

import logging
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger("agentforge.dispatch")


@dataclass
class ServerInfo:
    """Ephemeral server metadata."""
    id: str
    name: str
    ip: str
    provider: str
    server_type: str
    snapshot_profile: str
    status: str = "provisioning"


@dataclass
class DispatchResult:
    """Result of a task dispatch."""
    success: bool
    run_id: str
    server: ServerInfo | None = None
    exit_code: int | None = None
    elapsed_seconds: int = 0
    results_path: str | None = None
    output_bytes: int = 0
    metrics: dict = field(default_factory=dict)


class ComputeProvider(ABC):
    """Abstract interface for ephemeral compute providers."""

    @abstractmethod
    def create_server(
        self,
        name: str,
        snapshot_profile: str = "base",
        server_type: str | None = None,
    ) -> ServerInfo:
        ...

    @abstractmethod
    def destroy_server(self, server: ServerInfo) -> None:
        ...

    @abstractmethod
    def wait_for_ready(self, server: ServerInfo, timeout: int = 480) -> bool:
        ...

    @abstractmethod
    def ssh(self, server: ServerInfo, cmd: str, check: bool = True) -> subprocess.CompletedProcess:
        ...

    @abstractmethod
    def scp_to(self, server: ServerInfo, local_path: str, remote_path: str) -> bool:
        ...

    @abstractmethod
    def scp_from(self, server: ServerInfo, remote_path: str, local_path: str) -> bool:
        ...


class HetznerProvider(ComputeProvider):
    """Hetzner Cloud compute provider using hcloud CLI.

    Extracted from task-dispatcher.py. Uses pre-baked snapshots for fast boot (~20s).
    """

    def __init__(
        self,
        hcloud_token: str,
        ssh_key_name: str = "async@pi5",
        ssh_key_path: str | None = None,
        network_name: str = "renemurrell-vpc",
        firewall_name: str = "renemurrell-agents-firewall",
        location: str = "nbg1",
        default_server_type: str = "cax11",
        snapshots: dict[str, str] | None = None,
        light_init_script: str | None = None,
    ):
        self.hcloud_token = hcloud_token
        self.ssh_key_name = ssh_key_name
        self.ssh_key_path = ssh_key_path or str(Path.home() / ".ssh" / "id_ed25519")
        self.network_name = network_name
        self.firewall_name = firewall_name
        self.location = location
        self.default_server_type = default_server_type
        self.snapshots = snapshots or {
            "base": "370464673",
            "gui": "370465176",
            "gui-x86": "370835039",
        }
        self.light_init_script = light_init_script

        # SSH options for ephemeral servers (new host key each time)
        self._ssh_opts = (
            f"-i {self.ssh_key_path} "
            "-o StrictHostKeyChecking=no "
            "-o UserKnownHostsFile=/dev/null "
            "-o ConnectTimeout=10 "
            "-o ServerAliveInterval=30 "
            "-o ServerAliveCountMax=10 "
            "-o LogLevel=ERROR"
        )

    def _run(self, cmd: str, check: bool = True, timeout: int | None = None,
             input_data: str | None = None) -> subprocess.CompletedProcess:
        """Execute shell command with HCLOUD_TOKEN in env."""
        import os
        env = os.environ.copy()
        env["HCLOUD_TOKEN"] = self.hcloud_token
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, input=input_data, env=env,
        )
        if result.returncode != 0 and check:
            log.error(f"Command failed (rc={result.returncode}): {cmd}")
            if result.stderr:
                log.error(result.stderr[:500])
            raise RuntimeError(f"Command failed: {cmd}")
        return result

    def _ensure_firewall(self) -> str:
        """Create agent firewall if it doesn't exist."""
        result = self._run(
            f"hcloud firewall describe {self.firewall_name} -o format='{{{{.ID}}}}'",
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return self.firewall_name

        import json
        log.info(f"Creating firewall {self.firewall_name}...")
        rules = json.dumps([
            {"direction": "in", "protocol": "tcp", "port": "22",
             "source_ips": ["0.0.0.0/0", "::/0"]},
            {"direction": "in", "protocol": "tcp", "port": "any",
             "source_ips": ["10.0.1.1/32"]},
            {"direction": "out", "protocol": "tcp", "port": "443",
             "destination_ips": ["0.0.0.0/0", "::/0"]},
            {"direction": "out", "protocol": "tcp", "port": "80",
             "destination_ips": ["0.0.0.0/0", "::/0"]},
            {"direction": "out", "protocol": "udp", "port": "53",
             "destination_ips": ["0.0.0.0/0", "::/0"]},
            {"direction": "out", "protocol": "udp", "port": "123",
             "destination_ips": ["0.0.0.0/0", "::/0"]},
            {"direction": "out", "protocol": "tcp", "port": "any",
             "destination_ips": ["10.0.0.0/16"]},
        ])
        rules_file = Path("/tmp/agent-firewall-rules.json")
        rules_file.write_text(rules)
        self._run(f"hcloud firewall create --name {self.firewall_name} --rules-file {rules_file}")
        rules_file.unlink(missing_ok=True)
        return self.firewall_name

    def create_server(
        self,
        name: str,
        snapshot_profile: str = "base",
        server_type: str | None = None,
    ) -> ServerInfo:
        effective_type = server_type or self.default_server_type
        self._ensure_firewall()

        snapshot_id = self.snapshots.get(snapshot_profile)
        if snapshot_id:
            image = str(snapshot_id)
            user_data = (
                f"--user-data-from-file {self.light_init_script}"
                if self.light_init_script else ""
            )
            log.info(f"Using snapshot {snapshot_id} (profile: {snapshot_profile})")
        else:
            image = "ubuntu-24.04"
            user_data = ""
            log.info("Using ubuntu-24.04 (no snapshot for this profile)")

        cmd = (
            f"hcloud server create"
            f" --name {name}"
            f" --type {effective_type}"
            f" --image {image}"
            f" --location {self.location}"
            f" --ssh-key {self.ssh_key_name}"
            f" --label role=agent"
            f" --firewall {self.firewall_name}"
            f" --network {self.network_name}"
            f" {user_data}"
        ).strip()
        self._run(cmd)
        log.info(f"Server {name} created")

        # Get IP
        result = self._run(f"hcloud server ip {name}")
        ip = result.stdout.strip()

        # Get server ID
        result = self._run(f"hcloud server describe {name} -o format='{{{{.ID}}}}'")
        server_id = result.stdout.strip()

        return ServerInfo(
            id=server_id,
            name=name,
            ip=ip,
            provider="hetzner",
            server_type=effective_type,
            snapshot_profile=snapshot_profile,
            status="created",
        )

    def destroy_server(self, server: ServerInfo) -> None:
        log.info(f"Destroying server {server.name}...")
        self._run(f"hcloud server delete {server.id}", check=False)
        server.status = "destroyed"
        log.info(f"Server {server.name} destroyed")

    def wait_for_ready(self, server: ServerInfo, timeout: int = 480) -> bool:
        start = time.time()

        # Wait for SSH
        while time.time() - start < timeout:
            result = self.ssh(server, "echo ready", check=False)
            if result.returncode == 0:
                log.info(f"Server {server.name} SSH accessible")
                break
            log.info("Waiting for SSH...")
            time.sleep(15)
        else:
            raise TimeoutError(f"Server {server.name} SSH not ready within {timeout}s")

        # Wait for cloud-init
        while time.time() - start < timeout:
            cmd = "cloud-init status --wait 2>/dev/null || echo 'waiting'"
            result = self.ssh(server, cmd, check=False)
            if "done" in (result.stdout or ""):
                log.info("Cloud-init complete")
                break
            time.sleep(10)

        server.status = "ready"
        return True

    def ssh(self, server: ServerInfo, cmd: str, check: bool = True) -> subprocess.CompletedProcess:
        return self._run(
            f"ssh {self._ssh_opts} root@{server.ip} 'bash -s'",
            check=check,
            input_data=cmd,
        )

    def scp_to(self, server: ServerInfo, local_path: str, remote_path: str) -> bool:
        scp_opts = (
            f"-i {self.ssh_key_path} "
            "-o StrictHostKeyChecking=no "
            "-o UserKnownHostsFile=/dev/null "
            "-o LogLevel=ERROR"
        )
        result = self._run(
            f"scp {scp_opts} {local_path} root@{server.ip}:{remote_path}",
            check=False,
        )
        return result.returncode == 0

    def scp_from(self, server: ServerInfo, remote_path: str, local_path: str) -> bool:
        scp_opts = (
            f"-i {self.ssh_key_path} "
            "-o StrictHostKeyChecking=no "
            "-o UserKnownHostsFile=/dev/null "
            "-o LogLevel=ERROR"
        )
        result = self._run(
            f"scp {scp_opts} root@{server.ip}:{remote_path} {local_path}",
            check=False,
        )
        return result.returncode == 0

    def rsync_from(self, server: ServerInfo, remote_path: str, local_path: str) -> bool:
        """Rsync results from server to local directory."""
        result = self._run(
            f"rsync -avz -e 'ssh {self._ssh_opts}' "
            f"root@{server.ip}:{remote_path} {local_path}",
            check=False,
        )
        if result.returncode != 0:
            # Retry once
            time.sleep(5)
            result = self._run(
                f"rsync -avz -e 'ssh {self._ssh_opts}' "
                f"root@{server.ip}:{remote_path} {local_path}",
                check=False,
            )
        return result.returncode == 0
