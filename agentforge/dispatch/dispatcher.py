"""AgentForge Dispatcher: orchestrates task execution on ephemeral compute.

Core dispatch pipeline:
1. Provision ephemeral server
2. Sync secrets (isolated per tenant)
3. Upload task instructions
4. Execute agent
5. Collect results
6. Destroy server
"""

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from agentforge.dispatch.compute import ComputeProvider, DispatchResult, ServerInfo

log = logging.getLogger("agentforge.dispatch")


@dataclass
class SecretSet:
    """Isolated secrets for an ephemeral server execution.

    Consumer secrets: API keys the task submitter wants available (e.g. their own OpenAI key).
    Provider secrets: API keys the agent developer provides (e.g. their Anthropic key).
    Platform secrets: Platform-level keys (e.g. gateway tokens).

    On the ephemeral server:
      /workspace/secrets/consumer/api-keys.env  (consumer's keys)
      /workspace/secrets/provider/api-keys.env  (provider's keys)
      /workspace/secrets/api-keys.env           (merged, backward compat)

    No key ever crosses tenant boundaries. All destroyed with server.
    """
    consumer_keys: dict[str, str] | None = None
    provider_keys: dict[str, str] | None = None
    platform_keys: dict[str, str] | None = None
    gh_token: str | None = None


