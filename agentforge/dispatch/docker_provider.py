"""Docker-based compute provider for fast agent execution (~100ms startup).

Runs agents in isolated Docker containers on the same host. Suitable for
lightweight tasks that don't need a full VM. Containers are ephemeral
and destroyed after execution completes.

Compared to HetznerProvider (~20s boot):
  - ~100ms container startup
  - Shared kernel (less isolation, but still namespace-separated)
  - No SSH, uses docker exec
  - Results collected via docker cp
  - Resource-limited (CPU, memory, no GPU)
"""

import logging
import subprocess
import time
from pathlib import Path

from agentforge.dispatch.compute import ComputeProvider, ServerInfo

log = logging.getLogger("agentforge.dispatch.docker")

# Default resource limits for containers
DEFAULT_CPU_LIMIT = "2.0"  # 2 CPU cores
DEFAULT_MEMORY_LIMIT = "2g"  # 2GB RAM
DEFAULT_NETWORK = "bridge"
CONTAINER_WORKSPACE = "/workspace"


class DockerProvider(ComputeProvider):
    """Docker container compute provider for fast, lightweight execution.

    Uses pre-built Docker images instead of VM snapshots. Containers start
    in ~100ms vs ~20s for full VMs.
    """

    def __init__(
        self,
        default_image: str = "agentforge/runner:latest",
        images: dict[str, str] | None = None,
        cpu_limit: str = DEFAULT_CPU_LIMIT,
        memory_limit: str = DEFAULT_MEMORY_LIMIT,
        network: str = DEFAULT_NETWORK,
        results_base: str | Path = "results",
        docker_host: str | None = None,
    ):
        self.default_image = default_image
        self.images = images or {
            "base": "agentforge/runner:latest",
            "python": "agentforge/runner-python:latest",
            "node": "agentforge/runner-node:latest",
        }
        self.cpu_limit = cpu_limit
        self.memory_limit = memory_limit
        self.network = network
        self.results_base = Path(results_base)
        self.docker_host = docker_host

        self._docker_opts = ""
        if docker_host:
            self._docker_opts = f"-H {docker_host}"

    def _run(
        self, cmd: str, check: bool = True, timeout: int | None = None,
        input_data: str | None = None,
    ) -> subprocess.CompletedProcess:
        """Execute a docker command."""
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, input=input_data,
        )
        if result.returncode != 0 and check:
            log.error(f"Docker command failed (rc={result.returncode}): {cmd}")
            if result.stderr:
                log.error(result.stderr[:500])
            raise RuntimeError(f"Docker command failed: {cmd}")
        return result

    def create_server(
        self,
        name: str,
        snapshot_profile: str = "base",
        server_type: str | None = None,
    ) -> ServerInfo:
        """Create and start a Docker container.

        Returns immediately (~100ms). Container runs with:
        - Resource limits (CPU, memory)
        - Isolated workspace volume
        - No privileged access
        - Auto-remove disabled (we clean up after result collection)
        """
        image = self.images.get(snapshot_profile, self.default_image)

        # Create workspace directory for results
        workspace = self.results_base / name
        workspace.mkdir(parents=True, exist_ok=True)

        cmd = (
            f"docker {self._docker_opts} run -d"
            f" --name {name}"
            f" --cpus={self.cpu_limit}"
            f" --memory={self.memory_limit}"
            f" --network={self.network}"
            f" --security-opt no-new-privileges"
            f" -v {workspace.resolve()}:{CONTAINER_WORKSPACE}"
            f" -w {CONTAINER_WORKSPACE}"
            f" {image}"
            f" sleep infinity"  # keep alive until we exec into it
        )

        result = self._run(cmd)
        container_id = result.stdout.strip()[:12]

        log.info(
            f"Container {name} started (id={container_id}, "
            f"image={image}, cpu={self.cpu_limit}, mem={self.memory_limit})"
        )

        return ServerInfo(
            id=container_id,
            name=name,
            ip="127.0.0.1",  # local, no SSH needed
            provider="docker",
            server_type=f"container-{self.cpu_limit}cpu-{self.memory_limit}",
            snapshot_profile=snapshot_profile,
            status="running",
        )

    def destroy_server(self, server: ServerInfo) -> None:
        """Stop and remove the container."""
        log.info(f"Destroying container {server.name}...")
        self._run(
            f"docker {self._docker_opts} rm -f {server.name}",
            check=False,
        )
        server.status = "destroyed"
        log.info(f"Container {server.name} destroyed")

    def wait_for_ready(self, server: ServerInfo, timeout: int = 30) -> bool:
        """Containers are ready immediately after creation."""
        # Quick health check
        result = self._run(
            f"docker {self._docker_opts} exec {server.name} echo ready",
            check=False,
        )
        if result.returncode == 0:
            server.status = "ready"
            return True

        # Retry once (container might still be starting)
        time.sleep(0.5)
        result = self._run(
            f"docker {self._docker_opts} exec {server.name} echo ready",
            check=False,
        )
        server.status = "ready" if result.returncode == 0 else "error"
        return result.returncode == 0

    def ssh(
        self, server: ServerInfo, cmd: str, check: bool = True
    ) -> subprocess.CompletedProcess:
        """Execute command in container via docker exec (replaces SSH)."""
        return self._run(
            f"docker {self._docker_opts} exec {server.name} bash -c {_shell_quote(cmd)}",
            check=check,
            timeout=3600,
        )

    def scp_to(
        self, server: ServerInfo, local_path: str, remote_path: str
    ) -> bool:
        """Copy file into container via docker cp."""
        result = self._run(
            f"docker {self._docker_opts} cp {local_path} {server.name}:{remote_path}",
            check=False,
        )
        return result.returncode == 0

    def scp_from(
        self, server: ServerInfo, remote_path: str, local_path: str
    ) -> bool:
        """Copy file from container via docker cp."""
        result = self._run(
            f"docker {self._docker_opts} cp {server.name}:{remote_path} {local_path}",
            check=False,
        )
        return result.returncode == 0

    def rsync_from(
        self, server: ServerInfo, remote_path: str, local_path: str
    ) -> bool:
        """Copy directory from container. Uses docker cp (no rsync needed)."""
        Path(local_path).mkdir(parents=True, exist_ok=True)
        result = self._run(
            f"docker {self._docker_opts} cp {server.name}:{remote_path}. {local_path}",
            check=False,
        )
        return result.returncode == 0


def _shell_quote(s: str) -> str:
    """Quote a string for safe shell execution."""
    return "'" + s.replace("'", "'\\''") + "'"