class AgentForgeDispatcher:
    """Orchestrates the full lifecycle of an agent task execution.

    This is the platform-level dispatcher that wraps a ComputeProvider
    and adds secret brokerage, metering, and result collection.
    """

    def __init__(
        self,
        compute: ComputeProvider,
        results_dir: str | Path = "results",
    ):
        self.compute = compute
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def generate_run_id(self, task_id: str) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        return f"{task_id}-{ts}"

    def generate_server_name(self, run_id: str) -> str:
        short = run_id[:50].lower().replace("_", "-")
        return f"agent-{short}"

    def dispatch(
        self,
        agent_card: dict,
        task_inputs: dict,
        run_id: str | None = None,
        secrets: SecretSet | None = None,
        task_timeout: int | None = None,
    ) -> DispatchResult:
        """Execute full dispatch pipeline for a task.

        Args:
            agent_card: The agent's capability card (from DB)
            task_inputs: Consumer-provided inputs
            run_id: Unique run identifier (auto-generated if None)
            secrets: API keys and credentials to inject
            task_timeout: Override timeout from task constraints (seconds)
        """
        task_id = agent_card["meta"]["id"]
        run_id = run_id or self.generate_run_id(task_id)
        server_name = self.generate_server_name(run_id)

        runtime = agent_card.get("runtime", {})
        snapshot_profile = runtime.get("snapshot_profile", "base")
        server_type = runtime.get("server_type")
        model = runtime.get("model", "anthropic/claude-sonnet-4-6")

        # Use task-level timeout if provided, else fall back to agent card
        if task_timeout:
            timeout = task_timeout
        else:
            timeout = agent_card.get("capabilities", {}).get("constraints", {}).get(
                "timeout_max", 1800
            )
        timeout = min(timeout, 7200)

        server = None
        start_time = time.time()

        try:
            # Phase 1: Provision
            log.info(f"[{run_id}] Phase 1: Provisioning server...")
            server = self.compute.create_server(
                name=server_name,
                snapshot_profile=snapshot_profile,
                server_type=server_type,
            )

            # Phase 2: Wait for ready
            log.info(f"[{run_id}] Phase 2: Waiting for server...")
            self.compute.wait_for_ready(server)

            # Phase 3: Inject secrets (Secret Brokerage)
            log.info(f"[{run_id}] Phase 3: Injecting secrets...")
            self._inject_secrets(server, secrets)

            # Phase 4: Dispatch task
            log.info(f"[{run_id}] Phase 4: Dispatching task...")
            exit_code = self._execute_task(
                server, agent_card, task_inputs, run_id, model, timeout
            )

            # Phase 5: Collect results
            log.info(f"[{run_id}] Phase 5: Collecting results...")
            local_dir = self._collect_results(server, run_id)

            elapsed = int(time.time() - start_time)

            # Parse metrics from usage.json
            metrics = self._parse_metrics(local_dir)

            result = DispatchResult(
                success=exit_code == 0,
                run_id=run_id,
                server=server,
                exit_code=exit_code,
                elapsed_seconds=elapsed,
                results_path=str(local_dir),
                output_bytes=metrics.get("output_bytes", 0),
                metrics=metrics,
            )
            log.info(
                f"[{run_id}] Completed in {elapsed}s, exit={exit_code}, "
                f"output={metrics.get('output_bytes', 0)} bytes"
            )
            return result

        except Exception as e:
            elapsed = int(time.time() - start_time)
            log.error(f"[{run_id}] Failed after {elapsed}s: {e}")
            return DispatchResult(
                success=False,
                run_id=run_id,
                server=server,
                elapsed_seconds=elapsed,
                metrics={"error": str(e)},
            )

        finally:
            # Phase 6: Destroy (always, ephemeral by design)
            if server and server.status != "destroyed":
                log.info(f"[{run_id}] Phase 6: Destroying server...")
                try:
                    self.compute.destroy_server(server)
                except Exception as e:
                    log.error(f"[{run_id}] Failed to destroy server: {e}")

    def _inject_secrets(self, server: ServerInfo, secrets: SecretSet | None) -> None:
        """Inject secrets into ephemeral server. Core of the Secret Brokerage.

        Three isolated directories:
          /workspace/secrets/consumer/  (task submitter's keys)
          /workspace/secrets/provider/  (agent developer's keys)
          /workspace/secrets/           (merged env, backward compat)

        All destroyed when the server is destroyed. No key crosses tenant boundaries.
        """
        self.compute.ssh(
            server,
            "mkdir -p /workspace/secrets/consumer /workspace/secrets/provider",
            check=False,
        )

        if not secrets:
            return

        all_keys: dict[str, str] = {}

        # Consumer secrets (isolated)
        if secrets.consumer_keys:
            self._write_env_file(
                server, "/workspace/secrets/consumer/api-keys.env", secrets.consumer_keys
            )
            all_keys.update(secrets.consumer_keys)
            log.info(f"Injected {len(secrets.consumer_keys)} consumer secrets")

        # Provider secrets (isolated)
        if secrets.provider_keys:
            self._write_env_file(
                server, "/workspace/secrets/provider/api-keys.env", secrets.provider_keys
            )
            all_keys.update(secrets.provider_keys)
            log.info(f"Injected {len(secrets.provider_keys)} provider secrets")

        # Platform secrets
        if secrets.platform_keys:
            all_keys.update(secrets.platform_keys)
            log.info(f"Injected {len(secrets.platform_keys)} platform secrets")

        # Merged env for backward compatibility (runner sources this)
        if all_keys:
            self._write_env_file(server, "/workspace/secrets/api-keys.env", all_keys)

        # Git credentials
        if secrets.gh_token:
            self.compute.ssh(
                server,
                f'echo "https://x-access-token:{secrets.gh_token}@github.com"'
                f" > /root/.git-credentials && "
                f"chmod 600 /root/.git-credentials && "
                f"git config --global credential.helper store",
                check=False,
            )
            log.info("Injected git credentials")

    def _write_env_file(self, server: ServerInfo, path: str, keys: dict[str, str]) -> None:
        """Write a dict of key-value pairs as an env file on the server.

        Uses base64 encoding to prevent shell injection via newlines or
        special characters in secret values.
        """
        import base64

        env_lines = [f"{k}={v}" for k, v in keys.items()]
        env_content = "\n".join(env_lines)
        b64 = base64.b64encode(env_content.encode()).decode()
        self.compute.ssh(
            server,
            f"echo '{b64}' | base64 -d > {path} && chmod 600 {path}",
        )

    def _execute_task(
        self,
        server: ServerInfo,
        agent_card: dict,
        task_inputs: dict,
        run_id: str,
        model: str,
        timeout: int,
    ) -> int:
        """Build and execute the runner script on the ephemeral server."""
        task_id = agent_card["meta"]["id"]
        instructions = agent_card.get("instructions", "")

        # Substitute input variables into instructions
        for key, value in task_inputs.items():
            instructions = instructions.replace(f"{{{{{key}}}}}", str(value))
            instructions = instructions.replace(f"${{{key}}}", str(value))

        # Substitute runtime variables
        instructions = instructions.replace("$RUN_ID", run_id)
        instructions = instructions.replace("${RUN_ID}", run_id)

        # Create workspace
        self.compute.ssh(server, f"mkdir -p /workspace/agents/{run_id}")

        # Write instructions
        self.compute.ssh(
            server,
            f"cat > /workspace/agents/{run_id}/instructions.txt"
            f" << 'INSTEOF'\n{instructions}\nINSTEOF",
        )

        # Write task metadata
        task_meta = json.dumps({
            "run_id": run_id,
            "task_id": task_id,
            "model": model,
            "inputs": task_inputs,
        })
        self.compute.ssh(
            server,
            f"cat > /workspace/agents/{run_id}/task.json << 'TASKEOF'\n{task_meta}\nTASKEOF",
        )

        # Write runner script
        runner = self._build_runner_script(run_id, task_id, model, timeout)
        self.compute.ssh(
            server,
            f"cat > /workspace/agents/{run_id}/run.sh << 'RUNEOF'\n{runner}\nRUNEOF",
        )
        self.compute.ssh(server, f"chmod +x /workspace/agents/{run_id}/run.sh")

        # Execute
        log.info(f"Executing with model={model}, timeout={timeout}s")
        ssh_timeout = timeout + 60
        ssh_cmd = (
            f"ssh {self.compute._ssh_opts} root@{server.ip}"
            f" 'bash /workspace/agents/{run_id}/run.sh'"
        )
        result = self.compute._run(
            ssh_cmd,
            check=False,
            timeout=ssh_timeout,
        )
        return result.returncode

    def _build_runner_script(
        self, run_id: str, task_id: str, model: str, timeout: int
    ) -> str:
        """Generate the bash runner script for the ephemeral server."""
        return f"""#!/bin/bash
set -euo pipefail
source /workspace/secrets/api-keys.env 2>/dev/null || true
export DISPLAY=:99 2>/dev/null || true
export RUN_ID="{run_id}"

# Inject API key into OpenClaw auth-profiles if ANTHROPIC_API_KEY is set
if [ -n "${{ANTHROPIC_API_KEY:-}}" ]; then
    AGENT_DIR=/root/.openclaw/agents/main/agent
    mkdir -p "$AGENT_DIR"
    cat > "$AGENT_DIR/auth-profiles.json" << AUTHEOF
{{"version":1,"profiles":{{"anthropic:manual":{{"type":"token","provider":"anthropic","token":"$ANTHROPIC_API_KEY"}}}},"lastGood":{{"anthropic":"anthropic:manual"}},"usageStats":{{}}}}
AUTHEOF
fi
cd /workspace/agents/{run_id}

START_TS=$(date +%s)
INSTRUCTIONS="$(cat /workspace/agents/{run_id}/instructions.txt)"

# Detect Gateway mode
GATEWAY_MODE=false
if curl -sf http://127.0.0.1:18789/healthz > /dev/null 2>&1; then
    GATEWAY_MODE=true
fi

if [ "$GATEWAY_MODE" = true ]; then
    timeout --kill-after=30 {timeout} openclaw agent --agent main --timeout {timeout} --message "$INSTRUCTIONS" \\
        > /workspace/agents/{run_id}/stdout.log \\
        2> /workspace/agents/{run_id}/stderr.log
    EXIT_CODE=$?
else
    timeout --kill-after=30 {timeout} openclaw agent --local --agent main --timeout {timeout} --message "$INSTRUCTIONS" \\
        > /workspace/agents/{run_id}/stdout.log \\
        2> /workspace/agents/{run_id}/stderr.log
    EXIT_CODE=$?
fi

# Build output.md
OUTFILE=/workspace/agents/{run_id}/output.md
if [ -s "$OUTFILE" ] && [ "$(stat -c%s "$OUTFILE" 2>/dev/null || echo 0)" -gt 500 ]; then
    echo "Using agent-created output.md"
elif [ -s /workspace/agents/{run_id}/stdout.log ]; then
    cp /workspace/agents/{run_id}/stdout.log "$OUTFILE"
else
    echo "# Agent produced no output" > "$OUTFILE"
    echo "Exit code: $EXIT_CODE" >> "$OUTFILE"
fi

# Collect workspace files (check multiple locations where agents write output)
for f in /workspace/output.md /workspace/screenshots/*.png /root/.openclaw/workspace/output.md /root/output.md; do
    [ -e "$f" ] && cp -n "$f" /workspace/agents/{run_id}/ 2>/dev/null
done

END_TS=$(date +%s)
ELAPSED=$((END_TS - START_TS))

set +eo pipefail
STDOUT_BYTES=$(stat -c%s /workspace/agents/{run_id}/stdout.log 2>/dev/null || echo 0)
STDERR_BYTES=$(stat -c%s /workspace/agents/{run_id}/stderr.log 2>/dev/null || echo 0)
OUTPUT_BYTES=$(stat -c%s "$OUTFILE" 2>/dev/null || echo 0)
OUTPUT_CHARS=$(wc -c < "$OUTFILE" 2>/dev/null || echo 0)
EST_OUTPUT_TOKENS=$((OUTPUT_CHARS / 4))

cat > /workspace/agents/{run_id}/usage.json << USAGEEOF
{{
    "run_id": "{run_id}",
    "task_id": "{task_id}",
    "model": "{model}",
    "gateway_mode": "$GATEWAY_MODE",
    "start_ts": $START_TS,
    "end_ts": $END_TS,
    "elapsed_seconds": $ELAPSED,
    "exit_code": $EXIT_CODE,
    "metrics": {{
        "stdout_bytes": $STDOUT_BYTES,
        "stderr_bytes": $STDERR_BYTES,
        "output_bytes": $OUTPUT_BYTES,
        "output_tokens_est": $EST_OUTPUT_TOKENS
    }}
}}
USAGEEOF

exit $EXIT_CODE"""

    def _collect_results(self, server: ServerInfo, run_id: str) -> Path:
        """Rsync results from ephemeral server to local storage."""
        local_dir = self.results_dir / run_id
        local_dir.mkdir(parents=True, exist_ok=True)

        success = self.compute.rsync_from(
            server,
            f"/workspace/agents/{run_id}/",
            f"{local_dir}/",
        )
        if not success:
            log.warning(f"Result collection failed for {run_id}")

        return local_dir

    def _parse_metrics(self, results_dir: Path) -> dict:
        """Parse usage.json from results directory."""
        usage_file = results_dir / "usage.json"
        if not usage_file.exists():
            return {}
        try:
            data = json.loads(usage_file.read_text())
            return {
                "elapsed_seconds": data.get("elapsed_seconds"),
                "exit_code": data.get("exit_code"),
                "output_bytes": data.get("metrics", {}).get("output_bytes", 0),
                "output_tokens_est": data.get("metrics", {}).get("output_tokens_est", 0),
                "gateway_mode": data.get("gateway_mode"),
                "model": data.get("model"),
            }
        except Exception:
            return {}
